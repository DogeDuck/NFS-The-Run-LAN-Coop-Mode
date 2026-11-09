"""Server adapter: in story 10.5 every human gets an own police car from the same native spawner.

Native 10.5 (Challenge 28ff8b76, Survival): the spawner 25e92e81 (MaxCount 1) spawns ONE police car,
VehicleInteraction 13E2A70 puts the story player in it via 13D8510(player, vehicle) (ECX unused).
Every other human stays without vehicle (live 09.11.: guest without car/control, camera under map).

Version 2 (live 09.11. 22:04): scripted scenes (train QTE end of 10.5, ANT link to the spawner) use the
LAST car of the spawner (server 12F4DB0 = last list element; clients the newest spawned). With v1 that was
the guest car: Jack missing, QTE did not start on both clients. Therefore the STORY player now gets the
LAST car: the other humans take the cars in spawn order, the story player enters the final one.

Adapter (RAM, server only, 2-4 humans, guarded to challenge 10.5):
  A  CALL 13E2B46 -> 13D8510 (story player would enter car 1). If the spawner of that car
     ([car+DC], vtable 25918F0 = vehicle spawner) holds exactly this car: assign(car 1); else native.
  assign(car i = cars-1): occupant = i-th non-bot human that is not the story player; if there is none,
     the story player (end of chain). Other human: native entry 13D8510(human, car), then request the next
     car: native getTransform (vfunc +4C), moved 8 m * cars along negative forward, written to the native
     request pose (+EF0 flag, +F00 matrix, read by 127EAA1), spawn counter +84 minus one so the MaxCount
     check (12F8310) allows one more, native request 1305F90.
  C  vtable slot +A0 of 25918F0 (spawn completion 1304650): after the native completion of the armed
     spawner: +EF0 = 0 (later native respawns use the authored pose), assign(new car).
With one human everything is native order (story player enters car 1 directly).
No vehicle memory is copied, no player list/bot flag is written. XMM/x87 state saved around own calls.
"""
import struct
import uuid
from checkpoint_humans_adapter import Code

GUID = uuid.UUID('28ff8b76-510f-40cf-979e-3f061eade803')       # Challenge 10_5
ENTER_SITE, ENTER = 0x13E2B46, 0x13D8510
SLOT, DONE = 0x2591990, 0x1304650                               # vtable 25918F0 + A0
VTABLE, REQUEST = 0x25918F0, 0x1305F90
PLAYERS, BOT_OFFSET = 0x28A3220, 0x260
SPAWNER_OF, LIST, COUNT, HAS_POSE, POSE = 0xDC, 0xDA8, 0x84, 0xEF0, 0xF00
GET_TRANSFORM = 0x4C
CALLS_ENTER, CALLS_DONE, GUARD_REJECT, TYPE_REJECT, ARMS, ENTERS, STORY_ENTERS = 0, 4, 8, 0xC, 0x10, 0x14, 0x18
ARMED_SPAWNER, LAST_OTHER, STORY, LAST_VEHICLE, LAST_STORY_VEHICLE = 0x1C, 0x20, 0x24, 0x28, 0x2C
OFFSET, TMP, STATS_SIZE = 0x30, 0x40, 0x80
METERS = 8.0


def challenge_guard(c, fail):
    """Same check as story_start_spawn_adapter.story_guard (challenge 10.5 only), no internal labels."""
    c.emit('a1'); c.data += struct.pack('<I', 0x28E5C80)
    c.emit('85c0'); c.branch('0f84', fail)
    c.emit('8138506d5b02'); c.branch('0f85', fail)
    c.emit('8b401085c0'); c.branch('0f84', fail)
    for i, word in enumerate(struct.unpack('<4I', GUID.bytes_le)):
        c.emit('8178' + bytes([0xF0 + 4 * i]).hex()); c.data += struct.pack('<I', word)
        c.branch('0f85', fail)


def stats_init(meters=METERS):
    return bytes(OFFSET) + struct.pack('<f', meters) + bytes(STATS_SIZE - OFFSET - 4)


def make_code(base, stats):
    """Returns (code, entry_a, entry_c)."""
    c = Code(base)
    a = lambda op, v: (c.emit(op), c.data.extend(struct.pack('<I', v)))
    # ---- A: story player would enter car 1 ----
    c.label('entry_a')
    c.emit('5589e59c60'); a('ff05', stats + CALLS_ENTER)
    challenge_guard(c, 'a_reject')
    c.emit('8b7d0c85ff'); c.branch('0f84', 'a_native')
    c.emit('8bb7' + struct.pack('<I', SPAWNER_OF).hex() + '85f6'); c.branch('0f84', 'a_type')
    c.emit('8b06'); a('3d', VTABLE); c.branch('0f85', 'a_type')
    c.emit('8b86a80d00008b96ac0d000029c283fa04'); c.branch('0f85', 'a_native')   # exactly one car
    c.emit('3938'); c.branch('0f85', 'a_type')                                  # it is this car
    a('893d', stats + LAST_VEHICLE)
    c.emit('8b4508'); a('a3', stats + STORY)
    c.branch('e8', 'fx_assign')
    c.emit('619d5dc20800')
    c.label('a_reject'); a('ff05', stats + GUARD_REJECT); c.branch('e9', 'a_native')
    c.label('a_type'); a('ff05', stats + TYPE_REJECT)
    c.label('a_native'); c.emit('619d5d'); c.branch('e9', ENTER)                 # untouched native call
    # ---- C: spawn completion (vtable slot) ----
    c.label('entry_c')
    c.emit('5589e551ff7508'); c.branch('e8', DONE); c.emit('59')
    c.emit('9c60'); a('ff05', stats + CALLS_DONE)
    c.emit('85c9'); c.branch('0f84', 'c_out')
    a('3b0d', stats + ARMED_SPAWNER); c.branch('0f85', 'c_out')
    c.emit('89ce'); a('c705', stats + ARMED_SPAWNER); c.emit('00000000')
    c.emit('c686f00e000000')                                                    # native pose off again
    challenge_guard(c, 'c_reject')
    c.emit('8b7d0885ff'); c.branch('0f84', 'c_out')
    c.branch('e8', 'fx_assign'); c.branch('e9', 'c_out')
    c.label('c_reject'); a('ff05', stats + GUARD_REJECT)
    c.label('c_out'); c.emit('619d5dc20400')
    # ---- FXSAVE wrapper (ESP restored from the aligned area) ----
    c.label('fx_assign')
    c.emit('89e081ec1002000083e4f0898424000200000fae0424fc')
    c.branch('e8', 'assign')
    c.emit('0fae0c248ba42400020000c3')
    # ---- assign(ESI = spawner, EDI = car) ----
    c.label('assign')
    c.emit('8b86ac0d00002b86a80d0000c1f80248'); c.branch('0f88', 'ret')         # i = cars-1
    c.emit('89c3'); a('8b0d', PLAYERS)
    c.emit('85c9'); c.branch('0f84', 'story')
    c.emit('8b517c8b4978')
    c.label('scan')
    c.emit('39d1'); c.branch('0f83', 'story')
    c.emit('8b0183c10485c0'); c.branch('0f84', 'scan')
    c.emit('80b8' + struct.pack('<I', BOT_OFFSET).hex() + '00'); c.branch('0f85', 'scan')
    a('3b05', stats + STORY); c.branch('0f84', 'scan')
    c.emit('85db'); c.branch('0f84', 'other')
    c.emit('4b'); c.branch('e9', 'scan')
    c.label('other')                                                            # EAX = other human
    a('a3', stats + LAST_OTHER)
    c.emit('5750'); c.branch('e8', ENTER); a('ff05', stats + ENTERS)
    # request the next car (index = cars)
    c.emit('8b86ac0d00002b86a80d0000c1f802')                                   # EAX = cars
    c.emit('50'); a('bb', stats + TMP)
    c.emit('5389f18b06ff50' + bytes([GET_TRANSFORM]).hex())                    # getTransform(out), RET 4
    c.emit('58f30f2ac0'); a('f30f5905', stats + OFFSET)
    c.emit('0fc6c0000f104b200f59c80f1053300f5cd10f115330')                      # trans -= fwd*m*cars
    c.emit('56578dbe000f000089deb910000000f3a55f5e')                            # pose = TMP
    c.emit('c686f00e000001')
    c.emit('83be8400000000'); c.branch('0f8e', 'skipdec')
    c.emit('ff8e84000000')
    c.label('skipdec')
    a('8935', stats + ARMED_SPAWNER); a('ff05', stats + ARMS)
    c.emit('89f1'); c.branch('e8', REQUEST)
    c.emit('c3')
    c.label('story')                                                            # end of chain
    a('893d', stats + LAST_STORY_VEHICLE)
    c.emit('57'); a('ff35', stats + STORY); c.branch('e8', ENTER)
    a('ff05', stats + STORY_ENTERS)
    c.label('ret'); c.emit('c3')
    code = c.finish()
    return code, c.labels['entry_a'], c.labels['entry_c']
