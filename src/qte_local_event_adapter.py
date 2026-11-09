"""EXPERIMENTAL: give each client its local human context for received OOC player events.

Hypothesis, not a demonstrated game fix: the native network message names the
story player. Client logic/property resolution can then remain bound to a remote
human, while its local ANT/camera graph never starts. At E21C9A the engine makes
a ClientPlayerEvent from that player. In a separate opt-in candidate only, replace
that constructor's player argument with the current local human during connected
LAN Story OOC. Keep the original message, logic bus, event/index and all replies.

No fake QTE success, no event replay, no actor/camera teleport, no EventSync mute.
Driving, solo, missing context, bots and unknown schemas keep the original call.
No role/ID0/ID1 assumption: the native manager +BC is the local player for each
of 2-4 clients. This does NOT yet implement host-only input or guarantee delivery
to a client that never received the original message. Needs a joint live test.
"""
import struct
from checkpoint_humans_adapter import Code
from coop_hud_adapter import guard
from qte_hud_scope_adapter import challenge_route

SITE, NATIVE = 0xE21C9A, 0xEE3DE0
PLAYERS, PLAYER_VT = 0x2888F78, 0x254F020
CALLS, ELIGIBLE, REBOUND = 0, 4, 8
STATS_SIZE = 12


def make_code(base, stats):
    c = Code(base)
    imm = lambda value: struct.pack('<I', value)
    c.emit('9c60')  # flags/registers; constructor args now at +28/+2C
    c.emit('ff05'); c.data += imm(stats + CALLS)
    guard(c)
    challenge_route(c, 'ooc', 'native')
    c.label('ooc')
    c.emit('837c242c00'); c.branch('0f85', 'native')
    c.emit('8b44242885c0'); c.branch('0f84', 'native')
    c.emit('8138'); c.data += imm(PLAYER_VT); c.branch('0f85', 'native')
    c.emit('80b86002000000'); c.branch('0f85', 'native')
    c.emit('8b0d'); c.data += imm(PLAYERS)
    c.emit('85c9'); c.branch('0f84', 'native')
    c.emit('8b89bc00000085c9'); c.branch('0f84', 'native')
    c.emit('8139'); c.data += imm(PLAYER_VT); c.branch('0f85', 'native')
    c.emit('80b96002000000'); c.branch('0f85', 'native')
    c.emit('ff05'); c.data += imm(stats + ELIGIBLE)
    c.emit('39c1'); c.branch('0f84', 'native')
    c.emit('894c2428')  # change only the live constructor argument, never msg+3C
    c.emit('ff05'); c.data += imm(stats + REBOUND)
    c.label('native')
    c.emit('619d'); c.branch('e9', NATIVE)  # native thiscall RET8
    return c.finish()


def call_patch(target):
    return b'\xe8' + struct.pack('<i', target - SITE - 5)
