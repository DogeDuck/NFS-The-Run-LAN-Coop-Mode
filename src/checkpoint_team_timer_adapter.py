"""Prototype: publish the furthest checkpoint racer's time to both client timers.

Underlying native progression is per racer. Do not sum bonuses or advance counters.
Requires the companion both-human registration prototype. No world transforms.
"""
from checkpoint_humans_adapter import Code, story_guard

SITES = (0x13DBAA2, 0x13DBAFE)
ORIGINAL = bytes.fromhex('d94304518bce')  # fld [ebx+4]; push ecx; mov ecx,esi


def select_record(records):
    """Reference policy, stable first record when checkpoint indices tie."""
    if not records:
        raise ValueError('No racers')
    return max(records, key=lambda record: record['checkpoint'])


def make_code(base, site):
    if site not in SITES:
        raise ValueError('Unknown serialization site')
    code = Code(base)
    code.emit('9c60813f88ab5b02')  # Exact checkpoint replication proxy vtable.
    code.branch('0f85', 'fallback')
    story_guard(code, 'fallback')
    code.emit('8b77308b4f3485f6')
    code.branch('0f84', 'fallback')
    code.emit('39f1')
    code.branch('0f86', 'fallback')
    code.emit('89c829f03d00060000')  # <=64 native 24-byte racer records.
    code.branch('0f87', 'fallback')
    code.emit('31d2bb18000000f7f385d2')
    code.branch('0f85', 'fallback')
    code.emit('89f08b6e0883c618')  # First record is initial best.
    code.label('loop')
    code.emit('39ce')
    code.branch('0f83', 'selected')
    code.emit('8b560839ea')
    code.branch('0f86', 'next')
    code.emit('89d589f0')
    code.label('next')
    code.emit('83c618')
    code.branch('e9', 'loop')
    code.label('selected')
    code.emit('d94004619d518bce')
    code.branch('e9', site + len(ORIGINAL))
    code.label('fallback')
    code.emit('619d')
    code.data += ORIGINAL
    code.branch('e9', site + len(ORIGINAL))
    return code.finish()
