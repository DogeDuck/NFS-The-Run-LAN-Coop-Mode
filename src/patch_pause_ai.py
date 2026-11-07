"""DRAFT builder: append pause_ai_adapter to a v0.6-family client image (opt-in only)."""
from pe_adapter import append_adapter
from patch_headless_reset import file_offset, digest
from probe_lifecycle import call_bytes
import pause_ai_adapter as a


def build(base, guard_ai_state=True, hud_state=False):
    site, native = (a.HUD_SITE, a.HUD_NATIVE) if hud_state else (a.SITE, a.NATIVE)
    offset = file_offset(base, site)
    if base[offset:offset + 5] != call_bytes(site, native):
        raise ValueError('Native pause call site changed')
    if hud_state:
        from pe_image_readonly import PE32
        image = PE32(base)
        for addr, expected in ((0x900EB5,'68ebed4473'),(0x900ECE,'c7466402000000'),(0x900F0B,'c7466401000000')):
            if image.read(addr,len(bytes.fromhex(expected))) != bytes.fromhex(expected):
                raise ValueError('HUD pause state contract changed at ' + hex(addr))
    patched, layout, code, _ = append_adapter(base, lambda code, stats: a.make_code(code, stats, guard_ai_state, hud_state), b'.pauseai', b'.pausest')
    offset = file_offset(patched, site)
    patched[offset:offset + 5] = call_bytes(site, layout['adapter'])
    return bytes(patched), code, dict(sha256=digest(patched), layout=layout, site=hex(site), draft=True, guard_ai_state=guard_ai_state,
                                      source='hud_pause_visibility' if hud_state else 'client_pause_message',
                                      gameplay_verified=False,
                                      limitations='LAN only. Native AI switch F29820(entity,1/0,0,0) using '
                                                  +('HUD PauseVisibilty state transitions' if hud_state else 'ClientPauseGameMessage(paused)')
                                                  +'; switched back on resume. Not tested in game.')
