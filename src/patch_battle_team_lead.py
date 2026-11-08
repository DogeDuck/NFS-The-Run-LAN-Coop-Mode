"""Builder: append battle_team_lead_adapter to a client image and JMP over the first 10 bytes of 98C640."""
import struct
from pe_adapter import append_adapter
from pe_image_readonly import PE32
from patch_headless_reset import file_offset, digest
import battle_team_lead_adapter as a


def build(base):
    image = PE32(base)
    if image.read(a.SITE, len(a.SITE_BYTES)) != a.SITE_BYTES:
        raise ValueError('Battle lead function 98C640 changed')
    if (image.read(a.BOT_GETTER, 7) != bytes.fromhex('8a8160020000c3') or
            image.read(a.PLAYER_VTABLE + 0x18, 4) != struct.pack('<I', a.BOT_GETTER)):
        raise ValueError('ClientPlayer bot identity contract changed')
    layout = {}

    def factory(code, stats):
        layout.update(adapter=code, stats=stats)
        return a.make_code(code, stats)

    patched, info, code, _ = append_adapter(base, factory, a.CODE_SECTION, a.DATA_SECTION)
    off = file_offset(patched, a.SITE)
    patched[off:off + 10] = b'\xe9' + struct.pack('<i', layout['adapter'] - a.SITE - 5) + b'\x90' * 5
    return bytes(patched), code, dict(sha256=digest(patched), layout={k: hex(v) for k, v in layout.items()},
                                      site=hex(a.SITE), stats='CALLS +0, TEAM +4, NATIVE_FALLBACK +8',
                                      gameplay_verified=False,
                                      human_filter='ClientPlayer vtable + native bot byte +260 == 0; invalid schema uses native',
                                      limitations='Lead/HOLD THE LEAD uses the best human progress; '
                                                  'server-side finish for all humans needs --battle-team-finish.')
