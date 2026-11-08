"""Read-only registered racer inventory. Not a census of every scripted police car."""
import struct
import uuid

CONTEXT=0x28E5C80
MANAGER=0x28E5C90
PLAYERS=0x28A3220
RACER_VTABLE=0x25B6DF8
CONTEXT_VTABLE=0x25B6D50
STATE_NAMES={6:'Racing',7:'PostRace'}

def read_racer(reader,ptr):
    if reader.u32(ptr)!=RACER_VTABLE:raise ValueError('Unexpected racer vtable')
    racer_id,kind,state,desired=struct.unpack('<4I',reader.read(ptr+0x10,16))
    row=dict(id=racer_id,driver_kind_raw=kind,state=state,desired_state=desired,
             state_name=STATE_NAMES.get(state,'unknown'),classification='driver_kind_1' if kind==1 else 'unknown')
    try:
        owner=reader.u32(PLAYERS)
        table=reader.u32(owner+0xA4) if owner and racer_id<=63 and kind==0 else 0
        player=reader.u32(table+4*racer_id) if table else 0
        if player and reader.u32(player+0x2E4)==racer_id:
            flag=reader.read(player+0x260,1)[0]
            if flag in (0,1):row['classification']='human' if flag==0 else 'bot'
    except OSError:pass
    return row

def read_roster(reader,manager,offset):
    bounds=reader.read(manager+offset,8)
    begin,end=struct.unpack('<II',bounds)
    if end<begin or end-begin>64*4 or (end-begin)%4:raise ValueError('Invalid racer array bounds')
    if begin==0 and end!=0:raise ValueError('Null racer array')
    pointers=reader.read(begin,end-begin) if end>begin else b''
    seen=set();rows=[]
    for (ptr,) in struct.iter_unpack('<I',pointers):
        if not ptr or ptr in seen:raise ValueError('Null or duplicate racer pointer')
        seen.add(ptr);rows.append(read_racer(reader,ptr))
    if reader.read(manager+offset,8)!=bounds:raise ValueError('Racer list changed during sampling')
    if pointers and reader.read(begin,len(pointers))!=pointers:raise ValueError('Racer membership changed during sampling')
    return rows

def sample_population(reader):
    result=dict(complete=False,racers=[],caution='Registered racers only; scripted police/traffic may use separate entities. No expected AI count inferred.')
    try:
        context=reader.u32(CONTEXT)
        if not context or reader.u32(context)!=CONTEXT_VTABLE:raise ValueError('No verified story context')
        asset=reader.u32(context+0x10)
        if not asset:raise ValueError('No current story asset')
        result['challenge']=str(uuid.UUID(bytes_le=reader.read(asset-16,16)))
        manager=reader.u32(MANAGER)
        if not manager:raise ValueError('No racer manager')
        try:
            world=reader.u32(0x28A3228)
            result['population_inputs_raw']=dict(
                world_byte_1a03=reader.read(world+0x1A03,1)[0] if world else None,
                fill_byte_5c3=reader.read(manager+0x5C3,1)[0],
                total_5c8=reader.u32(manager+0x5C8),other_limit_5cc=reader.u32(manager+0x5CC),
                active_entity_present=bool(reader.u32(manager+0x5AC)))
        except OSError:result['population_inputs_unavailable']=True
        result['racers']=read_roster(reader,manager,0x56C)
        # Separate native list populated by13D66E0. Do not merge it into active
        # race counts or assume every late/secondary participant is already racing.
        try:
            result['secondary_racers']=read_roster(reader,manager,0x57C)
            result['secondary_complete']=True
        except (OSError,ValueError,struct.error) as exc:
            result['secondary_complete']=False;result['secondary_unavailable']=str(exc)
        if reader.u32(CONTEXT)!=context or reader.u32(context+0x10)!=asset:raise ValueError('Challenge changed during sampling')
        if reader.u32(MANAGER)!=manager:raise ValueError('Racer manager changed during sampling')
        result['counts']={kind:sum(r['classification']==kind for r in result['racers']) for kind in ('human','bot','driver_kind_1','unknown')}
        result['driver_kind_counts']={str(kind):sum(r['driver_kind_raw']==kind for r in result['racers']) for kind in sorted({r['driver_kind_raw'] for r in result['racers']})}
        result['complete']=True
    except (OSError,ValueError,struct.error) as exc:
        result['unavailable']=str(exc)
    return result

def compare_populations(reference,candidate):
    """Report a measured difference, never declare all AI missing from partial reads."""
    if not reference.get('complete') or not candidate.get('complete'):
        return dict(comparable=False,reason='Incomplete racer snapshot')
    if reference.get('challenge')!=candidate.get('challenge'):
        return dict(comparable=False,reason='Different story events')
    if any(r.get('classification')=='unknown' for s in (reference,candidate) for r in s['racers']):
        return dict(comparable=False,reason='Unresolved participant classification')
    def opponents(snapshot):return sum(r['classification'] in ('bot','driver_kind_1') for r in snapshot['racers'])
    return dict(comparable=True,reference_registered_non_player_racers=opponents(reference),candidate_registered_non_player_racers=opponents(candidate),
                delta=opponents(candidate)-opponents(reference),caution='DriverKind1 follows a separate native branch; not the human sharing its ID. Different event phases affect population; scripted police/traffic not covered.')
