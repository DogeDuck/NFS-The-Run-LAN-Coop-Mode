"""Offline candidate: one verified HOST advances two authored 10.4 milestones.

IMPORTANT authoring correction: fa70447f comes from kickandrun.OnStarted;
f6751589 comes from herostealscar.OnFinished. They are NOT loading acknowledgments.
Never wait for every human here. Host's real report emits native Out once. Other
EventSync nodes remain native. Retry and source-subworld reload rearm the state.

Sender: native NetworkMessage getter 1850800 returns message+28; native server
users (1331C60) pass that connection to 12F2210, which returns +1910 player.
Roster: ServerPlayerManager+78..7C, human iff ServerPlayer+260 is zero.
"""
import struct
import uuid
from checkpoint_humans_adapter import Code, story_guard
from pause_ai_adapter import absolute

HANDLER, RESUME, MAP_FIND, PEER_PLAYER = 0x12A3AC0,0x12A3ACB,0x12A2A10,0x12F2210
HEAD=bytes.fromhex('8b442404817808208b8f45')
RESET,RESET_RESUME=0x13D0050,0x13D0055
RESET_HEAD=bytes.fromhex('83ec205657')
SUB_VT,SUB_NATIVE=0x2593350,0x1297BB0
SUB_SLOT=SUB_VT+0xC
SYNC_VT=0x2595150
PLAYERS=0x28A3220
RESET_OFFSET,SUB_OFFSET,TRAMP_OFFSET=0x800,0xA00,0xC00
CACHE,SLOTS,STRIDE=0x40,8,20
STATS_SIZE=CACHE+SLOTS*STRIDE
CALLS,NATIVE_CALLS,WAITING,FIRED,DUPLICATES,FALLBACK,RETRIES,REARMS=range(0,32,4)
GUEST_IGNORED=WAITING
CTX,CHALLENGE,COUNT,ROSTER=0x20,0x24,0x28,0x30
HOST=0x2C
HOST_SELECTOR,HOST_STATE=0x132AC60,0x2B8F000
SYNC_GUIDS=(('fa70447f-b919-413e-b4af-309c653c4135',1),
            ('f6751589-2042-49ab-a421-0918940b2b6d',2))
SUB_GUIDS=(('43af5e6f-647f-448f-b64a-df6b7d646197',1),
           ('3fa7387e-ba40-4727-9b77-15c3f2527b46',2))


def guid(c,reg,value,miss):
    for off,word in zip((0xF0,0xF4,0xF8,0xFC),struct.unpack('<4I',uuid.UUID(value).bytes_le)):
        c.emit('81'+format(0x78+reg,'02x')+format(off,'02x'))
        c.data+=struct.pack('<I',word);c.branch('0f85',miss)


def clear(c,stats,label):
    absolute(c,'be',stats+CACHE);c.emit('b908000000')
    c.label(label)
    c.emit('c70600000000c7460c0000000083c61449');c.branch('0f85',label)


def gate(base,stats):
    c=Code(base);c.emit('9c6083ec30');absolute(c,'ff05',stats+CALLS)
    story_guard(c,'native')
    c.emit('894424288b401085c0');c.branch('0f84','native')
    c.emit('83782803');c.branch('0f85','native')
    c.emit('8944242c8b7c2458817f08208b8f45');c.branch('0f85','native')
    # Verify native connection -> player, retained on this invocation's stack.
    c.emit('8b4f2885c9');c.branch('0f84','fallback')
    c.branch('e8',PEER_PLAYER)
    c.emit('85c0');c.branch('0f84','fallback');c.emit('89442414')
    # Native tree lookup; unlike the original handler, retain its message arg.
    c.emit('8d4424208d573852508b4c24508d4908')
    c.branch('e8',MAP_FIND)
    c.emit('8b4424208b4c244883c10c39c8');c.branch('0f84','native')
    c.emit('8b701085f6');c.branch('0f84','native')
    c.emit('813e');c.data+=struct.pack('<I',SYNC_VT);c.branch('0f85','native')
    c.emit('897424188b4e1085c9');c.branch('0f84','native')
    guid(c,1,SYNC_GUIDS[0][0],'second_guid');c.emit('ba01000000');c.branch('e9','classified')
    c.label('second_guid');guid(c,1,SYNC_GUIDS[1][0],'native');c.emit('ba02000000')
    c.label('classified');c.emit('8954241c')
    # Assemble 2..4 distinct humans from the real player list, never racers.
    absolute(c,'a1',PLAYERS);c.emit('85c0');c.branch('0f84','fallback')
    c.emit('8b70788b787c85f6');c.branch('0f84','fallback')
    c.emit('89fa29f2');c.branch('0f82','fallback')
    c.emit('81fa00010000');c.branch('0f87','fallback')
    c.emit('f7c203000000');c.branch('0f85','fallback');c.emit('31ed')
    c.label('human_loop');c.emit('39fe');c.branch('0f84','roster_done')
    c.emit('8b0683c60485c0');c.branch('0f84','human_loop')
    c.emit('80b86002000000');c.branch('0f85','human_loop')
    c.emit('83fd04');c.branch('0f83','fallback');c.emit('31c9')
    c.label('unique');c.emit('39e9');c.branch('0f84','store_human')
    c.emit('39048c');c.branch('0f84','fallback');c.emit('41');c.branch('e9','unique')
    c.label('store_human');c.emit('8904ac45');c.branch('e9','human_loop')
    c.label('roster_done');c.emit('83fd02');c.branch('0f82','native')
    c.emit('896c24108b442428');absolute(c,'3b05',stats+CTX);c.branch('0f85','epoch')
    c.emit('8b44242c');absolute(c,'3b05',stats+CHALLENGE);c.branch('0f85','epoch')
    # Host authority has no per-roster-position ACK mask. A join, leave or list
    # reorder must NOT rearm an already completed story milestone.
    c.branch('e9','update_roster')
    c.label('epoch');clear(c,stats,'epoch_clear')
    c.emit('8b442428');absolute(c,'a3',stats+CTX)
    c.emit('8b44242c');absolute(c,'a3',stats+CHALLENGE)
    c.label('update_roster');absolute(c,'892d',stats+COUNT);c.emit('31c9')
    c.label('copy_roster');c.emit('39e9');c.branch('0f84','source_index')
    c.emit('8b048c');absolute(c,'ba',stats+ROSTER);c.emit('89048a41');c.branch('e9','copy_roster')
    c.label('source_index');c.emit('8b44241431c9')
    c.label('source_loop');c.emit('39e9');c.branch('0f84','fallback')
    c.emit('39048c');c.branch('0f84','have_source');c.emit('41');c.branch('e9','source_loop')
    c.label('have_source')
    # Use the installed native host-name selector, then verify the explicit name
    # ourselves: its native fallback can otherwise return the first human.
    absolute(c,'8b0d',PLAYERS);c.branch('e8',HOST_SELECTOR)
    c.emit('85c0');c.branch('0f84','fallback')
    absolute(c,'833d',HOST_STATE+12);c.emit('02');c.branch('0f85','fallback')
    c.emit('894424248b701085f6');c.branch('0f84','fallback')
    absolute(c,'bf',HOST_STATE+0x40);c.emit('ba40000000')
    c.label('host_name');c.emit('8a063a07');c.branch('0f85','fallback')
    c.emit('84c0');c.branch('0f84','verified_host')
    c.emit('46474a');c.branch('0f85','host_name');c.branch('e9','fallback')
    c.label('verified_host');c.emit('8b442424');absolute(c,'a3',stats+HOST)
    c.emit('3b442414');c.branch('0f85','guest')
    c.emit('c744242001000000c744242401000000')
    # Match a current entity/data/bus tuple; no pointer survives a native call.
    c.emit('8b5424188b7a108b6a0c')
    absolute(c,'be',stats+CACHE);c.emit('b90800000031db')
    c.label('slot');c.emit('8b0639d0');c.branch('0f85','other_slot')
    c.emit('397e04');c.branch('0f85','initialize')
    c.emit('396e08');c.branch('0f84','have_slot');c.branch('e9','initialize')
    c.label('other_slot');c.emit('85c0');c.branch('0f85','next_slot')
    c.emit('85db');c.branch('0f85','next_slot');c.emit('89f3')
    c.label('next_slot');c.emit('83c61449');c.branch('0f85','slot')
    c.emit('85db');c.branch('0f84','fallback');c.emit('89de')
    c.label('initialize');c.emit('8916897e04896e08c7460c000000008b44241c894610')
    c.label('have_slot');c.emit('8b460ca900000080');c.branch('0f85','duplicate')
    c.emit('8b54242085d0');c.branch('0f85','duplicate')
    c.emit('09d089460c3b442424');c.branch('0f85','wait')
    c.emit('0d0000008089460c');absolute(c,'ff05',stats+FIRED);c.branch('e9','native')
    c.label('wait');c.branch('e9','fallback') # Unreachable: one authoritative host bit.
    c.label('guest');absolute(c,'ff05',stats+GUEST_IGNORED);c.branch('e9','skip')
    c.label('duplicate');absolute(c,'ff05',stats+DUPLICATES);c.branch('e9','skip')
    c.label('fallback');absolute(c,'ff05',stats+FALLBACK)
    c.label('native');absolute(c,'ff05',stats+NATIVE_CALLS)
    c.emit('83c430619d');c.branch('e9',base+TRAMP_OFFSET)
    c.label('skip');c.emit('83c430619dc20400')
    return c.finish()


def reset(base,stats):
    c=Code(base);c.emit('9c608b442428817808839712b1');c.branch('0f84','clear')
    c.emit('8178087464cb94');c.branch('0f85','native')
    c.label('clear');clear(c,stats,'reset_loop')
    for off in (CTX,CHALLENGE,COUNT):absolute(c,'c705',stats+off);c.data+=bytes(4)
    absolute(c,'ff05',stats+RETRIES)
    c.label('native');c.emit('619d');c.data+=RESET_HEAD;c.branch('e9',RESET_RESUME)
    return c.finish()


def subworld(base,stats):
    c=Code(base);c.emit('9c6089cf');story_guard(c,'native')
    c.emit('8b401085c0');c.branch('0f84','native')
    c.emit('83782803');c.branch('0f85','native')
    c.emit('813f');c.data+=struct.pack('<I',SUB_VT);c.branch('0f85','native')
    c.emit('807f2900');c.branch('0f85','native') # native pending guard
    c.emit('8b4424288b500481fa6eba7604');c.branch('0f84','accepted')
    c.emit('81fa7ec17bd2');c.branch('0f84','conditional')
    c.emit('81fa77f6f321');c.branch('0f85','native')
    c.emit('807f2800');c.branch('0f85','accepted');c.branch('e9','native')
    c.label('conditional');c.emit('807f2800');c.branch('0f85','native')
    c.label('accepted');c.emit('8b4f1085c9');c.branch('0f84','native')
    guid(c,1,SUB_GUIDS[0][0],'sub_second');c.emit('ba01000000');c.branch('e9','rearm')
    c.label('sub_second');guid(c,1,SUB_GUIDS[1][0],'native');c.emit('ba02000000')
    c.label('rearm');absolute(c,'be',stats+CACHE);c.emit('b908000000')
    c.label('rearm_loop');c.emit('395610');c.branch('0f85','next')
    c.emit('c70600000000c7460c00000000')
    c.label('next');c.emit('83c61449');c.branch('0f85','rearm_loop')
    absolute(c,'ff05',stats+REARMS)
    c.label('native');c.emit('619d');c.branch('e9',SUB_NATIVE)
    return c.finish()


def make_code(base,stats):
    parts=((0,gate(base,stats)),(RESET_OFFSET,reset(base+RESET_OFFSET,stats)),
           (SUB_OFFSET,subworld(base+SUB_OFFSET,stats)),
           (TRAMP_OFFSET,HEAD+b'\xe9'+struct.pack('<i',RESUME-(base+TRAMP_OFFSET+len(HEAD)+5))))
    result=bytearray()
    for offset,code in parts:
        if len(result)>offset:raise ValueError('QTE readiness code overlap')
        result+=b'\xcc'*(offset-len(result))+code
    return bytes(result)
