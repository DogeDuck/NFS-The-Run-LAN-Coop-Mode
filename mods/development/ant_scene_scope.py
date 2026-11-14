"""Experimental ANT camera event wrapper, no process access.

Ghidra DF9F7069 990920: event DEAA09DC sets +25C=1, 72F6CC1D clears it.
5D121EF4 is neither. Wrapper observes native state transitions, never fabricates
camera/QTE success. Counter is input for a future leased AI adapter, not installed.
"""
import struct
from cutscene_ai_adapter import Asm,EAX,ECX,EDX,EBX

NATIVE=0x990920
VT=0x2488B48
START=(-0x2155f624)&0xffffffff
STOP=0x72F6CC1D
COUNT,STARTS,STOPS=0x00,0x04,0x08
TABLE,MAX_CAMERAS=0x20,64
SIZE=0x140
# Spare fields after the bounded pointer table. GetTickCount is already imported
# by this exact client. A frame count is unsuitable on 60..240+ Hz displays.
LAST_TICK,AGE_MS,CLOCK_SET=0x120,0x124,0x128
GETTICK_IAT=0x2A8B8E4
LOST_STOP_MS=120000

def make_code(base,data):
    c=Asm(base,data)
    # Observe native active state on every event, including already-active adoption.
    # Only pointer values are cached, never dereferenced later by the frame hook.
    # Locals: this, reserved. Original message argument is [esp+30h].
    c.emit('9c60fc83ec08');c.emit('890c24')
    c.emit('ff742430');c.branch('e8',NATIVE)
    c.emit('8b0c24')
    c.cmpm(ECX,0,VT);c.branch('0f85','done')
    c.cmpi(0x1C,0);c.branch('0f85','done')  # overflow fails closed until context reset
    c.emit('0fb6815c020000')
    c.test(EAX);c.branch('0f84','off')
    c.seti(0x14,0)
    c.xor(EBX);c.movi(EDX,0xffffffff)
    c.label('scan')
    c.emit('83fb40');c.branch('0f83','add')
    c.idx('8b',EAX,TABLE);c.cmpr(EAX,ECX);c.branch('0f84','done')
    c.test(EAX);c.branch('0f85','next')
    c.emit('83faff');c.branch('0f85','next');c.mov(EDX,EBX)
    c.label('next');c.emit('43');c.branch('e9','scan')
    c.label('add');c.emit('83faff');c.branch('0f84','overflow')
    c.emit('890c95');c.imm(data+TABLE)
    c.inc(COUNT);c.inc(STARTS);c.branch('e9','done')
    c.label('off');c.xor(EBX)
    c.label('remove_scan');c.emit('83fb40');c.branch('0f83','done')
    c.idx('8b',EAX,TABLE);c.cmpr(EAX,ECX);c.branch('0f84','remove')
    c.emit('43');c.branch('e9','remove_scan')
    c.label('remove');c.emit('c7049d');c.imm(data+TABLE);c.imm(0)
    c.cmpi(COUNT,0);c.branch('0f84','done')
    c.emit('ff0d');c.imm(data+COUNT);c.inc(STOPS);c.branch('e9','done')
    c.label('overflow');c.seti(COUNT,0);c.seti(0x1C,1)
    c.label('done');c.emit('83c408619dc20400')
    return c.finish()

def initial():return bytes(SIZE)

def make_combined(base,data,ghost=False):
    """Offline candidate: resets context on level/entity change, elapsed-time failsafe.
    Still needs leased live controller; same-level Retry is not a verified scene edge.
    ghost (Claude 14.11.): optional native vehicle ghost, default False keeps the bytes unchanged.
    """
    import cutscene_ai_adapter as original
    ant_data=data+original.DATA_SIZE
    code,entries=original.make_code(base,data,ant_count=ant_data+COUNT,ghost=ghost)
    camera_entry=base+len(code)
    code+=make_code(camera_entry,ant_data)
    entries['camera']=camera_entry
    return code,entries,original.data_init()+initial()
