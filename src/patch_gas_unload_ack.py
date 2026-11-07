"""Opt-in client builder. Verifies native ABI, redirects one CALL, appends RX/RW."""
import struct
from pe_adapter import append_adapter
from pe_image_readonly import PE32
from patch_headless_reset import file_offset, digest
from probe_lifecycle import call_bytes
import gas_unload_ack_adapter as a

CONTRACTS = {
    a.SITE: call_bytes(a.SITE, a.NATIVE),
    a.NATIVE: bytes.fromhex(
        '83ec1053568bf1bb01000000399efc07000074085e32c05b83c410c333d2'
        'c786fc07000002000000889ed9070000399618080000742e538d8604080000'
        '508d4c241c518bcee8161033008b5424148b028b4004508d4e08e814b9ffff'
        '5e8ac35b83c410c3'),
    0xE4CF21: bytes.fromhex(
        'e83a7448018d86040800008d4c24443bc174208b108bc28d7001eb038d4900'
        '8a084084c975f92bc650528d4c244ce8ac7c64ff8b0d7c8f880285c97411'
        '8d54240c52e8986704008bc8e801da08008bcfe82af6ffff8d4c2444e841f363ff'
        '8d4c240ce85838a000'),
    a.CTOR: bytes.fromhex('5668a47a27cb687ed13a628bf1e80e0758ffc7065cee5702c74638d40976028bc65ec3'),
    a.GET_SENDER: bytes.fromhex('8b411cc3'),
}


def verify_native(base):
    image = PE32(base)
    for site, expected in CONTRACTS.items():
        if image.read(site, len(expected)) != expected:
            raise ValueError('Native gas unload contract changed at %X' % site)


def build(base):
    verify_native(base)
    points = {}
    patched, layout, code, _ = append_adapter(
        base, lambda code, stats: a.make_code(code, stats, points), a.CODE_SECTION, a.DATA_SECTION)
    offset = file_offset(patched, a.SITE)
    patched[offset:offset + 5] = call_bytes(a.SITE, layout['adapter'])
    layout.update(points)
    return bytes(patched), code, dict(
        sha256=digest(patched), layout=layout, site=hex(a.SITE), draft=True,
        gameplay_verified=False, server_timeout=False, lan_only=True,
        stats='CALLS+0, UNLOADS+4, SENT+8, SKIPPED_CALLBACK+C, SKIPPED_NETWORK+10',
        limitations='Native unload completion only; pending state cleaned as in E4CE90. '
                    'No game test yet. Needs actual server acknowledgement/removal and preview verification.')


def completion_probe_spec(base):
    """Find the added Unloaded SEND for --completion; never guess live offsets."""
    image = PE32(base)
    sections = [s for s in image.sections if s['name'] == a.CODE_SECTION.decode()]
    if not sections:
        return ()
    if len(sections) != 1:
        raise ValueError('Ambiguous gas unload adapter section')
    section = sections[0]
    start = image.base + section['rva']
    if image.read(a.SITE, 5) != call_bytes(a.SITE, start):
        raise ValueError('Gas unload hook target changed')
    points = {}
    expected = a.make_code(start, start + 0x1000, points)
    if image.read(start, len(expected)) != expected:
        raise ValueError('Gas unload adapter code changed')
    return ((points['send_call'], a.SEND, 'client_send_bundle_unloaded_fix'),)
