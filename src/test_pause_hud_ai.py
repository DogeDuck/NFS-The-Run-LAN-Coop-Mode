"""Execute the real HUD-state adapter in Unicorn; no live game access."""
import json
import struct
import test_pause_ai_adapter as pause_tests
from test_pause_ai_adapter import ADAPTER, STATS, LOG, AILOG, DATA, STACK, RETURN, CLIENT, V06, logger
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_ECX, UC_X86_REG_ESI, UC_X86_REG_EDI
import pause_ai_adapter as a


class HudPauseAiTests(pause_tests.PauseAiTests):
    def setUp(self):
        super().setUp()
        self.hud = DATA + 0x10000
        self.u.mem_write(ADAPTER, a.make_code(ADAPTER, STATS, hud_state=True))
        self.u.mem_write(a.HUD_NATIVE, logger(a.HUD_NATIVE, LOG, 0))

    def pause(self, paused, flag29=0):
        self.tick(2 if paused else 1, paused, flag29)

    def tick(self, state, paused=0, flag29=0):
        self.put(self.hud + 0x64, state)
        sp = STACK + 0x10000
        self.u.mem_write(sp, struct.pack('<4I', RETURN, paused, 1, flag29))
        self.u.reg_write(UC_X86_REG_ESP, sp)
        self.u.reg_write(UC_X86_REG_ECX, 0x6A3E)
        self.u.reg_write(UC_X86_REG_ESI, self.hud)
        self.u.reg_write(UC_X86_REG_EDI, 0x7171)
        self.u.emu_start(ADAPTER, RETURN, count=5000)
        self.assertEqual(self.log(LOG)[-1], (0x6A3E, paused, 1, flag29))
        self.assertEqual(self.u.reg_read(UC_X86_REG_ESP), sp + 4)
        self.assertEqual((self.u.reg_read(UC_X86_REG_ESI), self.u.reg_read(UC_X86_REG_EDI)), (self.hud, 0x7171))

    def test_without_ai_state_guard_engages_even_if_d0_set(self):
        self.u.mem_write(ADAPTER, a.make_code(ADAPTER, STATS, guard_ai_state=False, hud_state=True))
        self.byte(self.entity + 0xD0, 1)
        self.pause(1); self.pause(0)
        self.assertEqual([r[1] for r in self.log(AILOG)], [1, 0])

    def test_invalid_hud_state_does_not_switch_ai(self):
        for state in (0, 3, 0xFFFFFFFF):
            self.tick(state)
        self.assertEqual(self.log(AILOG), [])

    def test_native_facts_and_builder_on_v06_client(self):
        from build_test_package import apply
        from patch_pause_ai import build
        from pe_image_readonly import PE32
        from probe_lifecycle import call_bytes
        base = apply(CLIENT.read_bytes(), json.loads(V06.read_text(encoding='utf-8-sig')))
        patched, _, report = build(base, guard_ai_state=False, hud_state=True)
        self.assertEqual(PE32(patched).read(a.HUD_SITE, 5), call_bytes(a.HUD_SITE, report['layout']['adapter']))
        self.assertEqual(PE32(patched).read(a.SITE, 5), PE32(base).read(a.SITE, 5))
        changed = bytearray(base)
        from patch_headless_reset import file_offset
        changed[file_offset(changed, 0x900ECE)] ^= 1
        with self.assertRaisesRegex(ValueError, 'contract changed'):
            build(bytes(changed), guard_ai_state=False, hud_state=True)


if __name__ == '__main__':
    import unittest
    unittest.main()
