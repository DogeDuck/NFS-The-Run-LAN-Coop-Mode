"""Bounded passive tracing of Battle timer wins versus next/checkpoint messages.

No win/filter/phase modifications. Original CALLs restored by the existing recorder.
Capture both clients separately; HOST session also includes server BattleStart.
"""
import struct
import story_finish_probe_adapter as adapter
import record_story_finish_flow as flow

CLIENT_SPECS=(('battle_transition_compare',0x990AE7,0x98C640),
              ('battle_transition_win',0x990AF2,0x98C830),
              ('battle_timer_win',0x990BBB,0x98C830))
SERVER_SPECS=(('battle_start',0x13E3084,0x13DB730),)


def build(name,base,stats):
    site,target={n:(s,t) for n,s,t in CLIENT_SPECS+SERVER_SPECS}[name]
    if name=='battle_start':
        # ECX=server mode; native args time/opponent at saved stack+28/+2C.
        payload=bytes.fromhex('8b442418894704c74708ffffffff8b44242889470c8b44242c894710c7471400000000')
    else:
        # ECX is the actual Battle entity, not RaceManager+30's property wrapper.
        payload=bytes.fromhex('8b4c2418894f048b81a80000008947088b819c0000008947108b8198000000894714')
        if name=='battle_transition_compare':
            # Native handler990A50 saves incoming opponent to original entryESP+4.
            # At CALL990AE7 ring saved-stack+48 reaches that slot (two NULL args).
            payload+=bytes.fromhex('8b44244889470c')
        elif name=='battle_transition_win':
            # CALL990AF2 occurs after RET8 from compare: native stack is8 higher.
            payload+=bytes.fromhex('8b44244089470c')
        else:payload+=bytes.fromhex('c7470cffffffff')
    return site,target,adapter.ring_code(base,stats,target,payload)


def decode(name,event):
    row=dict(sequence=event['sequence'],context=hex(event['entity']),caller=hex(event['caller_return']))
    if name=='battle_start':
        row.update(requested_opponent=event['controllable'],time_raw=event['player'])
    else:
        row.update(old_opponent=event['player_id'],incoming_opponent=event['player'],
                   defeated_before=event['controllable'],
                   timer_before=struct.unpack('<f',struct.pack('<I',event['raw_transform_pointer']))[0])
    return row


if __name__=='__main__':
    import argparse
    from pathlib import Path
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true')
    p.add_argument('--session',type=Path,required=True);p.add_argument('--seconds',type=int,default=180)
    args=p.parse_args()
    if args.run:
        flow.CLIENT_SPECS=CLIENT_SPECS;flow.SERVER_SPECS=SERVER_SPECS
        flow.build=build;flow.decode=decode
        flow.run(args.session,args.seconds)
    else:p.print_help()
