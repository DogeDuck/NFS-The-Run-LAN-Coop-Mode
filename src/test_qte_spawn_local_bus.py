"""Native-byte regression tests for local Story-OOC actor link resolution.

These tests emulate real registration/getter/link-resolver instructions. Engine
type/lookup services are fixture stubs; no world, rendering or QTE is emulated.
"""
from pathlib import Path
import itertools
import struct
import sys
import unittest
sys.path.insert(0, str(Path(__file__).parent/'outputs/test-libs'))
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import *
import qte_spawn_local_bus as a
import coop_hud_adapter as hud
from qte_hud_scope_adapter import CHALLENGE_CONTROLLER
from patch_qte_spawn_local_bus import build
from offline_test_images import image
from pe_image_readonly import PE32

BASE = image('client','integrated')
PATCHED, REPORT = build(BASE)
PE = PE32(BASE)
CODE, STATS = REPORT['adapter'], REPORT['counter']
D, STACK, RET = 0x30000000, 0x32000000, 0x34000000
SPAWN, VECTOR, LINK = D+0x1000, D+0x2000, D+0x3000
PARENT, BUS_VT = D+0x4000, D+0x5000
REF, BP, TYPE, ACTOR_DATA = D+0x6000, D+0x7000, D+0x8000, D+0x9000
TYPE_VT = D+0xA000
FAKE_TYPE, FAKE_BUS_RESOLVE, FAKE_CONTEXT = RET+0x1000, RET+0x2000, RET+0x3000


class Machine:
    def __init__(self, patched=True):
        self.u = u = Uc(UC_ARCH_X86, UC_MODE_32)
        u.mem_map(0x400000, 0x2800000)
        for va in (D, STACK, RET): u.mem_map(va, 0x100000)
        for start, length in ((a.NATIVE,4),(0xEEE300,0x67),(0xEE1EE0,0xB0),
                              (0x8CAFC0,0x2F),(0x459A00,0x388),
                              (0x44B9E0,0x2A),(0x42B180,0xF)):
            u.mem_write(start, PE.read(start,length))
        u.mem_write(a.SPAWN_VT,PE.read(a.SPAWN_VT,0x70))
        u.mem_write(CODE,a.make_code(CODE,STATS))
        self.put(a.SLOT,CODE if patched else a.NATIVE)
        self.put(SPAWN,a.SPAWN_VT)
        self.put(SPAWN+0x5C,VECTOR); self.put(SPAWN+0x60,VECTOR)
        self.put(SPAWN+0x64,VECTOR+64); self.put(SPAWN+0xC0,D+0xF000)
        self.put(hud.ONLINE,D+0x10000); self.put(D+0x100A4,3)
        self.put(hud.MODE,D+0x11000); self.put(D+0x11004,2)
        self.put(CHALLENGE_CONTROLLER,D+0x12000)
        self.put(D+0x12010,D+0x13000); self.put(D+0x13028,3)
        self.events=[]; self.lookups=[]; self.notify=[]
        u.hook_add(UC_HOOK_CODE,self.hook)

    def put(self, at, value): self.u.mem_write(at,struct.pack('<I',value))
    def get(self, at): return struct.unpack('<I',self.u.mem_read(at,4))[0]
    def return_from_stub(self, value=0, pop=0):
        u=self.u; sp=u.reg_read(UC_X86_REG_ESP); back=self.get(sp)
        u.reg_write(UC_X86_REG_EAX,value)
        u.reg_write(UC_X86_REG_ESP,sp+4+pop); u.reg_write(UC_X86_REG_EIP,back)

    def hook(self,u,pc,size,_):
        sp=u.reg_read(UC_X86_REG_ESP); ecx=u.reg_read(UC_X86_REG_ECX)
        if pc==RET: u.emu_stop()
        elif pc==0xEDEAE0:
            self.notify.append((ecx,self.get(sp+4),self.get(sp+8)))
            self.return_from_stub(pop=8)
        elif pc==0x44BEF0:
            self.events.append((ecx,self.get(sp+4))); self.return_from_stub(pop=4)
        elif pc==FAKE_TYPE: self.return_from_stub(TYPE)
        elif pc==0x48C1B0:
            self.return_from_stub(int(self.get(sp+4)==0x2A9310C),4)
        elif pc==FAKE_CONTEXT: self.return_from_stub(D+0xF100)
        elif pc==0x44ECE0: self.return_from_stub(ACTOR_DATA)
        elif pc==FAKE_BUS_RESOLVE:
            data=self.get(sp+4); self.lookups.append((ecx,data))
            if ecx==PARENT: result=SPAWN
            else: result=ecx+0x100
            self.return_from_stub(result,8)

    def call(self, entry, ecx=SPAWN, args=()):
        u=self.u; sp=STACK+0x8000
        self.put(sp,RET)
        for i,v in enumerate(args): self.put(sp+4+i*4,v)
        u.reg_write(UC_X86_REG_ESP,sp); u.reg_write(UC_X86_REG_ECX,ecx)
        u.emu_start(entry,RET+1,count=20000)
        assert u.reg_read(UC_X86_REG_EIP)==RET
        assert u.reg_read(UC_X86_REG_ESP)==sp+4+len(args)*4
        return u.reg_read(UC_X86_REG_EAX)

    def pawn(self, index, local=False):
        at=D+0x20000+index*0x1000; player=at+0x400; bus=at+0x800
        self.put(at,a.BASIC_VT); self.put(at+0x10,bus); self.put(at+0xD8,player)
        self.u.mem_write(player+0x37B,b'\x08' if local else b'\x00')
        self.put(bus,BUS_VT)
        return at,bus,player

    def add(self, pawn): self.call(0xEEE300,args=(pawn,))
    def getter(self): return self.call(self.get(a.SLOT))

    def link(self):
        self.put(PARENT,BUS_VT); self.put(BUS_VT+0x38,FAKE_BUS_RESOLVE)
        self.put(BUS_VT+0x4C,FAKE_CONTEXT)
        self.put(REF,TYPE_VT); self.put(BP,TYPE_VT); self.put(TYPE_VT,FAKE_TYPE)
        self.put(REF+0x50,BP); self.put(BP+0x24,ACTOR_DATA)
        self.u.mem_write(TYPE+0x14,struct.pack('<H',0x100))
        self.u.mem_write(0x2A93008,struct.pack('<2H',0x100,0x100))
        self.put(LINK+0xC,PARENT)
        self.call(0x459A00,LINK,(0,REF,0xA4CA82E5,0,0x2ABD884))
        return self.call(0x44B9E0,LINK,(0,))


class Tests(unittest.TestCase):
    def test_native_registration_keeps_first_remote_bus_even_after_local_add(self):
        m=Machine(False); remote,rb,_=m.pawn(0); local,lb,_=m.pawn(1,True)
        m.add(remote);m.add(local)
        self.assertEqual(m.get(SPAWN+0x6C),rb); self.assertEqual(m.getter(),rb)
        self.assertEqual([x[1] for x in m.notify],[remote,local])
        self.assertNotEqual(rb,lb)

    def test_native_full_reference_resolver_binds_remote_before_local_candidate(self):
        for patched in (False,True):
            m=Machine(patched); remote,rb,_=m.pawn(0); local,lb,_=m.pawn(1,True)
            m.add(remote);m.add(local)
            result=m.link(); chosen=lb if patched else rb
            self.assertEqual(m.get(LINK+0xC),chosen)
            self.assertEqual(m.lookups,[(PARENT,REF),(chosen,ACTOR_DATA)])
            self.assertEqual(result,chosen+0x100)
            self.assertEqual(m.get(SPAWN+0x6C),rb) # No global bus mutation.
            self.assertEqual(m.events,[])

    def test_two_to_four_humans_every_spawn_order_and_local_position(self):
        for count in (2,3,4):
            for order in itertools.permutations(range(count)):
                for local in range(count):
                    m=Machine(); pawns=[m.pawn(i,i==local) for i in range(count)]
                    for i in order:m.add(pawns[i][0])
                    self.assertEqual(m.getter(),pawns[local][1],(count,order,local))

    def test_native_set_owner_emits_local_spawn_only_for_local_player(self):
        for local in (False,True):
            m=Machine(); pawn,_,player=m.pawn(0,local);m.put(pawn+0xD8,0)
            m.call(0x8CAFC0,pawn,(player,));m.call(0x8CAFC0,pawn,(player,))
            self.assertEqual(m.get(pawn+0xD8),player)
            self.assertEqual(m.events,[(pawn,0x2B7CE0D8)] if local else [])

    def test_scope_fallback_never_reads_spawn_vector(self):
        for at,value in ((hud.ONLINE,0),(D+0x10008,1),(D+0x100A4,2),
                         (hud.MODE,0),(D+0x11004,1),(CHALLENGE_CONTROLLER,0),
                         (D+0x12010,0),(D+0x13028,0),(SPAWN,0xDEADBEEF)):
            m=Machine(); m.put(SPAWN+0x6C,0x12345678)
            m.put(SPAWN+0x5C,0xDEAD0000);m.put(SPAWN+0x60,0xDEAD0004)
            m.put(at,value); self.assertEqual(m.getter(),0x12345678)

    def test_empty_malformed_and_oversized_vectors_fall_back(self):
        for begin,end in ((0,0),(VECTOR,VECTOR),(VECTOR,VECTOR-4),
                          (VECTOR,VECTOR+3),(VECTOR,VECTOR+68)):
            m=Machine(); m.put(SPAWN+0x6C,0xABCDEF)
            m.put(SPAWN+0x5C,begin); m.put(SPAWN+0x60,end)
            self.assertEqual(m.getter(),0xABCDEF)

    def test_missing_owner_wrong_type_and_null_bus_do_not_select_remote(self):
        for offset,value in ((0,0xDEADBEEF),(0xD8,0),(0x10,0)):
            m=Machine();remote,rb,_=m.pawn(0);local,_,_=m.pawn(1,True)
            m.add(remote);m.add(local);m.put(local+offset,value)
            self.assertEqual(m.getter(),rb)

    def test_registration_removal_uses_current_local_pawn_without_cached_pointer(self):
        m=Machine(); r,rb,_=m.pawn(0);l,lb,p=m.pawn(1,True)
        m.add(r);m.add(l);self.assertEqual(m.getter(),lb)
        m.call(0xEE1EE0,args=(l,));self.assertEqual(m.getter(),rb)
        m.add(l);self.assertEqual(m.getter(),lb)
        m.u.mem_write(p+0x37B,b'\x00');self.assertEqual(m.getter(),rb)

    def test_abi_preserves_all_other_registers_flags_simd_and_stack(self):
        for found in (False,True):
            m=Machine();p,_,_=m.pawn(0,found);m.add(p)
            regs={UC_X86_REG_EBX:0xAABBCCDD,UC_X86_REG_ESI:1234,
                  UC_X86_REG_EDI:0xEEFF0011,UC_X86_REG_EBP:4242,UC_X86_REG_EDX:9876}
            for r,v in regs.items():m.u.reg_write(r,v)
            m.u.reg_write(UC_X86_REG_EFLAGS,0xAD7)
            m.u.reg_write(UC_X86_REG_XMM0,0x112233445566778899)
            m.getter()
            for r,v in regs.items():self.assertEqual(m.u.reg_read(r),v)
            self.assertEqual(m.u.reg_read(UC_X86_REG_ECX),SPAWN)
            self.assertEqual(m.u.reg_read(UC_X86_REG_EFLAGS)&0xFFF,0xAD7)
            self.assertEqual(m.u.reg_read(UC_X86_REG_XMM0),0x112233445566778899)

    def test_build_changes_only_one_existing_vtable_slot(self):
        q=PE32(PATCHED)
        self.assertEqual(q.read(a.SLOT,4),struct.pack('<I',CODE))
        for s in PE.sections:
            original=bytearray(PE.data[s['raw']:s['raw']+s['size']])
            changed=bytearray(q.read(q.base+s['rva'],s['size']))
            va=q.base+s['rva']
            if va<=a.SLOT<va+s['size']:
                off=a.SLOT-va;changed[off:off+4]=original[off:off+4]
            self.assertEqual(changed,original,s['name'])

    def test_refuses_unknown_or_stacked_images(self):
        for data in (BASE+b'x',PATCHED):
            with self.assertRaisesRegex(ValueError,'exact'):build(data)


if __name__=='__main__':unittest.main()
