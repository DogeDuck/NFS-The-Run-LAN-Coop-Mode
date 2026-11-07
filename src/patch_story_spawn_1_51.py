"""Version-locked1.51 client spawn patch. Default builds/checks offline only.

Experimental two-player recovery, not a general event spawn or progression fix.
No game binary is written unless --install/--restore is explicitly selected.
"""
import argparse
import json
import os
from pathlib import Path
import struct
from coop_diagnostics import BUILD
from orphan_spawn_release_adapter import SITE, TARGET, make_code
from patch_headless_reset import file_offset, digest, require_game_closed
from pe_adapter import append_adapter
from probe_lifecycle import call_bytes
ROOT=Path(__file__).resolve().parent
EXE=Path(r'X:\EA Games\Need for Speed The Run\Need for Speed The Run\Need For Speed The Run.exe')
BACKUP=ROOT/'backups/Need For Speed The Run.exe.before-spawn-1_51'
REFERENCE=ROOT/'diagnostics/references/story-1_51-recovery.json'


def build(base, manual_restart=False):
 if digest(base).upper()!=BUILD.upper():raise ValueError('Unsupported baseline client')
 off=file_offset(base,SITE)
 if base[off:off+5]!=call_bytes(SITE,TARGET):raise ValueError('Native actor binding call mismatch')
 reference=json.loads(REFERENCE.read_text(encoding='utf-8'))
 matrix=reference['matrix']
 if len(matrix)!=16:raise ValueError('Invalid recovery reference')
 def factory(a,s):
  spawn=make_code(a,s,runtime_lanes=True)
  if not manual_restart:return spawn
  from manual_retry_mode_adapter import client_code
  if len(spawn)>0x400:raise ValueError('Spawn adapter overlaps manual restart')
  return spawn+b'\xcc'*(0x400-len(spawn))+client_code(a+0x400,s+0x40)
 patched,layout,code,sections=append_adapter(base,factory,b'.spnfix',b'.spnstat')
 patched[off:off+5]=call_bytes(SITE,layout['adapter'])
 exclusions=[(off,off+5)]
 if manual_restart:
  from manual_retry_mode_adapter import CLIENT_SITE,CLIENT_ORIGINAL
  manual_off=file_offset(base,CLIENT_SITE)
  if base[manual_off:manual_off+6]!=CLIENT_ORIGINAL:raise ValueError('Manual restart entry mismatch')
  patched[manual_off:manual_off+6]=b'\xe9'+struct.pack('<i',layout['adapter']+0x400-CLIENT_SITE-5)+b'\x90'
  exclusions.append((manual_off,manual_off+6))
 stats=file_offset(patched,layout['counter'])
 struct.pack_into('<I',patched,stats,1)
 for index,delta in enumerate((-2.5,2.5)):
  lane=list(matrix)
  for axis in range(3):lane[12+axis]+=matrix[axis]*delta
  struct.pack_into('<16f',patched,stats+0x100+index*0x80,*lane)
 # Declare the full diagnostics and both lane matrices, not just an8-byte header.
 pe=struct.unpack_from('<I',patched,0x3c)[0];count=struct.unpack_from('<H',patched,pe+6)[0]
 table=pe+24+struct.unpack_from('<H',patched,pe+20)[0]
 struct.pack_into('<I',patched,table+40*(count-1)+8,0x1c0)
 for _,_,size,raw in sections:
  original=bytearray(base[raw:raw+size]);actual=bytearray(patched[raw:raw+size])
  for start,end in exclusions:
   lo,hi=max(start,raw),min(end,raw+size)
   if hi>lo:actual[lo-raw:hi-raw]=original[lo-raw:hi-raw]
  if actual!=original:raise ValueError('Unrelated native section changed')
 report=dict(base_sha256=digest(base),patched_sha256=digest(patched),layout=layout,site=hex(SITE),
             scope=reference['scope'],manual_restart=manual_restart,installed=False,live_validation='Prototype street position observed; broader testing pending')
 return bytes(patched),code,report


def main():
 p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group()
 g.add_argument('--install',action='store_true');g.add_argument('--restore',action='store_true');a=p.parse_args()
 current=EXE.read_bytes();base=BACKUP.read_bytes() if BACKUP.exists() else current
 patched,code,report=build(base)
 if current not in (base,patched):raise ValueError('Unrecognized installed client state')
 if a.install or a.restore:
  require_game_closed()
  if not BACKUP.exists():
   with BACKUP.open('xb') as f:f.write(base)
  if BACKUP.read_bytes()!=base:raise ValueError('Backup mismatch')
  replacement=base if a.restore else patched
  if replacement!=current:
   temp=EXE.with_name(EXE.name+'.spawn-tmp')
   with temp.open('xb') as f:f.write(replacement);f.flush();os.fsync(f.fileno())
   if temp.read_bytes()!=replacement or EXE.read_bytes()!=current:raise ValueError('Staged file mismatch')
   os.replace(temp,EXE)
  report['installed']=replacement==patched
 (ROOT/'outputs/spawn-1_51-adapter.bin').write_bytes(code)
 (ROOT/'outputs/spawn-1_51-patch.json').write_text(json.dumps(report,indent=2))
 print(json.dumps(report,indent=2))


if __name__=='__main__':main()
