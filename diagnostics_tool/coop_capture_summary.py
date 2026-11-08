"""Summarize existing local capture files offline; never opens game processes.

Samples from changes/recent overlap. Deduplicate their native capture clock;
never turn sparse state changes into measured durations or a successful finish.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

LIMIT=32*1024*1024

def read_json(path):
    if path.stat().st_size>LIMIT:raise ValueError('Oversized diagnostic file')
    return json.loads(path.read_text(encoding='utf-8-sig'))

def load_rows(directory):
    if read_json(directory/'manifest.json').get('status')!='stopped':
        raise ValueError('Stop the capture before summarizing')
    rows={}
    for name in ('changes.jsonl','recent.jsonl'):
        path=directory/name
        if not path.exists():continue
        if path.stat().st_size>LIMIT:raise ValueError('Oversized diagnostic file')
        with path.open(encoding='utf-8-sig') as stream:
            for index,line in enumerate(stream):
                if index>=10000:raise ValueError('Too many diagnostic rows')
                row=json.loads(line);stamp=row.get('elapsed_seconds')
                if type(stamp) not in (int,float) or not math.isfinite(stamp) or stamp<0:
                    raise ValueError('Invalid capture clock')
                if not isinstance(row.get('targets'),dict):raise ValueError('Missing capture targets')
                if stamp in rows and rows[stamp]!=row:raise ValueError('Conflicting samples at the same capture time')
                rows[stamp]=row
    return [rows[key] for key in sorted(rows)]

def summarize(rows):
    segments=[];current=None;previous=-1;roles=Counter()
    client_flags=Counter();population_errors=0
    for row in rows:
        stamp=row['elapsed_seconds']
        if type(stamp) not in (int,float) or not math.isfinite(stamp) or stamp<0 or stamp<=previous:
            raise ValueError('Samples must be unique and increasing')
        previous=stamp
        targets=row['targets'];server=targets.get('SERVER',{})
        challenge=server.get('challenge') if server.get('complete') is True else None
        if not challenge:
            population_errors+=int('SERVER' in targets);current=None
        else:
            if current is None or current['challenge']!=challenge:
                current=dict(challenge=challenge,first_observed_seconds=stamp,last_observed_seconds=stamp,
                             complete_samples=0,registered_populations={},native_inputs={})
                segments.append(current)
            current['last_observed_seconds']=stamp;current['complete_samples']+=1
            counts=Counter(r.get('classification','unknown') for r in server.get('racers',[]))
            key=json.dumps(dict(sorted(counts.items())),sort_keys=True)
            current['registered_populations'][key]=current['registered_populations'].get(key,0)+1
            inputs=server.get('population_inputs_raw')
            if inputs is not None:
                key=json.dumps(inputs,sort_keys=True)
                current['native_inputs'][key]=current['native_inputs'].get(key,0)+1
        for role,state in targets.items():
            roles[role]+=1
            if state.get('process_exited'):client_flags[role+':process_exited']+=1
            if role=='SERVER':continue
            vehicle=state.get('vehicle')
            if not vehicle:
                client_flags[role+':vehicle_unavailable']+=1;continue
            for flag in ('autopilot_enabled','animation_controlled','externally_controlled','collisions_disabled'):
                if vehicle.get(flag) is True:client_flags[role+':'+flag]+=1
            health=vehicle.get('health')
            if type(health) in (int,float) and math.isfinite(health) and health<=0:
                client_flags[role+':zero_health']+=1
    for segment in segments:
        for field in ('registered_populations','native_inputs'):
            segment[field]=[dict(value=json.loads(key),observed_samples=count) for key,count in segment[field].items()]
    return dict(schema=1,retained_unique_samples=len(rows),role_samples=dict(roles),
                incomplete_server_samples=population_errors,server_event_segments=segments,
                observed_client_flags=dict(client_flags),
                caution='Retained, potentially sparse samples only. Counts are observations, not durations. '
                'No inferred win, expected AI count, streaming readiness or crash cause. '
                'Repeated GUID segments do not prove an event restart. Scripted police/traffic may be outside the roster.')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=summarize(load_rows(args.directory))
    text=json.dumps(result,ensure_ascii=False,indent=2)
    if args.output:
        with args.output.open('x',encoding='utf-8') as stream:stream.write(text+'\n')
    else:print(text)

if __name__=='__main__':main()
