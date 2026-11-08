"""Unicorn tests for the DRAFT pause_ai_adapter (client).

Stubs: native E5DA70 (pause) logs its call; native F29820 (AI switch) logs (entity, enable, a2, a3).
"""
import json
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'outputs/test-libs'))
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32  # noqa: E402
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_ECX, UC_X86_REG_ESI, UC_X86_REG_EDI  # noqa: E402
import pause_ai_adapter as a  # noqa: E402
from checkpoint_humans_adapter import Code  # noqa: E402

CLIENT = ROOT / 'backups/Need For Speed The Run.exe.lan-before-road-reset'
V06 = ROOT / 'outputs/TheRun-Coop-v0.6-TEST-Final/patches/client.json'
ADAPTER, STATS, LOG, DATA, STACK, RETURN = 0x30000000, 0x30001000, 0x31000000, 0x32000000, 0x33000000, 0x34000000
AILOG = LOG + 0x100


def logger(base, target, ret):
    """Stub: append ecx + 3 stack args to a log at target, RET ret."""
    c = Code(base)
    c.emit('8b15'); c.data += struct.pack('<I', target)          # edx = cursor
    c.emit('890a')                                               # [edx] = ecx
    for i, disp in enumerate(('04', '08', '0c')):
        c.emit('8b4424' + disp); c.emit('89420' + str(4 + 4 * i) if 4 + 4 * i < 10 else '89420c')
    c.emit('8305'); c.data += struct.pack('<I', target); c.emit('10')
    c.emit('c2' + struct.pack('<H', ret).hex())
    return c.finish()


class PauseAiTests(unittest.TestCase):
    def setUp(self):
        u = self.u = Uc(UC_ARCH_X86, UC_MODE_32)
        for base in (0xE00000, 0x2800000, 0x30000000, 0x31000000, 0x32000000, 0x33000000, 0x34000000):
            u.mem_map(base, 0x200000)
        u.mem_write(ADAPTER, a.make_code(ADAPTER, STATS))
        u.mem_write(a.NATIVE, logger(a.NATIVE, LOG, 0xC))
        u.mem_write(a.SET_AI_CONTROL, logger(a.SET_AI_CONTROL, AILOG, 0xC))
        self.put(LOG, LOG + 0x10); self.put(AILOG, AILOG + 0x10)
        self.online, self.player, self.entity, self.vehicle = DATA, DATA + 0x1000, DATA + 0x2000, DATA + 0x4000
        self.world()

    def put(self, address, value):
        self.u.mem_write(address, struct.pack('<I', value))

    def byte(self, address, value):
        self.u.mem_write(address, bytes([value]))

    def world(self, lan=True, connected=3, entity=None):
        entity = entity or self.entity
        self.put(a.ONLINE, self.online); self.byte(self.online + 8, 0 if lan else 1); self.put(self.online + 0xA4, connected)
        self.put(a.PLAYERS, DATA + 0x800); self.put(DATA + 0x800 + 0xBC, self.player)
        self.put(self.player + 0x318, entity); self.put(entity, a.ENTITY_VT)
        self.put(entity + 0xE4, self.vehicle); self.put(self.vehicle, a.VEHICLE_VT)

    def log(self, base):
        end = struct.unpack('<I', self.u.mem_read(base, 4))[0]
        n = (end - base - 0x10) // 16
        return [struct.unpack('<4I', self.u.mem_read(base + 0x10 + 16 * i, 16)) for i in range(n)]

    def pause(self, paused, flag29=0):
        sp = STACK + 0x10000
        self.u.mem_write(sp, struct.pack('<4I', RETURN, paused, 1, flag29))
        self.u.reg_write(UC_X86_REG_ESP, sp)
        self.u.reg_write(UC_X86_REG_ECX, 0x6A3E)
        self.u.reg_write(UC_X86_REG_ESI, 0x5151); self.u.reg_write(UC_X86_REG_EDI, 0x7171)
        self.u.emu_start(ADAPTER, RETURN, count=5000)
        self.assertEqual(self.log(LOG)[-1], (0x6A3E, paused, 1, flag29))   # native pause always, unchanged
        self.assertEqual(self.u.reg_read(UC_X86_REG_ESP), sp + 16)
        self.assertEqual((self.u.reg_read(UC_X86_REG_ESI), self.u.reg_read(UC_X86_REG_EDI)), (0x5151, 0x7171))

    def state(self):
        return struct.unpack('<6I', self.u.mem_read(STATS, 24))

    def test_lan_pause_enables_ai_and_resume_disables(self):
        self.pause(1)
        self.assertEqual(self.log(AILOG), [(self.entity, 1, 0, 0)])
        self.pause(0)
        self.assertEqual(self.log(AILOG), [(self.entity, 1, 0, 0), (self.entity, 0, 0, 0)])
        s = self.state()
        self.assertEqual((s[a.ACTIVE // 4], s[a.ENGAGED // 4], s[a.RESTORED // 4]), (0, 1, 1))

    def test_double_pause_enables_once(self):
        self.pause(1); self.pause(1); self.pause(0)
        self.assertEqual([r[1] for r in self.log(AILOG)], [1, 0])

    def test_resume_without_engage_does_nothing(self):
        self.pause(0)
        self.assertEqual(self.log(AILOG), [])

    def test_singleplayer_and_disconnected_untouched(self):
        for kwargs in (dict(lan=False), dict(connected=2)):
            self.world(**kwargs)
            self.pause(1); self.pause(0)
        self.assertEqual(self.log(AILOG), [])

    def test_cutscene_owned_car_untouched(self):
        for flag in (0xA7C, 0xA7D):
            self.byte(self.vehicle + 0xA7C, 0); self.byte(self.vehicle + 0xA7D, 0)
            self.byte(self.vehicle + flag, 1)
            self.pause(1)
        self.assertEqual(self.log(AILOG), [])
        self.assertEqual(self.state()[a.SKIPPED_OWNED // 4], 2)

    def test_native_ai_state_already_set_untouched(self):
        self.byte(self.entity + 0xD0, 1)
        self.pause(1); self.pause(0)
        self.assertEqual(self.log(AILOG), [])
        self.assertEqual(self.state()[a.SKIPPED_AI // 4], 1)

    def test_without_ai_state_guard_engages_even_if_d0_set(self):
        self.u.mem_write(ADAPTER, a.make_code(ADAPTER, STATS, guard_ai_state=False))
        self.byte(self.entity + 0xD0, 1)
        self.pause(1); self.pause(0)
        self.assertEqual([r[1] for r in self.log(AILOG)], [1, 0])

    def test_entity_changed_during_pause_is_not_switched_back(self):
        self.pause(1)
        other = DATA + 0x8000
        self.world(entity=other)
        self.pause(0)
        self.assertEqual(self.log(AILOG), [(self.entity, 1, 0, 0)])
        self.assertEqual(self.state()[a.ACTIVE // 4], 0)

    def test_wrong_vtable_untouched(self):
        self.put(self.vehicle, 0x1234)
        self.pause(1)
        self.assertEqual(self.log(AILOG), [])

    @unittest.skipUnless(CLIENT.is_file() and V06.is_file(), 'client backup or v0.6 patch missing')
    def test_native_facts_and_builder_on_v06_client(self):
        from build_test_package import apply
        from pe_image_readonly import PE32
        from probe_lifecycle import call_bytes
        from patch_pause_ai import build
        from static_xref import Image
        v06 = apply(CLIENT.read_bytes(), json.loads(V06.read_text(encoding='utf-8-sig')))
        img = PE32(v06)
        self.assertEqual(img.read(a.SITE, 5), call_bytes(a.SITE, a.NATIVE))
        self.assertEqual(img.read(0xF29820, 6), bytes.fromhex('83ec40558be9'))   # sub esp,40; push ebp; mov ebp,ecx
        self.assertEqual(img.read(0xF298AC, 3), bytes.fromhex('c20c00'))         # RET 0xC
        self.assertEqual(img.read(0xF27380, 7), bytes.fromhex('8a81d0000000c3'))  # mov al,[ecx+D0]; ret
        # AIControlSetter Enable path pushes (x,0,1) then calls F29820 at 990641.
        self.assertEqual(img.read(0x990634, 4), bytes.fromhex('6a006a01'))
        self.assertEqual(img.read(0x990641, 5), call_bytes(0x990641, 0xF29820))
        patched, _, report = build(v06)
        self.assertEqual(PE32(patched).read(a.SITE, 5), call_bytes(a.SITE, report['layout']['adapter']))


if __name__ == '__main__':
    unittest.main()
