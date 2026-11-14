"""Builder (Claude 14.11.2026): make the leased cutscene AI permanent in a client image. Never installs anything.

Appends the combined adapter (cutscene_ai_adapter frame + stop wrapper, Codex' ANT camera wrapper from
ant_scene_scope, optional vehicle ghost) as two new sections and wires exactly the three sites the RAM tests use:
  CALL E1D700 at E6072E -> frame entry; ClientAnimationSequence Stop slot 2488AA0 -> stop wrapper;
  ClientAntCameraEntity event slot 2488B54 -> camera wrapper (calls native 990920 first).
Data section is pre-initialised (config AI | controller restore | ghost, quiet limit 15 frames), so the shipped
behaviour equals `ant_cutscene_live.py --ghost`. Only on a connected LAN client; solo/menus untouched.
Gameplay status: hooks ran stable as RAM patch (~50k frames), but no scene was detected in the helicopter
finale, so AI/ghost effect is NOT verified in game.
"""
import struct
import cutscene_ai_adapter as a
import ant_scene_scope as ant
from patch_headless_reset import file_offset, digest
from probe_lifecycle import call_bytes

CODE_NAME, DATA_NAME = b'.cutai', b'.cutaid'
CONFIG = a.CFG_AI | a.CFG_RESTORE | a.CFG_GHOST
CAMERA_SLOT = ant.VT + 0x0C


def align(v, b): return (v + b - 1) // b * b


def append_sections(base, code_factory, data_bytes, code_name, data_name):
    """Like pe_adapter.append_adapter, but code up to 0x4000 and an initialised RW section of any size."""
    data = bytearray(base)
    pe = struct.unpack_from('<I', data, 0x3C)[0]; opt = pe + 24
    count = struct.unpack_from('<H', data, pe + 6)[0]; opt_size = struct.unpack_from('<H', data, pe + 20)[0]
    if data[:2] != b'MZ' or data[pe:pe + 4] != b'PE\0\0' or struct.unpack_from('<H', data, opt)[0] != 0x10B:
        raise ValueError('Expected PE32 image')
    image_base = struct.unpack_from('<I', data, opt + 28)[0]
    section_align, file_align = struct.unpack_from('<II', data, opt + 32)
    if image_base != 0x400000 or section_align != 0x1000 or file_align not in (0x200, 0x1000):
        raise ValueError('Unsupported PE layout')
    table = opt + opt_size; sections = []
    for i in range(count):
        name = bytes(data[table + i * 40:table + i * 40 + 8]).rstrip(b'\0')
        if name in (code_name, data_name): raise ValueError('Cutscene AI sections already present')
        vs, rva, size, raw = struct.unpack_from('<4I', data, table + i * 40 + 8)
        sections.append((rva, vs, size, raw))
    headers = table + count * 40
    first_raw = min(raw for rva, vs, size, raw in sections if size)
    if headers + 80 > first_raw or any(data[headers:headers + 80]): raise ValueError('No free section-header space')
    code_rva = align(max(rva + max(vs, size) for rva, vs, size, raw in sections), section_align)
    code = code_factory(image_base + code_rva, None)          # first pass for size
    code_span = align(len(code), section_align)
    data_rva = code_rva + code_span
    code = code_factory(image_base + code_rva, image_base + data_rva)
    if align(len(code), section_align) != code_span: raise ValueError('Code size changed between passes')
    code_size = align(len(code), file_align); data_size = align(len(data_bytes), file_align)
    raw_code = align(len(data), file_align); raw_data = raw_code + code_size
    data.extend(b'\0' * (raw_code - len(data)))
    data.extend(code + b'\xcc' * (code_size - len(code)))
    data.extend(data_bytes + b'\0' * (data_size - len(data_bytes)))
    for index, (name, vs, rva, size, raw, flags) in enumerate((
            (code_name, len(code), code_rva, code_size, raw_code, 0x60000020),
            (data_name, len(data_bytes), data_rva, data_size, raw_data, 0xC0000040))):
        struct.pack_into('<8sIIIIIIHHI', data, headers + 40 * index, name.ljust(8, b'\0'), vs, rva, size, raw, 0, 0, 0, 0, flags)
    struct.pack_into('<H', data, pe + 6, count + 2)
    struct.pack_into('<I', data, opt + 4, struct.unpack_from('<I', data, opt + 4)[0] + code_size)
    struct.pack_into('<I', data, opt + 8, struct.unpack_from('<I', data, opt + 8)[0] + data_size)
    struct.pack_into('<I', data, opt + 56, data_rva + align(len(data_bytes), section_align))
    struct.pack_into('<I', data, opt + 64, 0)
    return data, image_base + code_rva, image_base + data_rva


def build(base, config=CONFIG, quiet_limit=15):
    """Returns (patched bytes, report). Refuses unless all three sites carry their exact original bytes."""
    expected = ((a.FRAME_SITE, a.FRAME_SITE_BYTES), (a.STOP_SLOT, struct.pack('<I', a.STOP_NATIVE)),
                (CAMERA_SLOT, struct.pack('<I', ant.NATIVE)))
    for site, original in expected:
        off = file_offset(base, site)
        if base[off:off + len(original)] != original: raise ValueError('Site changed: ' + hex(site))
    entries = {}

    def factory(code_va, data_va):
        code, ent, _ = ant.make_combined(code_va, data_va if data_va else code_va + 0x10000, ghost=True)
        entries.update(ent)
        return code
    raw = bytearray(a.data_init(config, quiet_limit) + ant.initial())
    patched, code_va, data_va = append_sections(base, factory, bytes(raw), CODE_NAME, DATA_NAME)
    for site, new in ((a.FRAME_SITE, call_bytes(a.FRAME_SITE, entries['frame'])),
                      (a.STOP_SLOT, struct.pack('<I', entries['stop'])),
                      (CAMERA_SLOT, struct.pack('<I', entries['camera']))):
        off = file_offset(patched, site)
        patched[off:off + len(new)] = new
    report = dict(sha256=digest(patched), code=hex(code_va), data=hex(data_va),
                  entries={k: hex(v) for k, v in entries.items()}, config=config, quiet_limit=quiet_limit,
                  sites=[hex(s) for s, _ in expected], lan_only=True, ghost=bool(config & a.CFG_GHOST),
                  gameplay_verified=False,
                  lost_ant_stop_failsafe_ms=ant.LOST_STOP_MS,frame_rate_independent_failsafe=True,
                  pawn_and_sequence_retry_cache_reset=True,
                  limitations='AI/controller restore/ghost only act when a ClientAnimationSequence runs or the ANT '
                              'camera reports active (DEAA09DC). In the helicopter finale neither fired in the older pre-R2 live test (13./14.11.); '
                              'effect in game unverified. Camera sync of guest scenes is not addressed.')
    return bytes(patched), report
