"""Builder: append hud_racer_guard_adapter to a client image and redirect the CALL at 90D5D0."""
import struct
from pe_adapter import append_adapter
from pe_image_readonly import PE32
from patch_headless_reset import file_offset, digest
from probe_lifecycle import call_bytes
import hud_racer_guard_adapter as a


def build(base):
    im = PE32(base)
    if im.read(a.SITE, 5) != a.SITE_BYTES or a.SITE_BYTES != call_bytes(a.SITE, a.NATIVE):
        raise ValueError('Leaderboard racer call site changed')
    if im.read(a.NATIVE_TAIL, len(a.TAIL_BYTES)) != a.TAIL_BYTES:
        raise ValueError('Leaderboard native tail changed')
    layout = {}

    def factory(code, stats):
        layout.update(adapter=code, stats=stats)
        return a.make_code(code, stats)

    patched, info, code, _ = append_adapter(base, factory, a.CODE_SECTION, a.DATA_SECTION)
    off = file_offset(patched, a.SITE)
    patched[off:off + 5] = call_bytes(a.SITE, layout['adapter'])
    return bytes(patched), code, dict(sha256=digest(patched), layout={k: hex(v) for k, v in layout.items()},
                                      site=hex(a.SITE), stats='CALLS +0, SKIPPED +4', gameplay_verified=False,
                                      limitations='Skips only the leaderboard build while no local racer exists; '
                                                  'B1496E/DD76D4 are separate and not addressed.')
