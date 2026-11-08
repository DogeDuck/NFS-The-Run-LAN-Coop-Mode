"""Hide an empty LAN Story leaderboard when the native HUD is shown/rebuilt.

CALL915894 is the native HUD-show path immediately before 90D570 builds the list.
Use the native visibility setter for widget1: no local racer -> hide and skip the
builder; racer present -> enable and build normally. This also allows the list
back on the next native HUD-show after a scene. Does NOT identify every cutscene
when racers still exist. Preserve GPRs/flags and FPU/SIMD across the extra UI call.
"""
from checkpoint_humans_adapter import Code
from pause_ai_adapter import absolute
from coop_hud_adapter import guard

SITE, NATIVE = 0x915894, 0x90D570
RACERS, PLAYERS, LOCAL_RACER, SET_VISIBLE = 0x28824F8, 0x2888F78, 0x866A60, 0x9015E0
SITE_BYTES = bytes.fromhex('e8d77cffff')
CODE_SECTION, DATA_SECTION = b'.emptyhd', b'.emptyhs'


def make_code(base, stats):
    c = Code(base)
    c.emit('9c60')
    guard(c)
    absolute(c, 'ff05', stats)
    c.emit('89ce')                  # ESI = HUD this (callee-saved)
    # Reserve 544 bytes; aligned FXSAVE512 plus room for alignment padding.
    # Align UP inside reserved memory; a buffer below ESP would be clobbered by CALL.
    c.emit('81ec200200008d6c240f83e5f00fae4500')
    absolute(c, 'a1', PLAYERS); c.emit('85c0'); c.branch('0f84', 'empty')
    absolute(c, '8b0d', RACERS); c.emit('85c9'); c.branch('0f84', 'empty')
    c.branch('e8', LOCAL_RACER)
    c.emit('85c0'); c.branch('0f84', 'empty')
    absolute(c, 'ff05', stats + 8)
    c.emit('6a016a0189f1')           # native setter(this HUD, widget1, enabled1)
    c.branch('e8', SET_VISIBLE)
    c.emit('0fae4d0081c420020000')  # FXRSTOR; release scratch
    c.label('native')
    c.emit('619d'); c.branch('e9', NATIVE)
    c.label('empty')
    absolute(c, 'ff05', stats + 4)
    c.emit('6a006a0189f1')
    c.branch('e8', SET_VISIBLE)
    c.emit('0fae4d0081c420020000619dc3')
    return c.finish()
