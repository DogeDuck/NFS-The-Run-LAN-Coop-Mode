"""Extend the story start-spawn race allowlist of an existing v0.7.3 server in place.

Only the two spawn adapters (.spngrid selector, .spnpose matrix) are regenerated at
their existing addresses with the existing stats/counter layout and slot reservation.
Proof of identity: the generator must first reproduce the installed adapter bytes
exactly from the current catalogue. Everything outside those two code ranges and
their section VirtualSize fields stays byte-identical (battle/phase code untouched).

Reason (MISSIONS-FEHLERREGISTER 10.31): Chicago Downtown Mini (challenge 10_31,
GUID 3e2c57e0) shares the racedata name sm_10_3 with 10.3 Chicago Interstate and
was therefore missing. Without the selector both humans fill grid slots from 0;
slot 0 is StartGrid Spawner1 = authored rival Marcus (AIPerformanceDistanceMode),
slot 1 = Spawner2 = player (PlayerGridPosition 2). A human in Spawner1 becomes Marcus.
"""
import hashlib
import json
import struct
import uuid
from pathlib import Path
import story_start_spawn_adapter as a

ROOT = Path(__file__).resolve().parent
CATALOGUE = ROOT / 'config/story-spawn-stage2-events.json'
V073_SERVER = 'c9ab0d36ff35d9cf2548bdc73a94d911cc2065a921fa4a4afac86ad2e593a988'
SELECT, STATS, MATRIX = 0x2B86000, 0x2B87000, 0x2B88000
ADDED = ({'event': '10_31', 'guid': '3e2c57e0-ed14-47e3-b63a-805c8b53ec28'},)


def sections(image):
    pe = struct.unpack_from('<I', image, 0x3C)[0]
    count = struct.unpack_from('<H', image, pe + 6)[0]
    table = pe + 24 + struct.unpack_from('<H', image, pe + 20)[0]
    base = struct.unpack_from('<I', image, pe + 52)[0]
    out = {}
    for i in range(count):
        header = table + 40 * i
        name, vsize, va, rsize, roff = struct.unpack_from('<8sIIII', image, header)
        out[name.rstrip(b'\0')] = dict(header=header, vsize=vsize, va=base + va, rsize=rsize, roff=roff)
    return out


def code(rows):
    guids = tuple(uuid.UUID(r['guid']) for r in rows)
    return (a.selector_code(SELECT, STATS, guids, True), a.matrix_code(MATRIX, STATS, guids))


def build(image, rows_old, rows_new):
    if hashlib.sha256(image).hexdigest() != V073_SERVER:
        raise ValueError('Installed v0.7.3 server required')
    sec = sections(image)
    old, new = code(rows_old), code(rows_new)
    patched = bytearray(image)
    for name, va, before, after in ((b'.spngrid', SELECT, old[0], new[0]), (b'.spnpose', MATRIX, old[1], new[1])):
        s = sec[name]
        if s['va'] != va or s['vsize'] != len(before):
            raise ValueError(f'{name} layout changed')
        if image[s['roff']:s['roff'] + len(before)] != before:
            raise ValueError(f'{name} is not reproduced by the generator; refuse')
        if len(after) > s['rsize'] or len(after) > 0x1000:
            raise ValueError(f'{name} too small for extended list')
        if set(image[s['roff'] + len(before):s['roff'] + s['rsize']]) != {0xCC}:
            raise ValueError(f'{name} slack is not INT3 padding')
        patched[s['roff']:s['roff'] + len(after)] = after
        struct.pack_into('<I', patched, s['header'] + 8, len(after))
    return bytes(patched)


def catalogues():
    """(v0.7.3 list, extended list). The config already contains ADDED for future builds."""
    rows = json.loads(CATALOGUE.read_text())['events']
    added = {r['guid'] for r in ADDED}
    if not added <= {r['guid'] for r in rows}:
        raise ValueError('Catalogue must contain the added race')
    return [r for r in rows if r['guid'] not in added], rows


def main():
    game = Path(r'X:\EA Games\Need for Speed The Run\Need for Speed The Run')
    image = (game / 'NFSTR_Server.exe').read_bytes()
    patched = build(image, *catalogues())
    out = ROOT / 'outputs/server-spawn-allowlist-10_31.exe'
    if out.exists():
        raise ValueError('Output exists; never overwrite')
    out.write_bytes(patched)
    print(json.dumps(dict(output=str(out), sha256=hashlib.sha256(patched).hexdigest(), added=ADDED)))


if __name__ == '__main__':
    main()
