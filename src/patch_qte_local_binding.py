"""Offline opt-in QTE candidate builder; never installs or starts the game."""
import hashlib
import struct
from pe_adapter import append_adapter
from pe_image_readonly import PE32
import qte_local_event_adapter as a

SUPPORTED = {
    'c3fba53c787f6b4edf97b142e2477f3fec4a8bf9ff0c6adacdf7beadd17cc0d6',
    'df9f70693dd4167440935725174014d1643c284b05d010fe198681d4b322ace5',
}


def build(base):
    digest = hashlib.sha256(base).hexdigest()
    if digest not in SUPPORTED:
        raise ValueError('Expected exact supported co-op client')
    image = PE32(base)
    expected = a.call_patch(a.NATIVE)
    if image.read(a.SITE, 5) != expected:
        raise ValueError('Player-event constructor call differs')
    if image.read(0xF26530, 7) != bytes.fromhex('8b81bc000000c3'):
        raise ValueError('Local-player getter differs')
    if image.read(0xF42020, 7) != bytes.fromhex('8a8160020000c3'):
        raise ValueError('Human/bot getter differs')
    if struct.unpack('<I', image.read(a.PLAYER_VT + 0x18, 4))[0] != 0xF42020:
        raise ValueError('Player schema differs')
    data, layout, code, _ = append_adapter(base, a.make_code, b'.qteloc', b'.qtelost')
    offset = PE32(data).offset(a.SITE, 5)
    data[offset:offset + 5] = a.call_patch(layout['adapter'])
    return bytes(data), dict(**layout, site=hex(a.SITE), bytes=len(code),
        experimental=True, default_enabled=False, gameplay_verified=False,
        scope='received human player-event context, LAN Story OOC only',
        host_only_input=False, alters_eventsync=False, fabricates_success=False)
