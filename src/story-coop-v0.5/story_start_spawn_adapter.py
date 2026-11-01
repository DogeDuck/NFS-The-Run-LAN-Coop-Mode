"""Scoped authoritative initial-spawn experiment, initially only challenge3.5.

Human grid selection uses the authored solo ordinal. Each human keeps its own
native source entity. At native vehicle creation, read the authored anchor with
the same virtual getTransform(out) ABI used by the engine. Offset second human
8m along negative forward. One-shot arms prevent applying race-start placement
to later garage swaps. Retry/transition behaviour still requires live validation.
"""
import struct
import uuid
from checkpoint_humans_adapter import Code

GUID=uuid.UUID('6be7deda-d431-4a04-a184-1689dd69b0d2')
SELECT_SITE,SELECT_NATIVE=0x13D6446,0x13DAD50
MATRIX_SITE=0x127EAA1
MATRIX_ORIGINAL=bytes.fromhex('80bbf00e0000007415')
MATRIX_OVERRIDE,MATRIX_CONTINUE=0x127EAAA,0x127EABF
# RW session state. No engine-owned global flags are changed.
SETTINGS,EPOCH,ANCHOR=0,4,8
SOURCES,ARMS,ENABLED=12,20,28
SELECT_COUNT,MATRIX_COUNTS,FALLBACK,OFFSET=32,36,44,64


def absolute(c,op,address):
    c.emit(op);c.data+=struct.pack('<I',address)


def story_guard(c,fail,guids=(GUID,)):
    absolute(c,'a1',0x28E5C80)
    c.emit('85c0');c.branch('0f84',fail)
    c.emit('8138506d5b02');c.branch('0f85',fail)
    c.emit('8b401085c0');c.branch('0f84',fail)
    if not guids:raise ValueError('Explicit authored race allowlist required')
    for index,guid in enumerate(dict.fromkeys(guids)):
        for i,word in enumerate(struct.unpack('<4I',guid.bytes_le)):
            c.emit('8178'+bytes([0xF0+4*i]).hex());c.data+=struct.pack('<I',word)
            c.branch('0f85','allow_next_'+str(index))
        c.branch('e9','allowed')
        c.label('allow_next_'+str(index))
    c.branch('e9',fail)
    c.label('allowed')


def selector_code(base,stats,guids=(GUID,)):
    c=Code(base)
    c.emit('9c60')
    absolute(c,'c705',stats+ENABLED);c.emit('00000000')
    story_guard(c,'native',guids)
    # EAX=current challenge asset; EBX is the original native racer manager.
    absolute(c,'3b1d',0x28E5C90);c.branch('0f85','native')
    absolute(c,'a3',stats+EPOCH)
    absolute(c,'a1',0x28A3228)
    c.emit('85c0');c.branch('0f84','native')
    c.emit('80b8031a000000');c.branch('0f85','native')
    # Only first/second human in this human-only native call; no NPC calls.
    # Native frame local+1C, plus pushed argument4, CALL return4, saved state36.
    c.emit('837c244801');c.branch('0f87','native')
    c.emit('8b74241885f6');c.branch('0f84','native') # incoming settings ECX
    c.emit('8b4e282b4e24');c.branch('0f82','native')
    c.emit('f6c103');c.branch('0f85','native')
    c.emit('c1e90283f902');c.branch('0f82','native')
    c.emit('83f940');c.branch('0f87','native')
    c.emit('8b83cc05000085c0');c.branch('0f84','native')
    c.emit('488b93c805000085d2');c.branch('0f84','native')
    c.emit('4a39d0');c.branch('0f86','clamped')
    c.emit('89d0')
    c.label('clamped')
    c.emit('39c8');c.branch('0f83','native')
    c.emit('8b7e2485ff');c.branch('0f84','native')
    c.emit('8b148785d2');c.branch('0f84','native')
    c.emit('837c244800');c.branch('0f85','keep_sources')
    for offset in (SOURCES,SOURCES+4,ARMS,ARMS+4):
        absolute(c,'c705',stats+offset);c.emit('00000000')
    c.label('keep_sources')
    absolute(c,'8935',stats+SETTINGS)
    absolute(c,'8915',stats+ANCHOR)
    # Replace only the preferred argument; native free-slot selection still runs.
    c.emit('89442428')
    absolute(c,'c705',stats+ENABLED);c.emit('01000000')
    c.label('native')
    c.emit('619d')
    # Duplicate native argument so the original selector RET4 consumes only its
    # own call frame; our RET4 later removes the original caller argument.
    c.emit('ff742404');c.branch('e8',SELECT_NATIVE)
    c.emit('9c60')
    absolute(c,'833d',stats+ENABLED);c.emit('01');c.branch('0f85','done')
    c.emit('8b44241c8b742408') # selected index EAX; caller EBP=settings
    absolute(c,'3b35',stats+SETTINGS);c.branch('0f85','done')
    c.emit('8b4e282b4e24c1e90239c8');c.branch('0f83','done')
    c.emit('8b4e248b148185d2');c.branch('0f84','done')
    c.emit('8b4c244883f901');c.branch('0f87','done')
    absolute(c,'89148d',stats+SOURCES)
    absolute(c,'c7048d',stats+ARMS);c.emit('01000000')
    absolute(c,'ff05',stats+SELECT_COUNT)
    c.label('done')
    c.emit('619dc20400')
    return c.finish()


def matrix_code(base,stats,guids=(GUID,)):
    c=Code(base)
    c.data+=MATRIX_ORIGINAL[:7] # preserve native CMP flags for fallback
    c.emit('9c60')
    story_guard(c,'native',guids)
    absolute(c,'3b05',stats+EPOCH);c.branch('0f85','native')
    absolute(c,'a1',0x28A3228)
    c.emit('85c0');c.branch('0f84','native')
    c.emit('80b8031a000000');c.branch('0f85','native')
    absolute(c,'8b35',stats+ANCHOR)
    c.emit('85f6');c.branch('0f84','native')
    # EBX is the native source entity in ServerVehicleEntity spawn preparation.
    absolute(c,'3b1d',stats+SOURCES);c.branch('0f84','first')
    absolute(c,'3b1d',stats+SOURCES+4);c.branch('0f85','native')
    c.emit('b901000000');c.branch('e9','matched')
    c.label('first');c.emit('31c9')
    c.label('matched')
    absolute(c,'833c8d',stats+ARMS);c.emit('01');c.branch('0f85','native')
    # Both are native entries in the same grid, require identical source type.
    c.emit('8b0685c0');c.branch('0f84','native')
    c.emit('3b03');c.branch('0f85','native')
    c.emit('8b504c81fa00004000');c.branch('0f82','native')
    c.emit('81fa00004002');c.branch('0f83','native')
    # Save the role in a callee-saved register, original output lives at ESP+54.
    c.emit('89cb8d7c245489e581ec2002000083e4f00fae0424')
    c.emit('5789f1ffd2') # native getTransform(anchor, out), RET4, game thread
    c.emit('85db');c.branch('0f84','positioned')
    c.emit('0f104720') # forward vector
    absolute(c,'0f5905',stats+OFFSET)
    c.emit('0f104f300f5cc80f114f30')
    c.label('positioned')
    absolute(c,'c7049d',stats+ARMS);c.emit('00000000')
    absolute(c,'ff049d',stats+MATRIX_COUNTS)
    c.emit('0fae0c2489ec619d')
    c.branch('e9',MATRIX_CONTINUE)
    c.label('native')
    absolute(c,'ff05',stats+FALLBACK)
    c.emit('619d');c.branch('0f84',MATRIX_CONTINUE);c.branch('e9',MATRIX_OVERRIDE)
    return c.finish()
