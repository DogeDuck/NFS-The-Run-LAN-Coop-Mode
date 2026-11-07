"""Opt-in LAN Story HUD policy: native Career leaderboard, hide Story clocks.

Only the HUD-local mode booleans change. CareerMode=1, StoryMode=2 and widget
indices are verified against the executable's reflected enum tables by builder.
No race mode, ranking, progress, time or finish data are written or fabricated.
"""
import struct
from checkpoint_humans_adapter import Code
from pause_ai_adapter import absolute, ONLINE

MODE = 0x288239C
POLICY_SITE, POLICY_RETURN = 0x915856, 0x91585E
POLICY_BYTES = bytes.fromhex('5332db57385c2412')
VISIBILITY_SITE, VISIBILITY_RETURN = 0x9015E0, 0x9015E6
VISIBILITY_BYTES = bytes.fromhex('558bec83e4f0')
VISIBILITY_OFFSET = 0x200
RACE_TIMER, SPLIT_TIMES, LEADERBOARD = 6, 8, 1


def guard(c):
    absolute(c, 'a1', ONLINE); c.emit('85c0'); c.branch('0f84', 'native')
    c.emit('80780800'); c.branch('0f85', 'native')
    c.emit('83b8a400000003'); c.branch('0f85', 'native')
    absolute(c, 'a1', MODE); c.emit('85c0'); c.branch('0f84', 'native')
    c.emit('83780402'); c.branch('0f85', 'native')


def policy_code(base, stats):
    c=Code(base);c.emit('9c60')
    guard(c)
    # Original ESP+9 = Career, +A = Story, +B = Challenge. pushfd/pushad=36.
    c.emit('c644242d01c644242e00c644242f00')
    absolute(c,'ff05',stats)
    c.label('native');c.emit('619d');c.data+=POLICY_BYTES
    c.branch('e9',POLICY_RETURN)
    return c.finish()


def visibility_code(base, stats):
    c=Code(base);c.emit('9c60');guard(c)
    c.emit('8b44242883f806');c.branch('0f84','timer')
    c.emit('83f808');c.branch('0f85','native')
    absolute(c,'ff05',stats+8);c.branch('e9','hide')
    c.label('timer');absolute(c,'ff05',stats+4)
    c.label('hide');c.emit('c744242c00000000') # original enable argument, ESP+8
    c.label('native');c.emit('619d');c.data+=VISIBILITY_BYTES
    c.branch('e9',VISIBILITY_RETURN)
    return c.finish()


def make_code(base, stats):
    p=policy_code(base,stats)
    if len(p)>VISIBILITY_OFFSET:raise ValueError('HUD policy overlaps visibility adapter')
    return p+b'\xcc'*(VISIBILITY_OFFSET-len(p))+visibility_code(base+VISIBILITY_OFFSET,stats)
