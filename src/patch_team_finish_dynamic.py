"""Build an OFFLINE candidate team-result client from installed v0.5 bytes.

Does not install, launch, or publish. Runtime roster variant needs gameplay testing.
"""
import argparse,json,struct
from pathlib import Path
from patch_headless_reset import digest,file_offset
from pe_adapter import append_adapter
from probe_lifecycle import call_bytes
from team_finish_adapter import SPECS
from team_finish_dynamic_adapter import make_code

BASE='2cb4570c34e46cc74ccded44f8f38338c12a0edfbb33a74572b72fc6e11ad249'

def build(base):
 if digest(base).lower()!=BASE:raise ValueError('Exact v0.5 client required')
 fingerprints={0x254F030:struct.pack('<I',0xF42010),0x254F038:struct.pack('<I',0xF42020),0xF26560:bytes.fromhex('8b4424043b4108'),0xF2656E:bytes.fromhex('8b89c00000008b0481'),0xF42010:bytes.fromhex('8b8134030000c3'),0xF42020:bytes.fromhex('8a8160020000c3')}
 for site,expected in fingerprints.items():
  off=file_offset(base,site)
  if base[off:off+len(expected)]!=expected:raise ValueError('Native roster ABI mismatch')
 for site,native in SPECS:
  off=file_offset(base,site)
  if base[off:off+5]!=call_bytes(site,native):raise ValueError('Result getter already changed')
 def factory(code,stats):
  first=make_code(code,stats,SPECS[0][1]);second=make_code(code+1024,stats+4,SPECS[1][1])
  if len(first)>1024:raise ValueError('Getter adapter overlap')
  return first+b'\xCC'*(1024-len(first))+second
 patched,layout,code,_=append_adapter(base,factory,b'.teamwin',b'.teamcnt')
 for index,(site,native) in enumerate(SPECS):
  off=file_offset(patched,site);patched[off:off+5]=call_bytes(site,layout['adapter']+index*1024)
 report=dict(sha256=digest(patched),source_sha256=BASE,layout=layout,gameplay_verified=False,published=False,installed=False,
  scope='Native Story result mode0 finish-time/rank getters; exactly two validated non-bot client players; IDs derived per call.',
  limitations=['Not a general scripted mission/failure-message replacement','No shared overtaken HUD','Native result timing and continue transition require gameplay tests','Unexpected roster/type declines to original behaviour'])
 return bytes(patched),code,report

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.source.resolve()==a.output.resolve() or a.output.exists():raise ValueError('New separate output required')
 data,_,report=build(a.source.read_bytes());a.output.write_bytes(data);a.output.with_suffix('.json').write_text(json.dumps(report,indent=2))
 print(json.dumps(report,indent=2))
