"""Opt-in empty leaderboard lifecycle fix; build only, never install or launch."""
import empty_standings_adapter as a
from pe_adapter import append_adapter
from pe_image_readonly import PE32
from patch_headless_reset import file_offset, digest
from probe_lifecycle import call_bytes


def build(base):
    im = PE32(base)
    if im.read(a.SITE, 5) != a.SITE_BYTES or a.SITE_BYTES != call_bytes(a.SITE, a.NATIVE):
        raise ValueError('HUD leaderboard entry contract changed')
    # 866A60 depends on client manager/F26530 and the native ID/racer lookup.
    for address, signature in ((a.LOCAL_RACER, '568bf18b0d788f8802e8c2fa6b00'),
                               (0xF26530, '8b81bc000000c3')):
        expected = bytes.fromhex(signature)
        if im.read(address, len(expected)) != expected:
            raise ValueError('HUD local racer getter contract changed')
    patched, layout, code, _ = append_adapter(base, a.make_code, a.CODE_SECTION, a.DATA_SECTION)
    off = file_offset(patched, a.SITE)
    patched[off:off+5] = call_bytes(a.SITE, layout['adapter'])
    return bytes(patched), code, dict(sha256=digest(patched), layout=layout,
        gameplay_verified=False, race_data_modified=False,
        stats='CALLS+0, HIDDEN_EMPTY+4, SHOWN_WITH_RACER+8',
        limitations='Only no-local-racer HUD rebuilds; cutscenes retaining racers require further evidence.')
