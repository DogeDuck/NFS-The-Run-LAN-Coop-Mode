"""Passive, verified CALL probes for Story predicate/result and server race states.

No success overrides. Predicate wrapper preserves its return registers/flags,
calls the native zero-argument predicate once, and keeps callee stack alignment.
"""
import struct
from teleport_probe_adapter import make_code as ring_code

CLIENT_SPECS=(('story_predicate',0x99371E,0x991150),('accepted_win',0x99372B,0x98CD60),('mode_type',0x9911BA,0x8D2140))
SERVER_SPECS=(('finish_constructor',0x13E128A,0x2264320),('racer_state_request',0x13CE2C7,0x226FB00),('finish_send',0x13E12B2,0x4F1D80))

def make_entry_code(base,stats,target,name):
    if name=='racer_state_request':
        # Original ESI in13CE280 is the native RacerInfo. No setter is called here.
        payload=bytes.fromhex('8b4c2404894f048b41108947088b411889470c8b411c8947108b4114894714')
    elif name=='accepted_win':
        payload=bytes.fromhex('8b4c2418894f04c74708ffffffff8b44242889470cc7471000000000c7471400000000')
    elif name=='finish_constructor':
        # The message is not initialized yet. Capture pointers, do not dereference.
        payload=bytes.fromhex('8b4c2418894f04c74708ffffffffc7470c000000008b4424108947108b442404894714')
    elif name=='finish_send':
        # Native initialized message pointer is the sole stack argument.
        payload=bytes.fromhex('8b4c2428894f048b412c8947088b410889470cc7471000000000c7471400000000')
    else:raise ValueError('Unknown finish probe')
    return ring_code(base,stats,target,payload)

def make_predicate_code(base,stats,target,raw_result=False):
    # Reserve12 + CALL return4 => original callee runs16 bytes lower, same alignment.
    # Saved ECX at oldESP-4 remains above the native callee's stack, not in a register
    # that the predicate may clobber. The original predicate has no stack arguments.
    prefix=bytes.fromhex('8d6424f4894c2408e8')+struct.pack('<i',target-(base+13))
    payload=(bytes.fromhex('8b4c242c894f04c74708ffffffff8b44241c89470cc7471000000000c7471400000000')
             if raw_result else bytes.fromhex('8b4c242c894f04c74708ffffffff0fb644241c89470c8b414c894710c7471400000000'))
    temporary=ring_code(base+13,stats,0x400000,payload,caller_offset=48)
    tail=base+13+len(temporary)
    body=ring_code(base+13,stats,tail,payload,caller_offset=48)
    # LEA leaves native EFLAGS intact after the ring's POPFD.
    return prefix+body+bytes.fromhex('8d64240cc3')

def build(name,base,stats):
    specs={n:(site,target) for n,site,target in CLIENT_SPECS+SERVER_SPECS}
    site,target=specs[name]
    if name in ('story_predicate','mode_type'):code=make_predicate_code(base,stats,target,raw_result=name=='mode_type')
    else:code=make_entry_code(base,stats,target,name)
    return site,target,code

def decode(name,event):
    result=dict(sequence=event['sequence'],context=hex(event['entity']),caller=hex(event['caller_return']))
    if name=='story_predicate':result.update(native_success=bool(event['player']&255),existing_result_raw=event['controllable'])
    elif name=='accepted_win':result['requested_win_raw']=event['player']
    elif name=='racer_state_request':result.update(racer_id=event['player_id'],state=event['player'],desired=event['controllable'],driver_kind_raw=event['raw_transform_pointer'])
    elif name=='finish_constructor':result.update(owner_raw=hex(event['controllable']),participant_raw=hex(event['raw_transform_pointer']),caution='Constructor entry only; not proof of successful finish or delivery')
    elif name=='mode_type':result['native_mode_type_raw']=event['player']
    elif name=='finish_send':result.update(player_id=event['player_id'],message_id=hex(event['player']),caution='Local message bus send; not proof of Story victory or remote receipt')
    else:raise ValueError('Unknown probe')
    return result
