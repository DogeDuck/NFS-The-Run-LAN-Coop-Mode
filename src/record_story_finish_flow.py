"""Bounded passive Story/MP finish trace for the current local launcher session.

Default is help. --run installs temporary native CALL hooks, never fake wins or
race-state requests. Works with a remote guest; no two-local-client assumption.
"""
import argparse
import datetime
import json
from pathlib import Path
import time
import uuid
from coop_diagnostics import ROOT,sample
from coop_population import sample_population
from coop_runtime_session import read_targets,open_reader,default_session_path,DOTNET_FILETIME_EPOCH
from probe_windows_backend import open_backend
from probe_lifecycle import CallProbe
from record_teleport_probe import save_manifest
from story_finish_probe_adapter import CLIENT_SPECS,SERVER_SPECS,build,decode
from teleport_probe_adapter import REQUIRED_STATS_BYTES
from teleport_ring_reader import RingTracker

def run(session,seconds=180):
    if not 1<=seconds<=300:raise ValueError('Use a bounded 1..300 second capture')
    targets=read_targets(session);backends=[];readers=[];hooks=[];manifest=dict(status='preparing',hooks=[])
    dest=ROOT/'outputs'/('story-finish-flow-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:12])
    try:
        for target in targets:
            reader,digest=open_reader(target);readers.append((target,reader))
            if target['role']!='SERVER':
                state=sample(reader)
                if state.get('singleplayer')!=0 or state.get('connection')!=3:raise ValueError('Client is not connected in LAN mode')
            backend=open_backend(target['pid'],Path(target['path']),digest);backends.append(backend)
            if backend.api.creation_time+DOTNET_FILETIME_EPOCH!=target['start_ticks']:raise ValueError('Process identity changed')
            specs=SERVER_SPECS if target['role']=='SERVER' else CLIENT_SPECS
            if len(specs)>8:raise ValueError('Code page capacity exceeded')
            base=backend.api.allocate(4096+len(specs)*2048)
            for index,(name,site,native) in enumerate(specs):
                address=base+index*512;stats=base+4096+index*2048
                _,_,code=build(name,address,stats)
                if len(code)>512:raise ValueError('Probe slot overflow')
                backend.api.write(address,code)
                if backend.read(address,len(code))!=code:raise OSError('Readback mismatch')
                probe=CallProbe(backend,site,native,address,digest)
                if backend.read(site,5)!=probe.original_bytes():raise ValueError('Native callsite mismatch')
                item=dict(role=target['role'],pid=target['pid'],creation_time=backend.api.creation_time,name=name,site=site,stats=stats,original=probe.original_bytes().hex(),patch=probe.adapter_bytes().hex(),state='prepared')
                hooks.append((backend,probe,item,RingTracker()));manifest['hooks'].append(item)
            backend.api.protect(base,4096,0x20);backend.api.flush(base,4096)
        dest.mkdir();save_manifest(dest/'recovery.json',manifest)
        for _,probe,item,_ in hooks:
            probe.install();item['state']='installed';save_manifest(dest/'recovery.json',manifest)
        manifest['status']='recording';save_manifest(dest/'recovery.json',manifest)
        print(json.dumps(dict(status='recording',seconds=seconds,directory=str(dest))),flush=True)
        end=time.monotonic()+seconds
        with (dest/'events.jsonl').open('x',encoding='utf-8') as out:
            while time.monotonic()<end:
                if any(not reader.is_alive() for _,reader in readers):break
                for backend,_,item,tracker in hooks:
                    result=tracker.consume(backend.read(item['stats'],REQUIRED_STATS_BYTES),backend.read(item['stats'],REQUIRED_STATS_BYTES))
                    for event in result['new_events']:
                        state={target['role']:(sample_population(reader) if target['role']=='SERVER' else sample(reader)) for target,reader in readers}
                        out.write(json.dumps(dict(polled_at=datetime.datetime.now().astimezone().isoformat(),role=item['role'],probe=item['name'],event=decode(item['name'],event),observed_state=state,expired_events=result['unobserved_expired'],timing='Separate rings; poll order is not native cross-probe execution order'))+'\n');out.flush()
                time.sleep(.05)
    finally:
        errors=[]
        for backend,probe,item,_ in reversed(hooks):
            try:
                owner=next(reader for target,reader in readers if target['pid']==item['pid'])
                if probe.installed and not owner.is_alive():
                    probe.installed=False;item['state']='process_exited'
                elif probe.installed and not backend.unsafe:item['state']=probe.restore()
            except Exception as exc:item['state']='restore_failed';errors.append(str(exc))
        manifest['status']='stopped' if not errors and not any(b.unsafe for b in backends) and not any(p.installed for _,p,_,_ in hooks) else 'recovery_required'
        manifest['errors']=errors
        try:
            if dest.exists():save_manifest(dest/'recovery.json',manifest)
        finally:
            for backend in reversed(backends):backend.api.close()
            for _,reader in reversed(readers):reader.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true')
    parser.add_argument('--session',type=Path);parser.add_argument('--seconds',type=int,default=180);args=parser.parse_args()
    if args.run:run(args.session or default_session_path(),args.seconds)
    else:parser.print_help()
