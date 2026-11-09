"""OFFLINE UNTESTED candidate: retain native Story HUD policy during OOC/QTE.

Existing coop_hud_adapter substitutes Career HUD in ALL connected Story scenes.
This narrower alternative leaves OOC mode booleans and native widget requests
alone, except suppressing its inappropriate MP leaderboard. Camera/actors/input
are separate: this is NOT a claim that restoring HUD policy repairs them.
"""
from checkpoint_humans_adapter import Code
from pause_ai_adapter import absolute
import coop_hud_adapter as old


CHALLENGE_CONTROLLER = 0x28824E8
OOC = 3  # Reflected ChallengeGameplayType_OOC at2B1FD1C: name25A2E2C,value3.
OOC_POLICY_KEPT, OOC_LIST_HIDDEN = 12, 16
STATS_SIZE = 20


def challenge_route(c, ooc, driving, unknown='native'):
    absolute(c, 'a1', CHALLENGE_CONTROLLER)
    c.emit('85c0'); c.branch('0f84', unknown)
    c.emit('8b401085c0'); c.branch('0f84', unknown)
    # Native HUD915866 loads the same Challenge pointer,915869 reads+28.
    c.emit('83782803'); c.branch('0f84', ooc)
    c.branch('e9', driving)


def policy_code(base, stats):
    c = Code(base)
    c.emit('9c60')
    old.guard(c)
    challenge_route(c, 'ooc', 'driving')
    c.label('driving')
    c.emit('c644242d01c644242e00c644242f00')
    absolute(c, 'ff05', stats)
    c.branch('e9', 'native')
    c.label('ooc')
    absolute(c, 'ff05', stats+OOC_POLICY_KEPT)
    # Clear a leaderboard left by the previous race even when the native OOC
    # branch never issues another visibility request for widget1. SetVisible
    # may use SIMD/FPU: retain it across this extra native UI call.
    c.emit('81ec200200008d6c240f83e5f00fae4500')
    c.emit('89f16a006a01')  # native91587A/9158AF use ESI=HUD; ECX is volatile here
    c.branch('e8', old.VISIBILITY_SITE)
    c.emit('0fae4d0081c420020000')
    c.label('native')
    c.emit('619d'); c.data += old.POLICY_BYTES
    c.branch('e9', old.POLICY_RETURN)
    return c.finish()


def visibility_code(base, stats):
    c = Code(base)
    c.emit('9c60')
    old.guard(c)
    challenge_route(c, 'ooc', 'driving')
    c.label('ooc')
    c.emit('8b44242883f801')
    c.branch('0f85', 'native')  # In OOC preserve ALL other native widget requests.
    absolute(c, 'ff05', stats+OOC_LIST_HIDDEN)
    c.branch('e9', 'hide')
    c.label('driving')
    c.emit('8b44242883f806'); c.branch('0f84', 'timer')
    c.emit('83f808'); c.branch('0f85', 'native')
    absolute(c, 'ff05', stats+8); c.branch('e9', 'hide')
    c.label('timer')
    absolute(c, 'ff05', stats+4)
    c.label('hide')
    c.emit('c744242c00000000')
    c.label('native')
    c.emit('619d'); c.data += old.VISIBILITY_BYTES
    c.branch('e9', old.VISIBILITY_RETURN)
    return c.finish()


def make_code(base, stats):
    policy = policy_code(base, stats)
    if len(policy) > old.VISIBILITY_OFFSET:
        raise ValueError('OOC policy overlaps visibility code')
    return (policy+b'\xcc'*(old.VISIBILITY_OFFSET-len(policy))
            + visibility_code(base+old.VISIBILITY_OFFSET, stats))
