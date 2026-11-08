"""Run the actual native990A50 handler; stub only its external lead/win callbacks."""
import json
import struct
import unittest
from pathlib import Path
from test_pause_ai_adapter import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn.x86_const import (UC_X86_REG_ESP,UC_X86_REG_ECX,UC_X86_REG_EBX,
    UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP,UC_X86_REG_EFLAGS)
from build_test_package import apply
from pe_image_readonly import PE32
from probe_lifecycle import call_bytes
from coop_hud_adapter import ONLINE,MODE
import battle_phase_guard_adapter as a

ROOT=Path(__file__).resolve().parent
CODE,STATS,H,SP,DONE=0x30000000,0x30001000,0x32000000,0x33008000,0x34000000
ROOT_ENTITY,MSG=H+0x1000,H+0x2000


class BattlePhaseGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.image=PE32((ROOT/'backups/Need For Speed The Run.exe.lan-before-road-reset').read_bytes())

    def world(self,patched=True,solo=0,connected=3,mode=2):
        u=Uc(UC_ARCH_X86,UC_MODE_32)
        for base in (0x900000,0x2300000,0x2800000,CODE,H,SP&~0xFFFF,DONE):u.mem_map(base,0x100000)
        u.mem_write(a.SITE,self.image.read(a.SITE,0xD0))
        u.mem_write(0x23DD828,self.image.read(0x23DD828,4))
        u.mem_write(CODE,a.make_code(CODE,STATS))
        if patched:u.mem_write(a.SITE,b'\xe9'+struct.pack('<i',CODE-a.SITE-5)+b'\x90')
        # Lead returns true (the shared comparator is tested separately).
        u.mem_write(0x98C640,bytes.fromhex('b801000000c20800'))
        # Native98C830's counter increment and state2; network/UI are not under test.
        u.mem_write(0x98C830,bytes.fromhex('ff819c000000c7819400000002000000c3'))
        self.put(u,ONLINE,H+0x3000);u.mem_write(H+0x3008,bytes([solo]));self.put(u,H+0x30A4,connected)
        self.put(u,MODE,H+0x4000);self.put(u,H+0x4004,mode)
        self.put(u,0x28824E8,H+0x5000);self.put(u,H+0x5010,H+0x6000)
        u.mem_write(ROOT_ENTITY+0x24,b'\x01');self.put(u,ROOT_ENTITY+0x14,H+0x7000)
        return u

    def put(self,u,address,value):u.mem_write(address,struct.pack('<I',value))
    def float(self,u,address,value):u.mem_write(address,struct.pack('<f',value))
    def state(self,u):
        return (struct.unpack('<I',u.mem_read(ROOT_ENTITY+0x9C,4))[0],
                struct.unpack('<I',u.mem_read(ROOT_ENTITY+0xA8,4))[0],
                struct.unpack('<f',u.mem_read(ROOT_ENTITY+0x98,4))[0])

    def packet(self,u,rival=2,timer=50.,state=0,message=a.START_MESSAGE):
        self.put(u,MSG+8,message);self.float(u,MSG+0x38,timer)
        self.put(u,MSG+0x3C,rival);self.put(u,MSG+0x40,3);self.put(u,MSG+0x44,state)
        u.mem_write(SP,struct.pack('<II',DONE,MSG))
        initial={UC_X86_REG_EBX:0xBB,UC_X86_REG_ESI:0x55,UC_X86_REG_EDI:0xDD,UC_X86_REG_EBP:0xEE}
        for reg,value in initial.items():u.reg_write(reg,value)
        u.reg_write(UC_X86_REG_ECX,ROOT_ENTITY+0x8C);u.reg_write(UC_X86_REG_ESP,SP)
        u.reg_write(UC_X86_REG_EFLAGS,0x246)
        u.emu_start(a.SITE,DONE,count=2500)
        self.assertEqual(u.reg_read(UC_X86_REG_ESP),SP+8)
        for reg,value in initial.items():self.assertEqual(u.reg_read(reg),value)
        return self.state(u)

    def test_native_duplicate_reproduces_live_double_count_at49_seconds(self):
        u=self.world(patched=False)
        self.packet(u,2);self.float(u,ROOT_ENTITY+0x98,0.)
        self.put(u,ROOT_ENTITY+0x9C,1)  # opponent2 already won by timer
        self.packet(u,3);self.float(u,ROOT_ENTITY+0x98,49.5)
        self.assertEqual(self.packet(u,3),(2,3,50.))

    def test_duplicate_neither_counts_nor_restarts_current_countdown(self):
        u=self.world();self.packet(u,2)
        self.float(u,ROOT_ENTITY+0x98,0.);self.put(u,ROOT_ENTITY+0x9C,1)
        self.packet(u,3);self.float(u,ROOT_ENTITY+0x98,49.5)
        self.assertEqual(self.packet(u,3),(1,3,49.5))
        self.assertEqual(struct.unpack('<I',u.mem_read(STATS+4,4))[0],1)

    def test_four_players_can_report_same_checkpoint_only_first_advances(self):
        # Four senders' broadcasts observed by one client; no four-instance test.
        u=self.world();self.packet(u,2);self.float(u,ROOT_ENTITY+0x98,35.)
        self.assertEqual(self.packet(u,3),(1,3,50.))
        self.float(u,ROOT_ENTITY+0x98,48.)
        for _ in range(3):self.assertEqual(self.packet(u,3),(1,3,48.))
        self.assertEqual(struct.unpack('<I',u.mem_read(STATS+4,4))[0],3)

    def test_first_checkpoint_transition_still_wins_before_countdown_end(self):
        u=self.world();self.packet(u,2);self.float(u,ROOT_ENTITY+0x98,35.)
        self.assertEqual(self.packet(u,3),(1,3,50.))

    def test_timer_then_checkpoint_does_not_win_twice(self):
        u=self.world();self.packet(u,2)
        self.float(u,ROOT_ENTITY+0x98,0.);self.put(u,ROOT_ENTITY+0x9C,1)
        self.assertEqual(self.packet(u,3),(1,3,50.))
        self.float(u,ROOT_ENTITY+0x98,42.)
        self.assertEqual(self.packet(u,3),(1,3,42.))

    def test_late_old_checkpoint_cannot_reverse_phase_or_defeat_new_rival(self):
        u=self.world();self.packet(u,2);self.packet(u,3);self.packet(u,4)
        self.float(u,ROOT_ENTITY+0x98,31.)
        self.assertEqual(self.packet(u,3),(2,4,31.))
        self.assertEqual(self.packet(u,2),(2,4,31.))

    def test_native_reset_allows_same_opponent_after_retry(self):
        u=self.world();self.packet(u,2);self.packet(u,3)
        self.packet(u,message=a.RESET_MESSAGE)
        self.assertEqual(self.packet(u,2),(0,2,50.))

    def test_changed_challenge_and_entity_data_start_new_generation(self):
        for address in (H+0x5010,ROOT_ENTITY+0x14):
            u=self.world();self.packet(u,2);self.packet(u,3)
            self.put(u,address,H+0x8000)
            before=self.state(u)[0]
            self.packet(u,2)
            self.assertEqual(self.state(u)[:2],(before+1,2))

    def test_nonstart_updates_and_other_modes_remain_native(self):
        u=self.world();self.packet(u,2)
        self.assertEqual(self.packet(u,2,timer=12.,state=1),(0,2,12.))
        for kwargs in (dict(solo=1),dict(connected=2),dict(mode=1),dict(mode=3)):
            u=self.world(**kwargs);self.packet(u,2)
            self.assertEqual(self.packet(u,2),(1,2,50.))

    def test_inactive_handler_does_not_dereference_packet(self):
        u=self.world();u.mem_write(ROOT_ENTITY+0x24,b'\0')
        u.mem_write(SP,struct.pack('<II',DONE,0))
        u.reg_write(UC_X86_REG_ECX,ROOT_ENTITY+0x8C);u.reg_write(UC_X86_REG_ESP,SP)
        u.emu_start(a.SITE,DONE,count=100)
        self.assertEqual(u.reg_read(UC_X86_REG_ESP),SP+8)

    def test_code_patch_composes_with_bot_filter_and_keeps_native_win_sites(self):
        from patch_battle_phase_guard import build
        from patch_claude_battle_botfilter import build as bot_filter
        patch=json.loads((ROOT/'outputs/TheRun-Coop-v0.7.2-TEST-CANDIDATE/patches/client.json').read_text())
        original=apply(self.image.data,patch)
        for base in (original,bot_filter(original)[0]):
            out,_,report=build(base)
            self.assertEqual(PE32(out).read(0x990BBB,5),call_bytes(0x990BBB,0x98C830))
            self.assertEqual(PE32(out).read(0x990AF2,5),call_bytes(0x990AF2,0x98C830))
            self.assertFalse(report['gameplay_verified'])
            with self.assertRaises(ValueError):build(out)


if __name__=='__main__':unittest.main()
