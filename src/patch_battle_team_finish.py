"""DRAFT builder: append battle_team_finish_adapter to a v0.6-family server image.

Not used by build_test_package. Verifies both native CALL sites, appends pick+wrapper
code in one RX section (shared RW state section), redirects the two CALLs.
"""
import struct
from pe_adapter import append_adapter
from patch_headless_reset import file_offset, digest
from probe_lifecycle import call_bytes
import battle_team_finish_adapter as a

SITES = ((a.PICK_SITE, a.PICK_NATIVE), (a.WRAP_SITE, a.WRAP_NATIVE))


def build(base):
    for site, native in SITES:
        offset = file_offset(base, site)
        if base[offset:offset + 5] != call_bytes(site, native):
            raise ValueError('Native battle call site changed: %x' % site)
    layout = {}

    def factory(code, stats):
        pick = a.pick_code(code, stats)
        wrapper_base = code + ((len(pick) + 15) & ~15)
        layout.update(pick=code, wrapper=wrapper_base, stats=stats)
        return pick + b'\xcc' * (wrapper_base - code - len(pick)) + a.wrapper_code(wrapper_base, stats)

    patched, info, code, _ = append_adapter(base, factory, b'.btlfin', b'.btlstat')
    for (site, _), target in zip(SITES, (layout['pick'], layout['wrapper'])):
        offset = file_offset(patched, site)
        patched[offset:offset + 5] = call_bytes(site, target)
    return bytes(patched), code, dict(sha256=digest(patched), layout=layout, sites=[hex(s) for s, _ in SITES],
                                      gameplay_verified=False, draft=True,
                                      limitations='Team finish for every human in BattleRace; bot part runs once per human; not tested in game.')
