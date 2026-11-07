"""DRAFT, not activated, not packaged: BattleRace finish for every human (ELIMINATOR-FINISH-2026-11-04.md).

Native 13E0B30 finishes only the FIRST human (132AC60). Two CALL hooks:
  A  13E0BA2  CALL 132AC60 -> pick_code: return [stats+TARGET] if set, else native 132AC60.
  B  13E2DC2  CALL 13E0B30 -> wrapper_code: story context only; call native 13E0B30 once per
     human in PlayerManager +78..+7C (Player+260 == 0), TARGET = that human. Re-entrant calls
     and non-story contexts run the native function unchanged. One human = identical to native.
13E0C30 (id variant, only for the first human) stays native.
Known side effect: the bot part of 13E0B30 (13CE280(7)) runs once per human; idempotence is
NOT verified in game. Team semantics (both finish together) is a design decision, see notes.
"""
import struct
from checkpoint_humans_adapter import Code, story_guard

PLAYERS = 0x28A3220
PICK_SITE, PICK_NATIVE = 0x13E0BA2, 0x132AC60
WRAP_SITE, WRAP_NATIVE = 0x13E2DC2, 0x13E0B30
# RW state layout
TARGET, BUSY, CALLS, HUMANS = 0, 4, 8, 12
MAX_PLAYERS = 64


def absolute(c, op, address):
    c.emit(op)
    c.data += struct.pack('<I', address)


def pick_code(base, stats):
    c = Code(base)
    absolute(c, 'a1', stats + TARGET)            # mov eax,[TARGET]
    c.emit('85c0')
    c.branch('0f84', PICK_NATIVE)                # not set -> native first-human getter
    c.emit('c3')
    return c.finish()


def wrapper_code(base, stats):
    c = Code(base)
    absolute(c, '833d', stats + BUSY); c.emit('00')
    c.branch('0f85', WRAP_NATIVE)                # re-entrant: plain native (tail jump, ECX intact)
    c.emit('51')                                 # push ecx (battle entity)
    story_guard(c, 'native_pop')                 # clobbers eax only
    c.emit('59')                                 # pop ecx
    c.emit('535657')                             # push ebx,esi,edi
    c.emit('89cf')                               # mov edi,ecx
    absolute(c, 'c705', stats + BUSY); c.emit('01000000')
    absolute(c, 'c705', stats + HUMANS); c.emit('00000000')
    c.emit('31db')                               # xor ebx,ebx  (index)
    c.label('loop')
    absolute(c, 'a1', PLAYERS)                   # re-read bounds every iteration
    c.emit('85c0'); c.branch('0f84', 'done')
    c.emit('8b7078')                             # mov esi,[eax+78]
    c.emit('8b407c')                             # mov eax,[eax+7C]
    c.emit('29f0')                               # sub eax,esi
    c.branch('0f82', 'done')                     # end < begin
    c.emit('c1e802')                             # shr eax,2
    c.emit('83f840'); c.branch('0f87', 'done')   # > 64 players: refuse
    c.emit('39c3'); c.branch('0f83', 'done')     # index >= count
    c.emit('8b049e')                             # mov eax,[esi+ebx*4]
    c.emit('43')                                 # inc ebx
    c.emit('85c0'); c.branch('0f84', 'loop')
    c.emit('80b86002000000'); c.branch('0f85', 'loop')  # bot -> skip
    absolute(c, 'a3', stats + TARGET)
    absolute(c, 'ff05', stats + HUMANS)
    c.emit('89f9')                               # mov ecx,edi
    c.branch('e8', WRAP_NATIVE)
    absolute(c, 'ff05', stats + CALLS)
    c.branch('e9', 'loop')
    c.label('done')
    absolute(c, 'c705', stats + TARGET); c.emit('00000000')
    absolute(c, 'c705', stats + BUSY); c.emit('00000000')
    absolute(c, '833d', stats + HUMANS); c.emit('00')
    c.emit('89f9')                               # ecx = battle for the fallback below
    c.emit('5f5e5b')                             # pop edi,esi,ebx
    c.branch('0f84', WRAP_NATIVE)                # no human found at all: native as before
    c.emit('c3')
    c.label('native_pop')
    c.emit('59')
    c.branch('e9', WRAP_NATIVE)
    return c.finish()
