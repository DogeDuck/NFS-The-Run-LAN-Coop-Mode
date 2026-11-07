"""Offline static helper for the original server/client images (read-only).

  python static_xref.py dis 0x1304200 [--count 80]     disassemble from address
  python static_xref.py callers 0x1304200              direct CALL/JMP rel32 sites
  python static_xref.py field 0xE18 [--near 0x1300000-0x1310000]  [reg+disp] accesses
  python static_xref.py func 0x1304284                 guess function start (int3/ret padding)

Default image: backups/NFSTR_Server.exe.headless-original (--image to change).
Capstone is loaded from the research analysis-libs folder. Never touches a running process.
"""
import argparse
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'outputs/test-libs'))
# Capstone lives in the older Codex research folder (same as coop_diagnostics.RESEARCH).
sys.path.insert(0, r'C:\Users\hatty\Documents\Codex\2026-10-28\es-x20\work\the-run\analysis-libs')
from capstone import Cs, CS_ARCH_X86, CS_MODE_32  # noqa: E402
from pe_image_readonly import PE32  # noqa: E402

DEFAULT = ROOT / 'backups/NFSTR_Server.exe.headless-original'


class Image:
    def __init__(self, path=DEFAULT):
        self.pe = PE32(Path(path).read_bytes())
        self.cs = Cs(CS_ARCH_X86, CS_MODE_32)
        self.text = [s for s in self.pe.sections if s['flags'] & 0x20000000]

    def dis(self, address, count=60, stop_at_ret=True):
        out = []
        code = self.pe.read(address, min(count * 15, 0x4000))
        for ins in self.cs.disasm(code, address):
            out.append(ins)
            if len(out) >= count or (stop_at_ret and ins.mnemonic == 'ret'):
                break
        return out

    def ranges(self):
        for s in self.text:
            yield self.pe.base + s['rva'], self.pe.data[s['raw']:s['raw'] + s['size']]

    def callers(self, target):
        hits = []
        for start, data in self.ranges():
            for i in range(len(data) - 5):
                op = data[i]
                if op in (0xE8, 0xE9):
                    site = start + i
                    if site + 5 + struct.unpack_from('<i', data, i + 1)[0] == target:
                        hits.append((site, 'call' if op == 0xE8 else 'jmp'))
        return hits

    def func_start(self, address):
        """Walk back to the CC/C3-padded boundary. Heuristic, verify by disassembly."""
        for a in range(address, address - 0x4000, -1):
            prev = self.pe.read(a - 1, 1)[0]
            if prev == 0xCC and a % 16 == 0:
                return a
        return None

    def field(self, disp, lo, hi):
        """Find disp32 operands by byte pattern, confirm each by decoding one instruction."""
        rows, needle, seen = [], struct.pack('<I', disp), set()
        for start, data in self.ranges():
            i = data.find(needle)
            while i >= 0:
                site = start + i
                if lo <= site < hi:
                    for back in range(2, 8):
                        try:
                            ins = next(self.cs.disasm(self.pe.read(site - back, 16), site - back), None)
                        except ValueError:
                            ins = None
                        if (ins and ins.address + ins.size > site and ('0x%x]' % disp) in ins.op_str
                                and ins.address not in seen):
                            seen.add(ins.address)
                            rows.append(ins)
                            break
                i = data.find(needle, i + 1)
        return sorted(rows, key=lambda r: r.address)


def fmt(ins):
    return '%08x  %-8s %s' % (ins.address, ins.mnemonic, ins.op_str)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('mode', choices=['dis', 'callers', 'field', 'func'])
    p.add_argument('value', type=lambda v: int(v, 0))
    p.add_argument('--count', type=int, default=60)
    p.add_argument('--near', default='0x1200000-0x1400000')
    p.add_argument('--image', type=Path, default=DEFAULT)
    a = p.parse_args()
    img = Image(a.image)
    if a.mode == 'dis':
        for ins in img.dis(a.value, a.count):
            print(fmt(ins))
    elif a.mode == 'callers':
        for site, kind in img.callers(a.value):
            print('%08x %s  (func ~%s)' % (site, kind, hex(img.func_start(site) or 0)))
    elif a.mode == 'func':
        print(hex(img.func_start(a.value) or 0))
    else:
        lo, hi = (int(x, 0) for x in a.near.split('-'))
        for ins in img.field(a.value, lo, hi):
            print(fmt(ins))


if __name__ == '__main__':
    main()
