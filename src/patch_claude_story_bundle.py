"""Persist the four Claude RAM fixes confirmed on 2026-11-09; no game/process access.

Uses the same native generators and initial data as the live helpers. No guest
mute, ANT probe, difficulty experiment or timed external helper is installed.
"""
import hashlib
import struct
from pe_adapter import append_adapter, align
from pe_image_readonly import PE32
import bundle_owner_adapter as owner
import coop_hud_adapter as hud_before
import qte_hud_scope_adapter as hud_after
import host_first_human_adapter as host
import guest_script_vehicle_adapter as vehicle
import host_difficulty_adapter as difficulty_adapter

CLIENT = 'c3fba53c787f6b4edf97b142e2477f3fec4a8bf9ff0c6adacdf7beadd17cc0d6'
SERVER = 'b5d06a6971c95f4a0ba23c1b5840817910865f413477b447a1e13a98d6d8f441'
VEHICLE_STATS = 0x100


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_at(data, address, expected, replacement):
    if len(expected) != len(replacement):
        raise ValueError('Native hook length mismatch')
    offset = PE32(data).offset(address, len(expected))
    if data[offset:offset + len(expected)] != expected:
        raise ValueError(f'Unexpected native bytes at {address:#x}')
    data[offset:offset + len(expected)] = replacement


def section(data, name):
    image = PE32(data)
    matches = [s for s in image.sections if s['name'] == name]
    if len(matches) != 1:
        raise ValueError(f'Missing/ambiguous section {name}')
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    table = pe + 24 + struct.unpack_from('<H', data, pe + 20)[0]
    index = image.sections.index(matches[0])
    return image, matches[0], table + 40 * index


def initialize_stats(data, name, content):
    _, entry, header = section(data, name)
    if len(content) > entry['size']:
        raise ValueError('Adapter data exceeds reserved section')
    data[entry['raw']:entry['raw'] + len(content)] = content
    struct.pack_into('<I', data, header + 8, len(content))


def build_client(base, catalog):
    if sha(base) != CLIENT:
        raise ValueError('Exact v0.7.3 client required')
    data = bytearray(base)
    image, code_section, header = section(data, '.coophud')
    _, stat_section, _ = section(data, '.hudstat')
    address = image.base + code_section['rva']
    stats = image.base + stat_section['rva']
    before = hud_before.make_code(address, stats)
    after = hud_after.make_code(address, stats)
    if max(len(before), len(after)) > code_section['size']:
        raise ValueError('HUD replacement exceeds existing section')
    raw = code_section['raw']
    if data[raw:raw + len(before)] != before or set(data[raw + len(before):raw + code_section['size']]) - {0, 0xcc}:
        raise ValueError('Existing HUD generator does not match baseline')
    data[raw:raw + code_section['size']] = after + b'\xcc' * (code_section['size'] - len(after))
    struct.pack_into('<I', data, header + 8, len(after))
    owners = [r['owner_guid'] for r in catalog['owners']][::-1]
    factory = lambda code, counters: owner.make_code(code, counters, catalog['asset_guid'], owners, ordered=True)
    data, layout, _, _ = append_adapter(data, factory, b'.ownbnd', b'.ownbst')
    initialize_stats(data, '.ownbst', bytes(owner.STATS_SIZE))
    call = lambda target: b'\xe8' + struct.pack('<i', target - owner.SITE - 5)
    write_at(data, owner.SITE, call(owner.TARGET), call(layout['adapter']))
    return bytes(data), dict(qte_hud=dict(code=address, stats=stats, bytes=len(after)),
                             bundle_owner=dict(**layout, prefer_latest=True,
                                               asset_guid=catalog['asset_guid'], owners=owners))


def build_server(base, with_difficulty=False):
    if sha(base) != SERVER:
        raise ValueError('Exact v0.7.3 Marcus-fixed server required')
    entries = {}

    def factory(code, stats):
        first = host.make_code(code, stats)
        offset = align(len(first), 16)
        rest, entry_a, entry_c = vehicle.make_code(code + offset, stats + VEHICLE_STATS)
        entries.update(host=code, vehicle_enter=entry_a, vehicle_done=entry_c,
                       host_stats=stats, vehicle_stats=stats + VEHICLE_STATS)
        code_blob = first + b'\xcc' * (offset - len(first)) + rest
        if with_difficulty:
            difficulty_offset = align(len(code_blob), 16)
            extra, difficulty_entries = difficulty_adapter.make_code(code + difficulty_offset, stats + 0x180)
            entries['difficulty'] = difficulty_entries
            entries['difficulty_stats'] = stats + 0x180
            code_blob = code_blob.ljust(difficulty_offset, b'\xcc') + extra
        return code_blob

    data, layout, _, _ = append_adapter(base, factory, b'.storycp', b'.storyst')
    content = host.stats_init().ljust(VEHICLE_STATS, b'\0') + vehicle.stats_init()
    if with_difficulty:
        content = content.ljust(0x180, b'\0') + difficulty_adapter.stats_init()
    initialize_stats(data, '.storyst', content)
    write_at(data, host.SITE, host.SITE_BYTES,
             b'\xe9' + struct.pack('<i', entries['host'] - host.SITE - 5) + b'\x90')
    call = lambda target: b'\xe8' + struct.pack('<i', target - vehicle.ENTER_SITE - 5)
    write_at(data, vehicle.ENTER_SITE, call(vehicle.ENTER), call(entries['vehicle_enter']))
    write_at(data, vehicle.SLOT, struct.pack('<I', vehicle.DONE), struct.pack('<I', entries['vehicle_done']))
    if with_difficulty:
        for name, site, before, _, _, _ in difficulty_adapter.SITES:
            write_at(data, site, before, difficulty_adapter.jmp_patch(site, len(before), entries['difficulty'][name]))
    return bytes(data), dict(**layout, entries=entries, host_env='THERUN_HOST_NAME',
                             guest_vehicle_scope='10.5 only, v2 story player enters last car',
                             players='enumerate real humans, no fixed player0/1 assumption')
