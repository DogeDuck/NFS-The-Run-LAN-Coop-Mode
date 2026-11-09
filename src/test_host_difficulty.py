"""Unicorn tests for host_difficulty_adapter against the REAL server bytes at both store sites."""
import struct
import unittest
from pathlib import Path
from test_pause_ai_adapter import Uc, UC_ARCH_X86, UC_MODE_32
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *  # noqa: F403
import host_difficulty_adapter as a
from pe_image_readonly import PE32

ROOT = Path(__file__).resolve().parent
SERVER = ROOT / 'backups/NFSTR_Server.exe.headless-original'
INSTALLED = Path(r'X:\EA Games\Need for Speed The Run\Need for Speed The Run\NFSTR_Server.exe')
CODE, STATS, D, STACK, IAT, GETENV = 0x30000000, 0x30001000, 0x32000000, 0x33000000, 0x2A8B000, 0x35000000


@unittest.skipUnless(SERVER.is_file(), 'server backup missing')
class DifficultyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pe = PE32(SERVER.read_bytes())
        cls.native = {name: pe.read(site, (resume - site) + 8) for name, site, _, resume, _, _ in a.SITES}

    def machine(self, env, patched=True):
        u = Uc(UC_ARCH_X86, UC_MODE_32)
        for base in (0x1200000, 0x1300000, 0x1400000, 0x2A00000, CODE, D, STACK, GETENV):
            u.mem_map(base, 0x100000)
        u.reg_write(UC_X86_REG_CR4, u.reg_read(UC_X86_REG_CR4) | 0x600)
        code, self.entries = a.make_code(CODE, STATS)
        u.mem_write(CODE, code); u.mem_write(STATS, a.stats_init())
        for name, site, original, resume, _, _ in a.SITES:
            u.mem_write(site, self.native[name])
            if patched:
                u.mem_write(site, a.jmp_patch(site, len(original), self.entries[name]))
        u.mem_write(a.GETENV_IAT, struct.pack('<I', GETENV))
        self.env, self.env_calls, self.u = env, 0, u
        u.hook_add(UC_HOOK_CODE, self.hook)
        return u

    def hook(self, uc, addr, size, data):
        if addr == GETENV:
            self.env_calls += 1
            esp = uc.reg_read(UC_X86_REG_ESP)
            ret, name, buf, n = struct.unpack('<4I', uc.mem_read(esp, 16))
            assert bytes(uc.mem_read(name, len(a.ENV))) == a.ENV
            value = self.env
            if value is None:
                length = 0
            elif len(value) + 1 > n:
                length = len(value) + 1
            else:
                uc.mem_write(buf, value + b'\0'); length = len(value)
            uc.reg_write(UC_X86_REG_EAX, length); uc.reg_write(UC_X86_REG_ECX, 0xEC); uc.reg_write(UC_X86_REG_EDX, 0xED)
            uc.reg_write(UC_X86_REG_XMM0, 0xDEAD)
            uc.reg_write(UC_X86_REG_ESP, esp + 16); uc.reg_write(UC_X86_REG_EIP, ret)

    def run_site(self, index, message_value):
        name, site, original, resume, _, _ = a.SITES[index]
        u, msg, obj = self.u, D + 0x100, D + 0x1000
        u.mem_write(msg + 0x38, struct.pack('<I', message_value))
        u.mem_write(obj + 0x24, struct.pack('<I', 0x77)); u.mem_write(obj + 0x5A8, struct.pack('<I', 0x77))
        regs = {UC_X86_REG_ESP: STACK + 0x8000, UC_X86_REG_EBX: 0xB0B, UC_X86_REG_EBP: 0xBB}
        if index == 0:
            regs.update({UC_X86_REG_EDI: msg, UC_X86_REG_ESI: obj, UC_X86_REG_ECX: 0xC1, UC_X86_REG_EDX: 0xD1})
        else:
            regs.update({UC_X86_REG_EDX: msg, UC_X86_REG_ECX: obj, UC_X86_REG_ESI: 0x51, UC_X86_REG_EDI: 0xD1})
        for k, v in regs.items(): u.reg_write(k, v)
        u.reg_write(UC_X86_REG_XMM0, 0x5555)
        u.emu_start(site, resume, count=4000)
        for k, v in regs.items():
            self.assertEqual(u.reg_read(k), v)
        self.assertEqual(u.reg_read(UC_X86_REG_XMM0), 0x5555)
        stored = struct.unpack('<I', u.mem_read(obj + (0x24 if index == 0 else 0x5A8), 4))[0]
        self.assertEqual(u.reg_read(UC_X86_REG_EAX), stored)
        return stored

    def stat(self, off): return struct.unpack('<I', self.u.mem_read(STATS + off, 4))[0]

    def test_host_value_wins_at_both_sites(self):
        for env, expected in ((b'0', 0), (b'2', 2), (b'3', 3)):
            with self.subTest(env=env):
                self.machine(env)
                self.assertEqual(self.run_site(0, 1), expected)
                self.assertEqual(self.run_site(1, 3), expected)
                self.assertEqual(self.run_site(0, 0), expected)
                self.assertEqual((self.stat(a.FORCED), self.stat(a.LAST_NATIVE), self.env_calls), (3, 0, 1))

    def test_unset_or_invalid_is_exactly_native(self):
        for env in (None, b'', b'4', b'x', b'12', b'/', b'2' * 40):
            with self.subTest(env=env):
                self.machine(env)
                self.assertEqual(self.run_site(0, 1), 1)
                self.assertEqual(self.run_site(1, 2), 2)
                self.assertEqual((self.stat(a.FORCED), self.stat(a.STATE), self.env_calls), (0, a.NATIVE, 1))

    def test_unpatched_reference_matches(self):
        self.machine(None, patched=False)
        self.assertEqual(self.run_site(0, 2), 2); self.assertEqual(self.run_site(1, 1), 1)

    def test_sites_in_original_and_installed_server(self):
        for path in (SERVER, INSTALLED):
            if path.is_file():
                pe = PE32(path.read_bytes())
                for name, site, original, *_ in a.SITES:
                    self.assertEqual(pe.read(site, len(original)), original)


if __name__ == '__main__':
    unittest.main()
