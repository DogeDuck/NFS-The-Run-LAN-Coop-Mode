"""Execute HUD adapters in Unicorn; no process writes or guessed gap values."""
import struct
import unittest
from pathlib import Path
from test_pause_ai_adapter import Uc,UC_ARCH_X86,UC_MODE_32,CLIENT,V06
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ECX,UC_X86_REG_EBX,UC_X86_REG_EDI,UC_X86_REG_ESI,UC_X86_REG_EBP
import coop_hud_adapter as a

B,S,D,SP=0x30000000,0x30001000,0x32000000,0x33001008


class HudTests(unittest.TestCase):
    def setUp(self):
        self.u=Uc(UC_ARCH_X86,UC_MODE_32)
        for base,size in ((0x900000,0x200000),(0x2800000,0x200000),(B,0x2000),(D,0x2000),(SP&~0xFFFF,0x20000)):
            self.u.mem_map(base,size)
        self.u.mem_write(B,a.make_code(B,S))
        self.world()

    def put(self,addr,value):self.u.mem_write(addr,struct.pack('<I',value))

    def world(self,solo=0,connected=3,mode=2):
        self.put(a.ONLINE,D);self.u.mem_write(D+8,bytes([solo]));self.put(D+0xA4,connected)
        self.put(a.MODE,D+0x100);self.put(D+0x104,mode)

    def policy(self):
        self.u.mem_write(SP+9,b'\0\1\0')
        self.u.reg_write(UC_X86_REG_ESP,SP)
        self.u.reg_write(UC_X86_REG_EBX,0xAABBCCDD)
        self.u.reg_write(UC_X86_REG_EDI,0x12345678)
        self.u.emu_start(B,a.POLICY_RETURN,count=1000)
        self.assertEqual(self.u.reg_read(UC_X86_REG_ESP),SP-8)
        self.assertEqual(self.u.reg_read(UC_X86_REG_EBX),0xAABBCC00)
        self.assertEqual(struct.unpack('<2I',self.u.mem_read(SP-8,8)),(0x12345678,0xAABBCCDD))
        return bytes(self.u.mem_read(SP+9,3))

    def visible(self,widget,enabled=1):
        self.u.mem_write(SP,struct.pack('<3I',0x11111111,widget,enabled))
        self.u.reg_write(UC_X86_REG_ESP,SP)
        self.u.reg_write(UC_X86_REG_ECX,0x12345678)
        self.u.reg_write(UC_X86_REG_ESI,0x87654321)
        self.u.emu_start(B+a.VISIBILITY_OFFSET,a.VISIBILITY_RETURN,count=1000)
        self.assertEqual(self.u.reg_read(UC_X86_REG_ECX),0x12345678)
        self.assertEqual(self.u.reg_read(UC_X86_REG_ESI),0x87654321)
        self.assertEqual(self.u.reg_read(UC_X86_REG_EBP),SP-4)
        self.assertEqual(self.u.reg_read(UC_X86_REG_ESP),(SP-4)&~15)
        self.assertEqual(struct.unpack('<I',self.u.mem_read(SP+4,4))[0],widget)
        return struct.unpack('<I',self.u.mem_read(SP+8,4))[0]

    def test_story_lan_selects_native_career_hud_only(self):
        self.assertEqual(self.policy(),b'\1\0\0')
        self.assertEqual(struct.unpack('<I',self.u.mem_read(D+0x104,4))[0],2)

    def test_story_clock_and_autolog_panel_hidden(self):
        self.assertEqual(self.visible(a.RACE_TIMER),0)
        self.assertEqual(self.visible(a.SPLIT_TIMES),0)

    def test_other_widgets_remain_native_including_countdown(self):
        for widget in (0,1,2,3,4,5,7,9,10,22):
            for requested in (0,1):
                self.assertEqual(self.visible(widget,requested),requested)

    def test_sp_disconnected_and_other_modes_remain_native(self):
        for kwargs in (dict(solo=1),dict(connected=2),dict(mode=1),dict(mode=3)):
            self.world(**kwargs)
            self.assertEqual(self.policy(),b'\0\1\0')
            self.assertEqual(self.visible(a.RACE_TIMER),1)

    def test_missing_globals_remain_native(self):
        for address in (a.MODE,a.ONLINE):
            self.world();self.put(address,0)
            self.assertEqual(self.policy(),b'\0\1\0')
            self.assertEqual(self.visible(a.SPLIT_TIMES),1)

    def test_builder_composes_with_pause_and_rejects_changed_site(self):
        import json
        from build_test_package import apply
        from patch_pause_ai import build as pause_build
        from patch_coop_hud import build
        from pe_image_readonly import PE32
        from patch_headless_reset import file_offset
        base=apply(CLIENT.read_bytes(),json.loads(V06.read_text(encoding='utf-8-sig')))
        paused,_,_=pause_build(base,False,True)
        patched,_,report=build(paused)
        self.assertFalse(report['race_data_modified'])
        self.assertEqual(PE32(patched).read(a.POLICY_SITE,1),b'\xe9')
        self.assertEqual(PE32(patched).read(a.VISIBILITY_SITE,1),b'\xe9')
        bad=bytearray(base);bad[file_offset(bad,a.POLICY_SITE)]^=1
        with self.assertRaisesRegex(ValueError,'contract changed'):build(bytes(bad))


if __name__=='__main__':unittest.main()
