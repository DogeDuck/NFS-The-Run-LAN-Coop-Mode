"""Offline-only x86 probe builder. Does NOT open, patch or launch any process.

Future hook point: CALL 013E2A5C -> 013E0130 on the verified server build.
Entry: ECX=TeleportEntity, [ESP+4]=ServerPlayer*, two more original arguments.
Tail-jump keeps return address/arguments unchanged; native callee performs RET 0C.
No inferred transforms or physics writes. Raw transform pointer can be compact.
"""
import struct

TARGET = 0x13E0130
SITE = 0x13E2A5C
SERVER_SHA256 = 'DCFAFC833016BAADE51F556C82963BA8C015406ADC69BEA0006919AD7DD68695'
SLOTS = 32
STRIDE = 32
RING_OFFSET = 64
REQUIRED_STATS_BYTES = RING_OFFSET + SLOTS * STRIDE
FIELDS = ('sequence', 'entity', 'player_id', 'player', 'controllable',
          'raw_transform_pointer', 'caller_return', 'commit')


def make_code(base, stats, target=TARGET, payload=None, caller_offset=36):
    if not (0x10000 <= base < 0x7FFFFFFF and 0x10000 <= stats < 0x7FFFFFFF):
        raise ValueError('Expected low 32-bit code/stats addresses')
    if caller_offset not in (36,40,44,48):raise ValueError('Unsupported caller stack layout')
    b = bytearray.fromhex('9c60')  # pushfd; pushad. Original ESP now +36.
    b += b'\xbf' + struct.pack('<I', stats)  # edi=stats
    # Non-blocking single-writer gate: skip logging rather than stall gameplay.
    b += bytes.fromhex('31c0ba01000000f00fb157040f85')
    busy_fix = len(b)
    b += b'\0' * 4
    b += bytes.fromhex('837f0c000f85')  # Sticky wrap flag: never reuse sequence epoch.
    wrapped_fix = len(b)
    b += b'\0' * 4
    b += bytes.fromhex('b801000000f00fc10740')  # lock xadd [edi],eax; inc eax
    b += bytes.fromhex('0f84')
    zero_fix = len(b)
    b += b'\0' * 4
    b += bytes.fromhex('89c34883e01fc1e0058d7c0740')  # ebx=seq; ring[(seq-1)&31]
    b += bytes.fromhex('c7471c00000000891f')  # invalidate slot commit; write sequence
    if payload is None:
        b += bytes.fromhex('8b4c2418894f04')  # original ECX is saved at ESP+24
        b += bytes.fromhex('8b54242889570c')  # original arg1 is at ESP+40
        b += bytes.fromhex('c74708ffffffffc7471000000000')  # null-player defaults
        b += bytes.fromhex('85d27400')
        fix = len(b) - 1
        b += bytes.fromhex('8b82e40200008947088b821c030000894710')
        b[fix] = len(b) - fix - 1
        b += bytes.fromhex('8b411c894714')  # copy raw property pointer, do not dereference
    else:
        b += payload
    b += bytes.fromhex('8b4424')+bytes([caller_offset])+bytes.fromhex('894718895f1c')  # caller; publish commit last
    b += b'\xbf' + struct.pack('<I', stats)  # EDI was advanced to slot.
    release = len(b)
    b += bytes.fromhex('c7470400000000')  # release writer gate after publishing
    b += b'\xe9'
    restore_fix = len(b)
    b += b'\0' * 4
    wrap = len(b)
    b += bytes.fromhex('c7470c01000000')
    b += b'\xe9' + struct.pack('<i', release - (len(b) + 5))
    dropped = len(b)
    b += bytes.fromhex('f0ff4708')  # count contention drops; don't release another owner
    restore = len(b)
    b += bytes.fromhex('619d')  # popad; popfd: registers/flags restored, SSE untouched
    b += b'\xe9' + struct.pack('<i', target - (base + len(b) + 5))
    for fix, target in ((busy_fix, dropped), (wrapped_fix, release),
                        (zero_fix, wrap), (restore_fix, restore)):
        struct.pack_into('<i', b, fix, target - fix - 4)
    return bytes(b)


def decode_ring(data):
    """Offline decoder; live reader must obtain two matching committed snapshots."""
    if len(data) < REQUIRED_STATS_BYTES:
        raise ValueError('Truncated stats ring')
    events = []
    for slot in range(SLOTS):
        values = struct.unpack_from('<8I', data, RING_OFFSET + slot * STRIDE)
        if values[0] and values[0] == values[-1]:
            events.append(dict(zip(FIELDS, values)))
    return sorted(events, key=lambda event: event['sequence'])


def summarize_events(events, expected_players=(0, 1)):
    counts = {player: 0 for player in expected_players}
    no_controllable = []
    for event in events:
        player = event['player_id']
        if player in counts:
            counts[player] += 1
            if not event['controllable']:
                no_controllable.append(event['sequence'])
    return dict(events_per_player=counts, not_observed=[p for p, count in counts.items() if not count],
                no_controllable_sequences=no_controllable,
                limit='Bounded ring, not proof of absence. Native entry observed, not successful teleport or terrain load. Sequence wraps at 2^32.')
