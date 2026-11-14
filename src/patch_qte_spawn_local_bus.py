"""Offline-only opt-in patch for the exact RACESTART client; never installs."""
import hashlib
import struct
from pe_adapter import append_adapter
from pe_image_readonly import PE32
import qte_spawn_local_bus as a

SUPPORTED = 'df9f70693dd4167440935725174014d1643c284b05d010fe198681d4b322ace5'


def build(base):
    if hashlib.sha256(base).hexdigest() != SUPPORTED:
        raise ValueError('Expected exact DF9F7069 RACESTART client; no stacked candidates')
    p = PE32(base)
    pins = {
        a.SLOT: struct.pack('<I', a.NATIVE),
        a.NATIVE: bytes.fromhex('8b416cc3'),
        a.BASIC_VT + 0x190: struct.pack('<I', 0x8CAFF0),
        0xF26530: bytes.fromhex('8b81bc000000c3'),
    }
    for address, expected in pins.items():
        if p.read(address, len(expected)) != expected:
            raise ValueError('Native schema differs at ' + hex(address))
    data, layout, code, _ = append_adapter(base, a.make_code, b'.qtelbus', b'.qtelbst')
    off = PE32(data).offset(a.SLOT, 4)
    struct.pack_into('<I', data, off, layout['adapter'])
    return bytes(data), dict(**layout, slot=hex(a.SLOT), native=hex(a.NATIVE),
        sha256=hashlib.sha256(data).hexdigest(), bytes=len(code),
        experimental=True, default_enabled=False, installed=False,
        gameplay_verified=False, scope='LAN Story OOC local BasicControllable spawn bus',
        max_pawns=a.MAX_PAWNS, frame_hook=False, adds_network_messages=False,
        replays_ant_start=False, host_only_input=False, qte_sync_verified=False)
