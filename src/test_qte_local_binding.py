"""Targeted native ABI/scope tests, not a simulated proof of QTE gameplay."""
import struct
import unittest
from pathlib import Path
from test_pause_ai_adapter import Uc, UC_ARCH_X86, UC_MODE_32
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *
from pe_image_readonly import PE32
import qte_local_event_adapter as a
import coop_hud_adapter as hud
from pause_ai_adapter import ONLINE
from qte_hud_scope_adapter import CHALLENGE_CONTROLLER

CODE, STATS, D, STACK, RET = 0x30000000, 0x30001000, 0x32000000, 0x33000000, 0x34000000


class BindingTests(unittest.TestCase):
    def machine(self, lan=True, mode=2, challenge=3, connected=3):
        u = self.u = Uc(UC_ARCH_X86, UC_MODE_32)
        for base in (0xE00000, 0x2800000, CODE, D, STACK, RET):
            u.mem_map(base, 0x100000)
        u.mem_write(CODE, a.make_code(CODE, STATS))
        u.mem_write(a.NATIVE, bytes.fromhex('8b442404c20800'))
        self.put(ONLINE, D); u.mem_write(D + 8, bytes([0 if lan else 1])); self.put(D + 0xA4, connected)
        self.put(hud.MODE, D + 0x1000); self.put(D + 0x1004, mode)
        self.put(CHALLENGE_CONTROLLER, D + 0x2000); self.put(D + 0x2010, D + 0x3000); self.put(D + 0x3028, challenge)
        self.put(a.PLAYERS, D + 0x4000)
        self.local = self.player(0, False)
        self.put(D + 0x40BC, self.local)
        return u

    def put(self, at, value):
        self.u.mem_write(at, struct.pack('<I', value))

    def player(self, index, bot=False, vt=a.PLAYER_VT):
        p = D + 0x10000 + index * 0x1000
        self.put(p, vt); self.put(p + 0x334, index + 7)
        self.u.mem_write(p + 0x260, bytes([int(bot)]))
        return p

    def call(self, original, second=0):
        u, sp = self.u, STACK + 0x8000
        stack = struct.pack('<4I', RET, original, second, 0xFEED)
        u.mem_write(sp, stack)
        regs = {UC_X86_REG_ECX: D + 0x5000, UC_X86_REG_EDX: 0xDADA,
                UC_X86_REG_EBX: 0xBBBB, UC_X86_REG_ESI: D + 0x6000,
                UC_X86_REG_EDI: 0xDDDD, UC_X86_REG_EBP: 0xEEEE}
        # ESI represents the unchanged received message, not a player override.
        u.mem_write(D + 0x6038, struct.pack('<3I', 14, 7, 0x1234))
        for reg, value in regs.items(): u.reg_write(reg, value)
        u.reg_write(UC_X86_REG_ESP, sp); u.reg_write(UC_X86_REG_EFLAGS, 0xA93)
        u.reg_write(UC_X86_REG_XMM0, 0x12345678)
        entered = []

        def native(uc, at, size, user):
            if at == a.NATIVE:
                entered.append(struct.unpack('<3I', uc.mem_read(sp, 12)))
                self.assertEqual(uc.reg_read(UC_X86_REG_ESP), sp)
                for reg, value in regs.items(): self.assertEqual(uc.reg_read(reg), value)
                self.assertEqual(uc.reg_read(UC_X86_REG_EFLAGS) & 0xCD5, 0xA93 & 0xCD5)

        hook = u.hook_add(UC_HOOK_CODE, native)
        try: u.emu_start(CODE, RET, count=1000)
        finally: u.hook_del(hook)
        self.assertEqual(len(entered), 1)
        self.assertEqual(u.reg_read(UC_X86_REG_ESP), sp + 12)
        self.assertEqual(u.reg_read(UC_X86_REG_XMM0), 0x12345678)
        self.assertEqual(bytes(u.mem_read(D + 0x6038, 12)), struct.pack('<3I', 14, 7, 0x1234))
        self.assertEqual(bytes(u.mem_read(sp + 12, 4)), struct.pack('<I', 0xFEED))
        return entered[0][1]

    def test_remote_humans_bind_to_each_of_two_to_four_local_players(self):
        for count in (2, 3, 4):
            for local in range(count):
                for source in range(count):
                    self.machine()
                    players = [self.player(i) for i in range(count)]
                    self.put(D + 0x40BC, players[local])
                    self.assertEqual(self.call(players[source]), players[local])

    def test_solo_driving_disconnected_and_nonstory_are_exact_native(self):
        for settings in ({'lan': False}, {'mode': 1}, {'challenge': 0}, {'challenge': 2}, {'connected': 0}):
            self.machine(**settings); p = self.player(1)
            self.assertEqual(self.call(p), p)

    def test_bot_or_unknown_source_is_not_rebound(self):
        for bot, vt in ((True, a.PLAYER_VT), (False, 0x1234)):
            self.machine(); p = self.player(1, bot, vt)
            self.assertEqual(self.call(p), p)
        self.machine(); self.assertEqual(self.call(0), 0)

    def test_missing_local_or_schema_or_nonzero_second_argument_is_native(self):
        for has_bot_local in (False, True):
            self.machine(); p = self.player(1)
            self.put(D + 0x40BC, self.player(2, True) if has_bot_local else 0)
            self.assertEqual(self.call(p), p)
        self.machine(); p = self.player(1); self.assertEqual(self.call(p, second=9), p)

    def test_exact_native_contracts_in_game_file(self):
        image = PE32(Path(r'X:\EA Games\Need for Speed The Run\Need for Speed The Run\Need For Speed The Run.exe').read_bytes())
        self.assertEqual(image.read(a.SITE, 5), a.call_patch(a.NATIVE))
        self.assertEqual(image.read(0xF26530, 7), bytes.fromhex('8b81bc000000c3'))
        self.assertEqual(image.read(0xF42020, 7), bytes.fromhex('8a8160020000c3'))
        self.assertEqual(struct.unpack('<I', image.read(a.PLAYER_VT + 0x18, 4))[0], 0xF42020)
        self.assertEqual(image.read(a.NATIVE, 8), bytes.fromhex('8b442408568bf18b'))


if __name__ == '__main__':
    unittest.main()
