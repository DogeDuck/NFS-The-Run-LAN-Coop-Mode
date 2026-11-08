"""Unicorn tests for battle_team_lead_adapter with the real client bytes of 98C640, 8635B0, F26530."""
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'outputs/test-libs'))
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE  # noqa: E402
from unicorn.x86_const import (UC_X86_REG_ESP, UC_X86_REG_ECX, UC_X86_REG_EAX, UC_X86_REG_EBX,  # noqa: E402
                               UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP, UC_X86_REG_EIP)
import battle_team_lead_adapter as a  # noqa: E402
from coop_hud_adapter import ONLINE, MODE

IMAGE = ROOT / 'backups/Need For Speed The Run.exe.lan-before-road-reset'
CODE, STATS, HEAP, STACK, RET = 0x30000000, 0x30001000, 0x32000000, 0x33000000, 0x34000000
PMGR, RMGR, BATTLE = HEAP + 0x1000, HEAP + 0x2000, HEAP + 0x3000


@unittest.skipUnless(IMAGE.is_file(), 'client backup missing')
class BattleTeamLeadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pe_image_readonly import PE32
        pe = PE32(IMAGE.read_bytes())
        cls.native = pe.read(a.SITE, 0x84)
        assert cls.native[:10] == a.SITE_BYTES
        cls.lookup = pe.read(a.LOOKUP, 0x2A)
        cls.local = pe.read(0xF26530, 7)
        cls.bot_getter = pe.read(a.BOT_GETTER, 7)
        cls.bot_slot = pe.read(a.PLAYER_VTABLE + 0x18, 4)

    def world(self, racers, humans, rival_id, local_id=0, patched=True, bots=(),
              invalid_flag=False, invalid_vtable=False, solo=False, connected=3, mode=2):
        """racers: {id: progress}; humans: player vector IDs (can include bots)."""
        u = Uc(UC_ARCH_X86, UC_MODE_32)
        for base in (0x800000, 0x900000, 0xF00000, 0x2800000, CODE, HEAP, STACK, RET):
            u.mem_map(base, 0x100000)
        u.mem_write(a.SITE, self.native)
        if patched:
            u.mem_write(a.SITE, b'\xe9' + struct.pack('<i', CODE - a.SITE - 5) + b'\x90' * 5)
        u.mem_write(a.LOOKUP, self.lookup)
        u.mem_write(0xF26530, self.local)
        u.mem_write(CODE, a.make_code(CODE, STATS))
        put = lambda addr, v: u.mem_write(addr, struct.pack('<I', v))
        putf = lambda addr, v: u.mem_write(addr, struct.pack('<f', v))
        put(ONLINE, HEAP + 0x100); u.mem_write(HEAP + 0x108, bytes([solo]))
        put(HEAP + 0x1A4, connected)
        put(MODE, HEAP + 0x200); put(HEAP + 0x204, mode)
        # racers
        arr = HEAP + 0x4000
        for i, (rid, prog) in enumerate(racers.items()):
            r = HEAP + 0x5000 + 0x100 * i
            put(arr + 4 * i, r); put(r + 0x10, rid); putf(r + 0x24, prog)
        put(RMGR + 0x3C, arr); put(RMGR + 0x40, arr + 4 * len(racers)); put(a.RACERS, RMGR)
        # human players (+334 id), local player at +BC with vtable+10 -> local id
        harr = HEAP + 0x8000
        for i, pid in enumerate(humans):
            p = HEAP + 0x9000 + 0x400 * i
            put(harr + 4 * i, p); put(p + 0x334, pid)
            put(p, 0 if invalid_vtable else a.PLAYER_VTABLE)
            u.mem_write(p + 0x260, bytes([2 if invalid_flag else int(pid in bots)]))
        put(PMGR + 0x9C, harr); put(PMGR + 0xA0, harr + 4 * len(humans)); put(a.PLAYERS, PMGR)
        lp = HEAP + 0xE000
        put(PMGR + 0xBC, lp); put(lp, HEAP + 0xE800); put(HEAP + 0xE810, HEAP + 0xE900)
        u.mem_write(HEAP + 0xE900, b'\xb8' + struct.pack('<I', local_id) + b'\xc3')
        put(BATTLE + 0xA8, rival_id)
        u.mem_write(RET, b'\xf4')
        return u

    def call(self, u):
        esp = STACK + 0x8000
        outl, outr = HEAP + 0xF000, HEAP + 0xF010
        u.mem_write(outl, struct.pack('<ff', -1.0, -1.0)); u.mem_write(outr, struct.pack('<f', -1.0))
        u.mem_write(esp, struct.pack('<III', RET, outl, outr))
        u.reg_write(UC_X86_REG_ESP, esp); u.reg_write(UC_X86_REG_ECX, BATTLE)
        for reg, v in ((UC_X86_REG_EBX, 0xB0B), (UC_X86_REG_ESI, 0x51), (UC_X86_REG_EDI, 0xD1), (UC_X86_REG_EBP, 0xBB)):
            u.reg_write(reg, v)
        u.hook_add(UC_HOOK_CODE, lambda uc, addr, size, d: uc.emu_stop() if addr == RET else None)
        u.emu_start(a.SITE, 0, count=2000)
        self.assertEqual(u.reg_read(UC_X86_REG_EIP), RET)
        self.assertEqual(u.reg_read(UC_X86_REG_ESP), esp + 12)          # RET 8
        self.assertEqual([u.reg_read(r) for r in (UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP)],
                         [0xB0B, 0x51, 0xD1, 0xBB])
        loc = struct.unpack('<f', u.mem_read(outl, 4))[0]
        riv = struct.unpack('<f', u.mem_read(outr, 4))[0]
        return u.reg_read(UC_X86_REG_EAX) & 0xFF, loc, riv

    RACE = {0: 81.0, 1: 40.0, 2: 17.8, 3: 55.0, 4: 78.2}        # host 81, guest 40, rival 4 at 78.2

    def test_host_ahead_counts_for_guest_client(self):
        for local in (0, 1):
            with self.subTest(local=local):
                lead, loc, riv = self.call(self.world(self.RACE, [0, 1], rival_id=4, local_id=local))
                self.assertEqual((lead, round(loc, 1), round(riv, 1)), (1, 81.0, 78.2))

    def test_both_behind_is_not_leading(self):
        race = {**self.RACE, 0: 50.0}
        lead, loc, riv = self.call(self.world(race, [0, 1], rival_id=4, local_id=1))
        self.assertEqual((lead, round(loc, 1)), (0, 50.0))

    def test_teammate_is_never_an_opponent(self):
        lead, loc, riv = self.call(self.world(self.RACE, [0, 1], rival_id=0, local_id=1))
        self.assertEqual(lead, 1)

    def test_missing_rival_is_leading_like_native(self):
        self.assertEqual(self.call(self.world(self.RACE, [0, 1], rival_id=9))[0], 1)

    def test_no_human_racer_is_not_leading(self):
        racers = {2: 10.0, 3: 20.0, 4: 30.0}
        self.assertEqual(self.call(self.world(racers, [0, 1], rival_id=4))[0], 0)

    def test_four_humans_any_order(self):
        racers = {5: 10.0, 2: 99.0, 7: 30.0, 3: 20.0, 9: 50.0}
        lead, loc, riv = self.call(self.world(racers, [3, 5, 7, 2], rival_id=9))
        self.assertEqual((lead, round(loc, 1)), (1, 99.0))

    def test_single_human_equals_native(self):
        race = {0: 30.0, 4: 40.0}
        for patched in (True, False):
            with self.subTest(patched=patched):
                self.assertEqual(self.call(self.world(race, [0], rival_id=4, patched=patched))[0], 0)
        race = {0: 45.0, 4: 40.0}
        self.assertEqual(self.call(self.world(race, [0], rival_id=4))[0],
                         self.call(self.world(race, [0], rival_id=4, patched=False))[0])

    def test_empty_human_list_runs_native_code(self):
        u = self.world({0: 90.0, 4: 40.0}, [], rival_id=4, local_id=0)
        lead, loc, riv = self.call(u)
        self.assertEqual((lead, round(loc, 1), round(riv, 1)), (1, 90.0, 40.0))   # native local racer path
        self.assertEqual(struct.unpack('<3I', u.mem_read(STATS, 12))[2], 1)       # NATIVE_FALLBACK

    def test_bot_rival_in_player_vector_does_not_award_free_lead(self):
        race = {0: 20.0, 1: 30.0, 4: 80.0}
        for local in (0, 1):
            self.assertEqual(self.call(self.world(race, [0, 4, 1], rival_id=4,
                                                 local_id=local, bots=(4,))), (0, 30.0, 80.0))

    def test_faster_other_bot_cannot_lead_for_team(self):
        race = {0: 20.0, 1: 30.0, 4: 80.0, 5: 99.0}
        self.assertEqual(self.call(self.world(race, [5, 0, 4, 1], rival_id=4,
                                             bots=(4, 5))), (0, 30.0, 80.0))
        race[1] = 90.0
        self.assertEqual(self.call(self.world(race, [5, 0, 4, 1], rival_id=4,
                                             bots=(4, 5))), (1, 90.0, 80.0))

    def test_only_bots_is_not_human_victory(self):
        self.assertEqual(self.call(self.world({4: 80.0, 5: 99.0}, [4, 5], rival_id=4,
                                             bots=(4, 5)))[0], 0)

    def test_unknown_player_schema_falls_back_with_native_stack(self):
        for kw in (dict(invalid_flag=True), dict(invalid_vtable=True)):
            u = self.world({0: 20.0, 1: 90.0, 4: 80.0}, [0, 1], rival_id=4, **kw)
            self.assertEqual(self.call(u), (0, 20.0, 80.0))  # native local, no team substitution
            self.assertEqual(struct.unpack('<3I', u.mem_read(STATS, 12))[2], 1)

    def test_solo_disconnected_and_other_modes_keep_native_local_comparison(self):
        for kw in (dict(solo=True), dict(connected=2), dict(mode=1), dict(mode=3)):
            u = self.world({0: 20.0, 1: 90.0, 4: 80.0}, [0, 1], rival_id=4, **kw)
            self.assertEqual(self.call(u), (0, 20.0, 80.0))

    def test_filter_offset_matches_native_bot_getter_and_vtable(self):
        self.assertEqual(self.bot_getter, bytes.fromhex('8a8160020000c3'))
        self.assertEqual(self.bot_slot, struct.pack('<I', a.BOT_GETTER))


if __name__ == '__main__':
    unittest.main()
