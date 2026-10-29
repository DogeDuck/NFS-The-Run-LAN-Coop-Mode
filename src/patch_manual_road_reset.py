"""Experimental manual road reset in the compatible LAN client.

Routes the manual reset input through the existing road recovery buffer and
client-to-server actor teleport request, instead of emitting a story rewind.
This patch affects manual reset in this executable, including solo sessions.
Automatic wreck/timeout recovery is NOT covered. Restore before normal solo play.
"""
from pathlib import Path
import argparse
import datetime
import json
import os
import struct
from patch_headless_reset import require_game_closed, file_offset, digest

ROOT=Path(__file__).resolve().parent
ORIGINAL_HASH='33853c17cb5850cc7deb9fb8e7d013815a60026be0ff3b3f6b70071cb56215e9'
SITE=0x8ECA81
TARGET=0x8ECAF0
BEFORE=bytes.fromhex('a1cc2a8802')
AFTER=b'\xe9'+struct.pack('<i',TARGET-SITE-5)

def build(original):
    if digest(original)!=ORIGINAL_HASH:raise ValueError('Unsupported client build')
    offset=file_offset(original,SITE)
    if original[offset:offset+5]!=BEFORE:raise ValueError('Input branch does not match')
    # Check both the surrounding input function and the recovery-buffer branch.
    if original[file_offset(original,0x8ECA70):file_offset(original,0x8ECA70)+10]!=bytes.fromhex('83ec28568bf1b9010000'):
        raise ValueError('Input function does not match')
    if original[file_offset(original,TARGET):file_offset(original,TARGET)+8]!=bytes.fromhex('8b46208b50103b50'):
        raise ValueError('Road reset branch does not match')
    result=bytearray(original);result[offset:offset+5]=AFTER
    if any(a!=b for a,b in zip(original[:offset],result[:offset])) or original[offset+5:]!=result[offset+5:]:
        raise ValueError('Patch changes unrelated bytes')
    return bytes(result),offset

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-dir',type=Path,default=Path(r'X:\EA Games\Need for Speed The Run\Need for Speed The Run'))
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--restore',action='store_true')
    args=parser.parse_args()
    game_dir=args.game_dir.resolve()
    if any(part.casefold()=='therunbackup' for part in game_dir.parts):raise ValueError('User backup is excluded')
    exe=game_dir/'Need For Speed The Run.exe'
    backup=ROOT/'backups'/'Need For Speed The Run.exe.lan-before-road-reset'
    current=exe.read_bytes()
    original=current if digest(current)==ORIGINAL_HASH else backup.read_bytes()
    patched,offset=build(original)
    if current not in (original,patched):raise ValueError('Client changed; refusing overwrite')
    replacement=original if args.restore else patched
    if args.check:
        print(json.dumps(dict(status='verified',site=hex(SITE),target=hex(TARGET),fileOffset=hex(offset),
            originalHash=digest(original),patchedHash=digest(patched),installed=current==patched)))
        return
    if current==replacement:print('Requested manual reset mode already installed');return
    require_game_closed()
    backup.parent.mkdir(exist_ok=True)
    if backup.exists() and backup.read_bytes()!=original:raise ValueError('Existing LAN client backup differs')
    if not backup.exists():
        with backup.open('xb') as out:out.write(original)
    if backup.read_bytes()!=original:raise RuntimeError('Backup verification failed')
    with exe.open('r+b') as out:
        if out.read()!=current:raise RuntimeError('Client changed during preparation')
        out.seek(0);out.write(replacement);out.truncate();out.flush();os.fsync(out.fileno())
    if exe.read_bytes()!=replacement:raise RuntimeError('Installed client verification failed')
    report=dict(timestamp=datetime.datetime.now().astimezone().isoformat(),action='restore' if args.restore else 'patch',
        executable=str(exe),backup=str(backup),before=digest(current),after=digest(replacement),
        site=hex(SITE),target=hex(TARGET),scope='Manual reset input only; automatic wreck and mission timeout remain unchanged')
    outputs=ROOT/'outputs';outputs.mkdir(exist_ok=True)
    (outputs/'manual-road-reset-patch.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
