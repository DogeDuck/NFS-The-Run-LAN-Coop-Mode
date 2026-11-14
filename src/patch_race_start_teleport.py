"""Append race_start_teleport_adapter to the exact public 0.7.7 server (B4DFA348). Never installs anything."""
import struct
from pe_adapter import append_adapter
from patch_headless_reset import file_offset, digest
from probe_lifecycle import call_bytes
from offline_test_images import INTEGRATED_HASHES
import race_start_teleport_adapter as adapter


def build(base, expected=INTEGRATED_HASHES['server']):
    if digest(base).lower() != expected:
        raise ValueError('Exact 0.7.7 server required')
    offset = file_offset(base, adapter.SITE)
    if base[offset:offset + 5] != call_bytes(adapter.SITE, adapter.TARGET):
        raise ValueError('Race-start teleport CALL differs')
    patched, info, code, _ = append_adapter(base, adapter.make_code, b'.rstele', b'.rstdat')
    pe = struct.unpack_from('<I', patched, 0x3C)[0]
    count = struct.unpack_from('<H', patched, pe + 6)[0]
    table = pe + 24 + struct.unpack_from('<H', patched, pe + 20)[0]
    struct.pack_into('<I', patched, table + (count - 1) * 40 + 8, adapter.STATS_SIZE)  # RW VirtualSize
    stats = file_offset(patched, info['counter'])
    patched[stats:stats + adapter.STATS_SIZE] = adapter.stats_init()
    site = file_offset(patched, adapter.SITE)
    patched[site:site + 5] = call_bytes(adapter.SITE, info['adapter'])
    return bytes(patched), dict(info, sha256=digest(patched), site=hex(adapter.SITE), installed=False)
