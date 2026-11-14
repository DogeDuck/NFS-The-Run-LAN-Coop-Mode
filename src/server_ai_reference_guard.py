"""Narrow offline test candidate for server dump11188, not an AI root-cause fix.

At127BC07 ECX=[ESI+6C], native getter [vtable+10] jumps to data2572B58.
Only that exact bad target returns NULL; every other getter is called unchanged.
Downstream handling of NULL must be tested live before this is shipped.
"""
import hashlib,struct
from checkpoint_humans_adapter import Code
from pe_adapter import append_adapter
from patch_headless_reset import file_offset
SITE,RETURN,BAD=0x127BC07,0x127BC0E,0x2572B58
ORIGINAL=bytes.fromhex('8b018b5010ffd2')
STATS_SIZE=0x20
BASE='bcdafbf8db104fb070e093e147e9e3d440daef15f4499c3a2037313a14bc40aa'
R2='f2e5a72ccb5d781833e58395715c08e1b7a400c5700e0177b5861ad66f688173'
def make_code(base,stats):
 c=Code(base);c.emit('9c8b018b501081fa'+struct.pack('<I',BAD).hex())
 c.branch('0f84','invalid');c.emit('9dffd2');c.branch('e9',RETURN)
 c.label('invalid');c.emit('ff05'+struct.pack('<I',stats).hex())
 # Capture already-loaded registers only; no additional risky heap dereference.
 for opcode,offset in (('890d',4),('a3',8),('8915',12),('8935',16),('893d',20)):
  c.emit(opcode+struct.pack('<I',stats+offset).hex())
 c.emit('9db800000000');c.branch('e9',RETURN)
 return c.finish()
def build(raw):
 if hashlib.sha256(raw).hexdigest() not in (BASE,R2):raise ValueError('Exact RACESTART BC or R2 server required')
 at=file_offset(raw,SITE)
 if raw[at:at+7]!=ORIGINAL:raise ValueError('Virtual getter site differs')
 patched,info,_,_=append_adapter(raw,make_code,b'.aiguard',b'.aigstat')
 pe=struct.unpack_from('<I',patched,0x3C)[0]
 table=pe+24+struct.unpack_from('<H',patched,pe+20)[0]
 count=struct.unpack_from('<H',patched,pe+6)[0]
 struct.pack_into('<I',patched,table+(count-1)*40+8,STATS_SIZE)
 at=file_offset(patched,SITE);patched[at:at+7]=b'\xe9'+struct.pack('<i',info['adapter']-(SITE+5))+b'\x90\x90'
 return bytes(patched),dict(info,installed=False,experimental=True,gameplay_verified=False,
                           root_cause_fixed=False,scope='exact bad target only; NULL fallback needs gameplay verification')
