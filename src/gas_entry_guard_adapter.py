"""Opt-in dedicated-server gas-station OnEnter gate. No assets, physics or UI writes.

1307952 constructs PlayerEvent OnEnter(FB35AD6C); CALL1307968 dispatches it through
ServerAreaTriggerEntity1306BD0. Native code proves entity+14 is data; data GUID
precedes that object by16 bytes. Restrict to the reflected SimpleAreaTrigger class,
the exact gas-station prefab data GUID, and an active Story challenge controller.
"""
import struct
import uuid
from checkpoint_humans_adapter import Code

SITE,TARGET=0x1307968,0x1306BD0
SIMPLE_TRIGGER_VT=0x25B9BA0
STORY_CONTROLLER=0x28E5C80
STORY_VT=0x25B6D50
GAS_GUID=uuid.UUID('a861bb8f-053a-4b02-b664-bbe3a2efcf27')
CALLS,BLOCKED=0,4


def make_code(base,stats):
    c=Code(base)
    def absolute(op,value):c.emit(op);c.data+=struct.pack('<I',value)
    c.emit('9c60');absolute('ff05',stats+CALLS)
    c.emit('8b44241885c0');c.branch('0f84','native')
    c.emit('8138');c.data+=struct.pack('<I',SIMPLE_TRIGGER_VT)
    c.branch('0f85','native')
    c.emit('8b401485c0');c.branch('0f84','native')
    for offset,word in zip((0xF0,0xF4,0xF8,0xFC),struct.unpack('<4I',GAS_GUID.bytes_le)):
        c.emit('8178'+bytes([offset]).hex());c.data+=struct.pack('<I',word)
        c.branch('0f85','native')
    absolute('a1',STORY_CONTROLLER);c.emit('85c0');c.branch('0f84','native')
    c.emit('8138');c.data+=struct.pack('<I',STORY_VT)
    c.branch('0f85','native')
    c.emit('8b401085c0');c.branch('0f84','native')
    # Preserve scripted on-foot/intro car selection; this gate is for driving.
    c.emit('83782803');c.branch('0f84','native')
    absolute('ff05',stats+BLOCKED)
    c.emit('619dc20400')
    c.label('native');c.emit('619d');c.branch('e9',TARGET)
    return c.finish()


def call_patch(target):
    return b'\xe8'+struct.pack('<i',target-SITE-5)
