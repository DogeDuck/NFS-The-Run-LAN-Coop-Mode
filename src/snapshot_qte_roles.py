"""Read-only live QTE role/controllable snapshot; never changes a scene."""
import datetime
import json
import struct
from pathlib import Path
from coop_runtime_session import read_targets, open_reader
from coop_diagnostics import sample
from coop_population import sample_population

ROOT = Path(__file__).resolve().parent
LOCAL_ACTOR_CLIENT='1E5CAB30563EF2DA390D70D59EFDEB95B3796C7560FB19306206B4CE78025339'
MILESTONE_SERVER='F2E5A72CCB5D781833E58395715C08E1B7A400C5700E0177B5861AD66F688173'
CANDIDATE_STATS=0x2B93000


def candidate_snapshot(reader,digest):
    """Read only the two exact night candidates; never follow cached pointers."""
    if digest==LOCAL_ACTOR_CLIENT:
        native,local=struct.unpack('<2I',reader.read(CANDIDATE_STATS,8))
        return dict(kind='local_actor',native_getters=native,local_selections=local)
    if digest!=MILESTONE_SERVER:return None
    from qte_host_milestones import STATS_SIZE,CACHE,SLOTS,STRIDE
    raw=reader.read(CANDIDATE_STATS,STATS_SIZE)
    if reader.read(CANDIDATE_STATS,STATS_SIZE)!=raw:
        return dict(kind='host_milestones',stable=False)
    words=struct.unpack('<%dI'%(len(raw)//4),raw)
    if not 0<=words[10]<=4:raise ValueError('Candidate roster count outside 0..4')
    names=('calls','native_calls','guest_ignored','fired','duplicates','fallback','retries','rearms')
    entries=[]
    for i in range(SLOTS):
        entity,data,bus,mask,group=struct.unpack_from('<5I',raw,CACHE+i*STRIDE)
        if entity:entries.append(dict(entity=hex(entity),source_group=group,
            arrived_mask=mask&0xF,closed=bool(mask&0x80000000)))
    return dict(kind='host_milestones',stable=True,counters=dict(zip(names,words[:8])),
                human_count=words[10],verified_host=hex(words[11]),entries=entries)


def name_of(reader, player):
    pointer = reader.u32(player + 0x10)
    return reader.read(pointer, 64).split(b'\0')[0].decode('utf-8', 'replace') if pointer else None


def capture(directory,host_candidate=False):
    targets = {t['role']: t for name in ('host-session.json', 'guest-session.json') for t in read_targets(directory / name)}
    result = dict(time=datetime.datetime.now().astimezone().isoformat(), read_only=True, targets=[])
    for role, target in targets.items():
        row = dict(role=role, pid=target['pid'])
        result['targets'].append(row)
        allowed={MILESTONE_SERVER} if role=='SERVER' else {LOCAL_ACTOR_CLIENT}
        reader, digest = open_reader(target,extra_builds=allowed if host_candidate else frozenset())
        try:
            if host_candidate:row['candidate']=candidate_snapshot(reader,digest)
            if role == 'SERVER':
                row['state'] = sample_population(reader)
                manager = reader.u32(0x28A3220)
                start, end = struct.unpack('<II', reader.read(manager + 0x78, 8))
                if end < start or (end - start) % 4 or end - start > 256:
                    raise ValueError('Unstable server player vector')
                row['humans'] = []
                for pointer, in struct.iter_unpack('<I', reader.read(start, end - start)):
                    if pointer and reader.read(pointer + 0x260, 1) == b'\0':
                        row['humans'].append(dict(pointer=hex(pointer), name=name_of(reader, pointer),
                                                  id=reader.u32(pointer + 0x2E4)))
            else:
                row['state'] = sample(reader)
                player = reader.u32(reader.u32(0x2888F78) + 0xBC)
                entity = reader.u32(player + 0x318)
                row.update(local_name=name_of(reader, player), local_player=hex(player),
                           controllable=hex(entity), controllable_vtable=hex(reader.u32(entity)) if entity else None)
        except (OSError, ValueError) as exc:
            row['unavailable'] = str(exc)
        finally:
            reader.close()
    output = ROOT / 'outputs' / ('qte-role-state-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json')
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return output


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--host-candidate',action='store_true',help='Explicitly allow the two exact local-actor/host-milestone hashes, read only')
    args=parser.parse_args()
    print(capture(args.directory,args.host_candidate))
