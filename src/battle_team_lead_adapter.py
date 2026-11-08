"""Client: Eliminator/Battle lead counts for the whole human team (ELIMINATOR-TEAM-2026-11-08.md).

Native 98C640(this=battle, float* outLocal, float* outRival), RET 8:
  local = 8635B0(local player id), rival = 8635B0([battle+A8]); compares racer+24 (route progress).
  no local racer -> 0 (not leading); no rival -> 1 (leading); else local >= rival.
Live 08.11.: both clients see identical racer progress for every racer, humans included.
The client vector [[2888F78]+9C..+A0] can also contain bots. ClientPlayer+260 is the
native bot byte (F42020 / vtable+18); only verified ClientPlayers with byte 0 join the team.

Adapter (JMP over the first 10 bytes of 98C640):
- best = human racer with the highest +24 among the human players (1..16 humans, any order).
- rival racer missing -> 1, like native. rival is itself a human -> 1: a teammate is never an opponent.
- no human racer -> 0, like native without a local racer.
- otherwise write outLocal=best.+24, outRival=rival.+24 (if pointers given), return best >= rival.
- non-LAN Story, invalid player schema/vector -> exact native code (relocated prologue).
One human = native behaviour for that human.
"""
import struct
from checkpoint_humans_adapter import Code
from coop_hud_adapter import guard as lan_story_guard

SITE, RESUME = 0x98C640, 0x98C64A
SITE_BYTES = bytes.fromhex('56578bf98b0d788f8802')
LOOKUP, PLAYERS, RACERS = 0x8635B0, 0x2888F78, 0x28824F8
PLAYER_VTABLE, BOT_GETTER = 0x254F020, 0xF42020
CALLS, TEAM, NATIVE_FALLBACK = 0, 4, 8
CODE_SECTION, DATA_SECTION = b'.btllead', b'.btlleas'


def absolute(c, op, address, tail=''):
    c.emit(op)
    c.data += struct.pack('<I', address)
    if tail:
        c.emit(tail)


def make_code(base, stats):
    c = Code(base)
    absolute(c, 'ff05', stats + CALLS)
    # Guard reads EAX only; native fallback retains the original battle ECX.
    lan_story_guard(c)
    absolute(c, 'a1', RACERS)
    c.emit('85c0'); c.branch('0f84', 'native')
    absolute(c, 'a1', PLAYERS)                    # eax = client player manager
    c.emit('85c0'); c.branch('0f84', 'native')
    c.emit('8b909c000000')                        # edx = begin (+9C)
    c.emit('8b80a0000000')                        # eax = end (+A0)
    c.emit('85d2'); c.branch('0f84', 'native')
    c.emit('29d0'); c.branch('0f86', 'native')    # eax = bytes; <=0 -> native
    c.emit('a803'); c.branch('0f85', 'native')    # misaligned
    c.emit('83f840'); c.branch('0f87', 'native')  # > 16 humans
    # frame: [esp+0]=best racer, [esp+4]=rival racer, [esp+8]=rival is human
    c.emit('5356575583ec0c')                      # push ebx,esi,edi,ebp; sub esp,0C
    c.emit('89cf')                                # edi = battle
    c.emit('89d6')                                # esi = cursor
    c.emit('8d1c02')                              # ebx = end pointer
    c.emit('c7042400000000c744240800000000')      # best=0, rivalHuman=0
    # rival = 8635B0([battle+A8])
    c.emit('ffb7a8000000')
    absolute(c, '8b0d', RACERS); c.branch('e8', LOOKUP)
    c.emit('89442404')                            # [esp+4] = rival
    c.label('loop')
    c.emit('39de'); c.branch('0f83', 'done')
    c.emit('8b06'); c.emit('83c604')              # eax = player; cursor += 4
    c.emit('85c0'); c.branch('0f84', 'loop')
    c.emit('8138'); c.data += struct.pack('<I', PLAYER_VTABLE)
    c.branch('0f85', 'native_frame')
    c.emit('80b86002000001'); c.branch('0f84', 'loop')  # native bot -> exclude
    c.emit('80b86002000000'); c.branch('0f85', 'native_frame')  # unknown flag -> native
    c.emit('8b8034030000')                        # eax = player id (+334)
    c.emit('3b87a8000000'); c.branch('0f85', 'lookup')
    c.emit('c744240801000000')                    # rival id is a human
    c.label('lookup')
    c.emit('50')
    absolute(c, '8b0d', RACERS); c.branch('e8', LOOKUP)
    c.emit('85c0'); c.branch('0f84', 'loop')
    c.emit('8b0c24'); c.emit('85c9'); c.branch('0f84', 'take')
    c.emit('f30f104024')                          # xmm0 = candidate +24
    c.emit('0f2e4124'); c.branch('0f86', 'loop')  # ucomiss xmm0,[best+24]; not greater -> keep
    c.label('take')
    c.emit('890424'); c.branch('e9', 'loop')
    c.label('done')
    absolute(c, 'ff05', stats + TEAM)
    c.emit('8b0424'); c.emit('85c0'); c.branch('0f84', 'not_leading')   # no human racer
    c.emit('8b4c2404'); c.emit('85c9'); c.branch('0f84', 'leading')     # no rival
    c.emit('837c240800'); c.branch('0f85', 'leading')                    # teammate is never an opponent
    c.emit('f30f104024'); c.emit('f30f104924')    # xmm0 = best, xmm1 = rival
    c.emit('8b54242085d27404f30f1102')            # outLocal ([esp+20]) = best
    c.emit('8b54242485d27404f30f110a')            # outRival ([esp+24]) = rival
    c.emit('0f2ec1'); c.branch('0f83', 'leading')  # best >= rival
    c.label('not_leading')
    c.emit('31c0'); c.branch('e9', 'out')
    c.label('leading')
    c.emit('b801000000')
    c.label('out')
    c.emit('83c40c5d5f5e5b')                      # add esp,0C; pop ebp,edi,esi,ebx
    c.emit('c20800')
    c.label('native_frame')
    c.emit('89f9')                                # restore battle ECX before native prologue
    c.emit('83c40c5d5f5e5b')
    c.label('native')
    absolute(c, 'ff05', stats + NATIVE_FALLBACK)
    c.emit('56578bf9'); absolute(c, '8b0d', PLAYERS)   # relocated native prologue
    c.branch('e9', RESUME)
    return c.finish()
