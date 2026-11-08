"""Execute native StartBattle instructions/cleanup and guard sender-independent repeats."""
import json
import struct
import unittest
from pathlib import Path
from test_pause_ai_adapter import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn.x86_const import (UC_X86_REG_ESP,UC_X86_REG_ECX,UC_X86_REG_EAX,
    UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP)
from pe_image_readonly import PE32
from build_test_package import apply
import server_battle_phase_guard as a

ROOT=Path(__file__).resolve().parent
CODE,STATS,H,SP,DONE=0x30000000,0x30001000,0x32000000,0x33008000,0x34000000
SOURCE1,SOURCE2=H+0x1000,H+0x2000


class ServerPhaseGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.image=PE32((ROOT/'backups/NFSTR_Server.exe.headless-original').read_bytes())
    def put(self,u,address,value):u.mem_write(address,struct.pack('<I',value))
    def world(self,patched=True):
        u=Uc(UC_ARCH_X86,UC_MODE_32)
        for base in (0x400000,0x1300000,0x1800000,0x2200000,0x2800000,CODE,H,SP&~0xFFFF,DONE):u.mem_map(base,0x100000)
        u.mem_write(a.GATE,self.image.read(a.GATE,0x5F))  # include RET4's two-byte operand
        u.mem_write(a.ENABLE,self.image.read(a.ENABLE,5))
        u.mem_write(a.RESET,self.image.read(a.RESET,0x26))
        u.mem_write(CODE,a.make_code(CODE,STATS))
        if patched:
            for site,expected,offset in ((a.GATE,a.GATE_BYTES,0),(a.ENABLE,a.ENABLE_BYTES,a.ENABLE_OFFSET),(a.RESET,a.RESET_BYTES,a.RESET_OFFSET)):
                u.mem_write(site,b'\xe9'+struct.pack('<i',CODE+offset-site-5)+b'\x90'*(len(expected)-5))
        # External engine operations are stubs; the caller's real dispatch,
        # source+48 write, argument setup and cleanup execute from the EXE.
        u.mem_write(0x13C42B0,b'\xff\x05'+struct.pack('<I',H+0x800)+bytes.fromhex('c20800'))
        u.mem_write(0x13E0D10,bytes.fromhex('c20400'))
        u.mem_write(0x44B9E0,b'\xb8'+struct.pack('<I',H+0x9000)+bytes.fromhex('c20400'))
        u.mem_write(0x13DB730,b'\xff\x05'+struct.pack('<I',H+0x804)+bytes.fromhex('c20800'))
        for fn in (0x452240,0x467AF0,0x454220,0x2266D30,0x18507E0):u.mem_write(fn,b'\xc3')
        u.mem_write(0x1311E90,bytes.fromhex('c20400'))
        self.put(u,0x28E5C80,H+0x3000);self.put(u,H+0x3000,0x25B6D50);self.put(u,H+0x3010,H+0x4000)
        self.put(u,0x28A3228,H+0x5000)
        for source,data in ((SOURCE1,H+0x6000),(SOURCE2,H+0x7000)):
            self.put(u,source+0x14,data);u.mem_write(data+0x60,struct.pack('<f',50.))
        return u

    def start(self,u,source,rival):
        # Real handler frame at13E304F: four callee saves below its60-byte locals.
        body=SP-0x70
        u.mem_write(body,struct.pack('<4I',0xEE,0xBB,0xDD,0x55))
        u.mem_write(SP,struct.pack('<II',DONE,0))
        self.put(u,H+0x8000,rival)
        for reg,value in ((UC_X86_REG_ESP,body),(UC_X86_REG_ESI,source),(UC_X86_REG_EAX,H+0x8000),
                          (UC_X86_REG_EBX,H+0xA000),(UC_X86_REG_EBP,0xEE),(UC_X86_REG_EDI,0xDD)):
            u.reg_write(reg,value)
        u.emu_start(a.GATE,DONE,count=2500)
        self.assertEqual(u.reg_read(UC_X86_REG_ESP),SP+8)
        self.assertEqual([u.reg_read(r) for r in (UC_X86_REG_EBP,UC_X86_REG_EBX,UC_X86_REG_EDI,UC_X86_REG_ESI)],
                         [0xEE,0xBB,0xDD,0x55])
        return struct.unpack('<2I',u.mem_read(H+0x800,8))

    def reset(self,u):
        self.put(u,SP,DONE);u.reg_write(UC_X86_REG_ESP,SP)
        u.emu_start(a.RESET,DONE,count=1000)
        self.assertEqual(u.reg_read(UC_X86_REG_ESP),SP+4)

    def test_native_four_senders_reactivate_and_broadcast_four_times(self):
        u=self.world(False)
        for i in range(4):self.assertEqual(self.start(u,SOURCE1,3),(i+1,i+1))

    def test_four_senders_activate_and_broadcast_only_once(self):
        u=self.world()
        for _ in range(4):self.assertEqual(self.start(u,SOURCE1,3),(1,1))
        self.assertEqual(struct.unpack('<I',u.mem_read(STATS+4,4))[0],3)

    def test_late_previous_source_cannot_reactivate_old_opponent(self):
        u=self.world();self.start(u,SOURCE1,3);self.start(u,SOURCE2,4)
        self.assertEqual(self.start(u,SOURCE1,3),(2,2))
        self.assertEqual(struct.unpack('<I',u.mem_read(SOURCE2+0x48,4))[0],4)

    def test_new_rival_on_same_source_remains_native(self):
        u=self.world();self.start(u,SOURCE1,3)
        self.assertEqual(self.start(u,SOURCE1,4),(2,2))

    def test_enable_clears_only_its_source_history(self):
        u=self.world();self.start(u,SOURCE1,3);self.start(u,SOURCE2,4)
        u.reg_write(UC_X86_REG_ECX,SOURCE1);u.reg_write(UC_X86_REG_ESP,SP)
        u.emu_start(a.ENABLE,a.ENABLE_RESUME,count=1000)
        self.assertEqual(u.reg_read(UC_X86_REG_ESP),SP-0x4C-8)
        self.assertEqual(self.start(u,SOURCE1,3),(3,3))
        self.assertEqual(self.start(u,SOURCE2,4),(3,3))

    def test_global_reset_and_changed_challenge_allow_same_checkpoint_again(self):
        for change in ('reset','challenge'):
            u=self.world();self.start(u,SOURCE1,3)
            if change=='reset':self.reset(u)
            else:self.put(u,H+0x3010,H+0xB000)
            self.assertEqual(self.start(u,SOURCE1,3),(2,2))

    def test_missing_story_context_falls_back_natively(self):
        u=self.world();self.put(u,0x28E5C80,0)
        self.start(u,SOURCE1,3)
        self.assertEqual(self.start(u,SOURCE1,3),(2,2))

    def test_only_three_intended_sites_change_in_native_sections(self):
        from patch_server_battle_phase_guard import build
        patch=json.loads((ROOT/'outputs/TheRun-Coop-v0.7.2-TEST-CANDIDATE/patches/server.json').read_text())
        base=apply(self.image.data,patch);out,_,report=build(base)
        allowed=set()
        for site,expected in ((a.GATE,a.GATE_BYTES),(a.ENABLE,a.ENABLE_BYTES),(a.RESET,a.RESET_BYTES)):
            off=PE32(base).offset(site);allowed.update(range(off,off+len(expected)))
        diff={i for i,(x,y) in enumerate(zip(base,out)) if x!=y and i>=0x1000}
        self.assertLessEqual(diff,allowed)
        self.assertTrue(report['guard_before_actor_activation']);self.assertFalse(report['gameplay_verified'])
        with self.assertRaises(ValueError):build(out)


if __name__=='__main__':unittest.main()
