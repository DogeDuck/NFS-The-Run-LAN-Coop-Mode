"""Candidate: resolve Story OOC spawn links through the local human's pawn bus.

Native EEE300 and EE1EE0 keep +6C = first spawned controllable's +10 bus.
The generic reference resolver 459A00 uses VT+24 (EDA3D0, return +6C).
Cinebot 115E720/115EA80 explicitly select a local pawn using +D8 player,
player+37B bit 3, instead. Apply that same choice to this one spawner type.

No event replay, graph mutation, actor creation, controller replacement, frame
hook, remote thread or shared host/guest player-ID assumption. This is a new
offline candidate, NOT a verified fix for the complete QTE/camera problem.
"""
from checkpoint_humans_adapter import Code
from pause_ai_adapter import absolute
import coop_hud_adapter as hud
from qte_hud_scope_adapter import CHALLENGE_CONTROLLER

SPAWN_VT = 0x246F290
SLOT = SPAWN_VT + 0x24
NATIVE = 0xEDA3D0
BASIC_VT = 0x247F5B8
MAX_PAWNS = 16
NATIVE_CALLS, LOCAL_SELECTED = 0, 4


def make_code(base, stats):
    c = Code(base)
    c.emit('9c60')  # Preserve native getter's flags and all regs except EAX.
    hud.guard(c)
    absolute(c, 'a1', CHALLENGE_CONTROLLER)
    c.emit('85c0'); c.branch('0f84', 'native')
    c.emit('8b401085c0'); c.branch('0f84', 'native')
    c.emit('83782803'); c.branch('0f85', 'native')
    c.emit('8139'); c.data += SPAWN_VT.to_bytes(4, 'little')
    c.branch('0f85', 'native')
    c.emit('8b715c8b7960')  # ESI=begin, EDI=end, engine-owned pointer vector.
    c.emit('85f6'); c.branch('0f84', 'native')
    c.emit('89fa29f2'); c.branch('0f82', 'native')
    c.emit('f7c203000000'); c.branch('0f85', 'native')
    c.emit('83fa'); c.data += bytes([4 * MAX_PAWNS])
    c.branch('0f87', 'native')
    c.label('loop')
    c.emit('39fe'); c.branch('0f84', 'native')
    c.emit('8b0685c0'); c.branch('0f84', 'next')
    c.emit('8138'); c.data += BASIC_VT.to_bytes(4, 'little')
    c.branch('0f85', 'next')
    c.emit('8b90d800000085d2'); c.branch('0f84', 'next')
    c.emit('f6827b03000008'); c.branch('0f84', 'next')
    c.emit('8b401085c0'); c.branch('0f84', 'next')
    c.emit('8944241c')  # Saved EAX = locally owned pawn's native bus.
    absolute(c, 'ff05', stats + LOCAL_SELECTED)
    c.emit('619dc3')
    c.label('next')
    c.emit('83c604'); c.branch('e9', 'loop')
    c.label('native')
    absolute(c, 'ff05', stats + NATIVE_CALLS)
    c.emit('619d'); c.branch('e9', NATIVE)
    return c.finish()
