"""Reversible, version-locked first fix for The Run's dedicated story server.

This fixes ONLY the headless spatial-streaming settle counter. Multiplayer
vehicle teleport and story/HUD synchronization are still under investigation.
No game assets or executable code are distributed with this script.
"""
from pathlib import Path
import argparse
import ctypes as c
from ctypes import wintypes as w
import datetime
import hashlib
import json
import os
import struct

ROOT = Path(__file__).resolve().parent
ORIGINAL_SHA256 = '198c0d478dab01898d3dd487e1ee483c8ae0fd6bf2ed3fb03d409de5b2f1fe5e'
INSTRUCTION_VA = 0xD9F6C0
ORIGINAL = bytes.fromhex('c7864002000003000000')
PATCHED = bytes.fromhex('c7864002000000000000')

def digest(data):
    return hashlib.sha256(data).hexdigest()

def file_offset(data, address):
    pe = struct.unpack_from('<I', data, 0x3C)[0]
    assert data[:2] == b'MZ' and data[pe:pe+4] == b'PE\0\0', 'Invalid executable'
    assert struct.unpack_from('<H', data, pe+4)[0] == 0x14C, 'Expected x86 executable'
    base = struct.unpack_from('<I', data, pe+52)[0]
    count = struct.unpack_from('<H', data, pe+6)[0]
    opt_size = struct.unpack_from('<H', data, pe+20)[0]
    for index in range(count):
        section = pe+24+opt_size+40*index
        _, rva, size, raw = struct.unpack_from('<4I', data, section+8)
        if base+rva <= address < base+rva+size:
            return raw+address-base-rva
    raise ValueError('Instruction is outside file-backed sections')

def require_game_closed():
    if os.name != 'nt':
        raise RuntimeError('Installation patching is supported on Windows only')
    # Read-only process inventory. Refuse even inaccessible matching processes.
    kernel = c.WinDLL('kernel32', use_last_error=True)
    class Entry(c.Structure):
        _fields_ = [('size',w.DWORD),('usage',w.DWORD),('pid',w.DWORD),
            ('heap',c.c_size_t),('module',w.DWORD),('threads',w.DWORD),
            ('parent',w.DWORD),('priority',w.LONG),('flags',w.DWORD),
            ('name',w.WCHAR*260)]
    kernel.CreateToolhelp32Snapshot.argtypes=[w.DWORD,w.DWORD]
    kernel.CreateToolhelp32Snapshot.restype=w.HANDLE
    kernel.Process32FirstW.argtypes=[w.HANDLE,c.POINTER(Entry)]
    kernel.Process32NextW.argtypes=[w.HANDLE,c.POINTER(Entry)]
    kernel.CloseHandle.argtypes=[w.HANDLE]
    snapshot=kernel.CreateToolhelp32Snapshot(2,0)
    if snapshot == c.c_void_p(-1).value:
        raise c.WinError(c.get_last_error())
    try:
        entry=Entry();entry.size=c.sizeof(entry)
        ok=kernel.Process32FirstW(snapshot,c.byref(entry))
        if not ok:raise c.WinError(c.get_last_error())
        while ok:
            if entry.name.casefold() in ('nfstr_server.exe','need for speed the run.exe'):
                raise RuntimeError(f'Close the game and server first (PID {entry.pid})')
            ok=kernel.Process32NextW(snapshot,c.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)

def patch_bytes(original):
    if digest(original) != ORIGINAL_SHA256:
        raise ValueError('Unknown server build; refusing patch')
    offset=file_offset(original,INSTRUCTION_VA)
    if original[offset:offset+len(ORIGINAL)] != ORIGINAL:
        raise ValueError('Reset instruction does not match')
    result=bytearray(original)
    result[offset:offset+len(ORIGINAL)]=PATCHED
    changed=[i for i,(a,b) in enumerate(zip(original,result)) if a!=b]
    if changed != [offset+6]:
        raise ValueError('Unexpected patch scope')
    return bytes(result), offset

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-dir',type=Path,default=Path(r'X:\EA Games\Need for Speed The Run\Need for Speed The Run'))
    parser.add_argument('--restore',action='store_true')
    parser.add_argument('--check',action='store_true',help='Verify the patch without modifying any files')
    args=parser.parse_args()
    game_dir=args.game_dir.resolve()
    if game_dir.name.casefold()=='therunbackup':
        raise ValueError('User backup must not be modified')
    server=game_dir/'NFSTR_Server.exe'
    backup=ROOT/'backups'/'NFSTR_Server.exe.headless-original'
    current=server.read_bytes()
    if args.restore:
        original=backup.read_bytes()
        patched,offset=patch_bytes(original)
        if digest(current)==ORIGINAL_SHA256:
            print('Original server already restored');return
        if current != patched:
            raise ValueError('Server changed since patching; refusing restore')
        replacement=original
    else:
        if digest(current)==ORIGINAL_SHA256:
            original=current
        elif backup.exists():
            original=backup.read_bytes()
        else:
            raise ValueError('Unknown server build and no local original backup')
        patched,offset=patch_bytes(original)
        if current==patched:
            print('Headless settle patch is already installed');return
        if current!=original:
            raise ValueError('Current server does not match the original')
        replacement=patched
    if args.check:
        print(json.dumps(dict(status='verified',instructionVA=hex(INSTRUCTION_VA),
            offset=hex(offset),changedBytes=1,originalHash=digest(original),patchedHash=digest(patched))))
        return
    require_game_closed()
    if not args.restore:
        backup.parent.mkdir(exist_ok=True)
        if backup.exists() and backup.read_bytes()!=original:
            raise ValueError('Existing original backup differs')
        if not backup.exists():
            with backup.open('xb') as out:out.write(original)
        if backup.read_bytes()!=original:raise RuntimeError('Backup verification failed')
    # Locked/mapped executable files fail the open on Windows.
    with server.open('r+b') as out:
        if out.read()!=current:raise RuntimeError('Server changed during patch preparation')
        out.seek(0);out.write(replacement);out.truncate();out.flush();os.fsync(out.fileno())
    if server.read_bytes()!=replacement:raise RuntimeError('Written server failed verification')
    report=dict(timestamp=datetime.datetime.now().astimezone().isoformat(),
        action='restore' if args.restore else 'patch',server=str(server),backup=str(backup),
        before=digest(current),after=digest(replacement),changedBytes=1,
        limitation='Only headless streaming settle counter. Client vehicle/HUD reset synchronization remains unresolved.')
    outputs=ROOT/'outputs';outputs.mkdir(exist_ok=True)
    (outputs/'headless-reset-patch.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
