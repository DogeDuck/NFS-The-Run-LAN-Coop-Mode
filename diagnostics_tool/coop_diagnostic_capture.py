"""Read-only two-PC/Radmin capture, bounded rolling evidence and local export.

No process writes, injected hooks, game launches, save changes or network upload.
Explicit `record` is required; default invocation displays help.
"""
import argparse
from collections import deque
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import time
import zipfile
from coop_diagnostics import sample
from coop_population import sample_population,compare_populations
from coop_runtime_session import read_targets,open_reader,default_session_path,CLIENT_BUILDS,SERVER_BUILDS,CLIENT_NAME,SERVER_NAME
from coop_diagnostics import Reader

EXPORT_FILES=('manifest.json','recent.jsonl','changes.jsonl','markers.jsonl','report.json')
V3_CLIENT='2CB4570C34E46CC74CCDED44F8F38338C12A0EDFBB33A74572B72FC6E11AD249'
V3_SERVER='79368D76F6967918C2AE0208757546AA5A0E197B8EE9BFDB631ED809F15AC79E'
RESET_LAYOUT_BUILDS={V3_SERVER,'22F1604CC40643DBCB18154CDA3DA627A63F0B34A4DFDFD7631AD99C9A81B768',
                     '76F2D6DDDBBEAE3C6FDA85644C4D9D65ED7551AB6542AD4D08750EA4F2C04A92',
                     '2BBD8E66B7E5219CF72C7CCCA06404AA2C36712F2B58E4CFEFCAA53C1082066C'}

def dump_references(targets,directory=None):
    """Metadata only, scoped to this PID and session start. Never copies dumps."""
    if directory is None:
        local=os.environ.get('LOCALAPPDATA')
        if not local:return []
        directory=Path(local)/'CrashDumps'
    matches=[]
    for target in targets:
        path=directory/(Path(target['path']).name+'.'+str(target['pid'])+'.dmp')
        try:
            info=path.stat()
            start_ns=(target['start_ticks']-621355968000000000)*100
            if info.st_mtime_ns>=start_ns:
                matches.append(dict(role=target['role'],file=path.name,bytes=info.st_size,modified_ns=info.st_mtime_ns))
        except OSError:pass
    return matches

def now():return datetime.datetime.now().astimezone().isoformat()

def atomic_json(path,value):
    pending=path.with_suffix(path.suffix+'.tmp')
    with pending.open('w',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.flush();os.fsync(stream.fileno())
    pending.replace(path)

def state_signature(row):
    """Suppress ordinary position updates, retain state/counter/racer changes."""
    compact={}
    for role,state in row['targets'].items():
        clone=json.loads(json.dumps(state))
        vehicle=clone.get('vehicle',{})
        vehicle.pop('position',None);vehicle.pop('basis_candidate',None)
        clone.get('spawn_counters',{}).pop('skipped_bindings',None)
        compact[role]=clone
    return json.dumps(compact,sort_keys=True,separators=(',',':'))

class EvidenceBuffer:
    def __init__(self,capacity=240,change_limit=500):
        if not 1<=capacity<=10000 or not 1<=change_limit<=10000:raise ValueError('Invalid buffer bounds')
        self.recent=deque(maxlen=capacity);self.changes=deque(maxlen=change_limit)
        self.total=0;self.total_changes=0;self.previous=None;self.last_elapsed=-1
    def append(self,row):
        elapsed=row['elapsed_seconds']
        if not math.isfinite(elapsed) or elapsed<0 or elapsed<self.last_elapsed:raise ValueError('Nonmonotonic sample')
        self.last_elapsed=elapsed;self.total+=1;self.recent.append(row)
        signature=state_signature(row)
        if signature!=self.previous:
            self.previous=signature;self.total_changes+=1;self.changes.append(row)
    def write(self,directory):
        for name,rows in (('recent.jsonl',self.recent),('changes.jsonl',self.changes)):
            path=directory/name;pending=path.with_suffix('.tmp')
            with pending.open('w',encoding='utf-8') as out:
                for row in rows:out.write(json.dumps(row,ensure_ascii=False)+'\n')
                out.flush();os.fsync(out.fileno())
            pending.replace(path)
    def report(self,reason):
        return dict(stopped_at=now(),stop_reason=reason,total_samples=self.total,
                    retained_samples=len(self.recent),expired_samples=self.total-len(self.recent),
                    total_state_changes=self.total_changes,retained_state_changes=len(self.changes),
                    latest=self.recent[-1] if self.recent else None,
                    caution='Observed process state only. No inferred finish, terrain readiness or expected AI count.')

def sample_target(reader,target,digest):
    if not reader.is_alive():return dict(process_exited=True)
    state=sample_population(reader) if target['role']=='SERVER' else sample(reader)
    try:
        if target['role']=='SERVER' and digest in RESET_LAYOUT_BUILDS:
            values=struct.unpack('<4I',reader.read(0x2B83000,16))
            state['reset_counters']=dict(zip(('acknowledged_without_restore','unused','both_dead_retries','last_retry_tick'),values))
            if digest in ('76F2D6DDDBBEAE3C6FDA85644C4D9D65ED7551AB6542AD4D08750EA4F2C04A92','2BBD8E66B7E5219CF72C7CCCA06404AA2C36712F2B58E4CFEFCAA53C1082066C'):
                state['ai_quota_counters']=dict(zip(('applied','native_fallback','underflow_clamped','last_capacity_requirement'),struct.unpack('<4I',reader.read(0x2B85000,16))))
        elif digest==V3_CLIENT:
            values=struct.unpack('<7I',reader.read(0x2B81000,28))
            # Internal address is intentionally omitted from exported counters.
            state['spawn_counters']=dict(zip(('armed','released','skipped_bindings','teleports','ai_releases','unused'),values[:6]))
            state['select_retry_count']=struct.unpack('<I',reader.read(0x2B81040,4))[0]
    except OSError:state['counter_unavailable']=True
    return state

def record(session_path,destination,seconds=1800,interval=.5,window=120):
    if not 1<=seconds<=1800 or not math.isfinite(interval) or not .1<=interval<=5:
        raise ValueError('Use 1..1800 seconds and interval 0.1..5')
    if not 1<=window<=600:raise ValueError('Use 1..600 seconds of rolling evidence')
    targets=read_targets(session_path)
    evidence=EvidenceBuffer(min(10000,max(1,math.ceil(window/interval))))
    opened=[];reason='error';manifest=None
    try:
        # Validate all identities/builds before creating a capture or sampling.
        for target in targets:
            reader,digest=open_reader(target);opened.append((target,reader,digest))
        destination.mkdir(parents=True,exist_ok=False)
        manifest=dict(schema=1,status='recording',started_at=now(),duration_limit_seconds=seconds,
                      interval_seconds=interval,window_seconds=window,
                      targets=[dict(role=t['role'],pid=t['pid'],start_ticks=t['start_ticks'],sha256=d,filename=Path(t['path']).name) for t,_,d in opened],
                      process_writes=False,network_upload=False,video_recording=False)
        atomic_json(destination/'manifest.json',manifest)
        print(json.dumps(dict(status='recording',directory=str(destination),roles=[t['role'] for t in targets])),flush=True)
        start=time.monotonic();flushed=start
        reason='duration_limit'
        while time.monotonic()-start<seconds:
            row=dict(at=now(),elapsed_seconds=time.monotonic()-start,targets={})
            for target,reader,digest in opened:
                try:state=sample_target(reader,target,digest)
                except OSError as exc:state=dict(unavailable=str(exc))
                row['targets'][target['role']]=state
            evidence.append(row)
            if any(row['targets'][t['role']].get('process_exited') for t in targets if t['role']!='SERVER'):
                reason='local_client_exited';break
            if any(state.get('process_exited') for state in row['targets'].values()):
                reason='local_server_exited';break
            if time.monotonic()-flushed>=5:
                evidence.write(destination);flushed=time.monotonic()
            time.sleep(interval)
    except KeyboardInterrupt:reason='interrupted'
    finally:
        try:
            if manifest is not None:
                evidence.write(destination)
                report=evidence.report(reason)
                report.update(dump_references=dump_references(targets),dump_note='Dump metadata only; a dump can appear after capture stops. Absence is not proof of no crash.')
                atomic_json(destination/'report.json',report)
                manifest.update(status='stopped',stop_reason=reason,stopped_at=now())
                atomic_json(destination/'manifest.json',manifest)
        finally:
            for _,reader,_ in reversed(opened):reader.close()
    return destination

def add_marker(directory,label):
    if not label.strip() or len(label)>160 or '\n' in label or '\r' in label:raise ValueError('Use a single marker line, 1..160 characters')
    if not (directory/'manifest.json').is_file():raise ValueError('Not a diagnostic capture directory')
    with (directory/'markers.jsonl').open('a',encoding='utf-8') as out:
        out.write(json.dumps(dict(at=now(),label=label),ensure_ascii=False)+'\n');out.flush()

def export_bundle(directory,archive):
    manifest=directory/'manifest.json'
    if not manifest.is_file():raise ValueError('Capture manifest missing')
    if json.loads(manifest.read_text(encoding='utf-8')).get('status')!='stopped':raise ValueError('Stop capture before exporting')
    if archive.exists():raise ValueError('Output archive exists')
    selected=[]
    for name in EXPORT_FILES:
        path=directory/name
        if path.is_symlink():raise ValueError('Symlink export refused')
        if path.is_file():
            if path.stat().st_size>32*1024*1024:raise ValueError('Oversized diagnostic file')
            selected.append(path)
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as out:
        for path in selected:out.write(path,path.name)
    return dict(path=str(archive),sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=[p.name for p in selected])

def population_from_document(document):
    if 'racers' in document and 'complete' in document:return document
    if isinstance(document.get('population'),dict):return document['population']
    row=document.get('latest',document)
    if isinstance(row,dict) and isinstance(row.get('targets',{}).get('SERVER'),dict):return row['targets']['SERVER']
    raise ValueError('No server/solo racer population in document')

def snapshot(pid,role,game_directory,output):
    """Explicit read-only Solo/Host/Guest/Server reference; no launcher required."""
    if pid<=0:raise ValueError('Use a positive PID')
    executable=game_directory/(SERVER_NAME if role=='SERVER' else CLIENT_NAME)
    digest=hashlib.sha256(executable.read_bytes()).hexdigest().upper()
    if digest not in (SERVER_BUILDS if role=='SERVER' else CLIENT_BUILDS):raise ValueError('Unsupported snapshot build')
    reader=Reader(pid,executable)
    try:
        data=dict(at=now(),role=role,sha256=digest,process_creation_time=reader.creation_time(),
                  population=sample_population(reader))
        if role!='SERVER':data['client']=sample(reader)
        atomic_json(output,data)
        return data
    finally:reader.close()

def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command')
    capture=commands.add_parser('record');capture.add_argument('--session',type=Path)
    capture.add_argument('--output',type=Path,required=True);capture.add_argument('--seconds',type=int,default=1800)
    capture.add_argument('--interval',type=float,default=.5);capture.add_argument('--window',type=int,default=120)
    marker=commands.add_parser('mark');marker.add_argument('directory',type=Path);marker.add_argument('label')
    bundle=commands.add_parser('export');bundle.add_argument('directory',type=Path);bundle.add_argument('archive',type=Path)
    compare=commands.add_parser('compare');compare.add_argument('reference',type=Path);compare.add_argument('candidate',type=Path)
    single=commands.add_parser('snapshot');single.add_argument('--pid',type=int,required=True)
    single.add_argument('--role',choices=('SOLO','HOST','GAST','SERVER'),required=True)
    single.add_argument('--game-directory',type=Path,required=True);single.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='record':record(args.session or default_session_path(),args.output,args.seconds,args.interval,args.window)
    elif args.command=='mark':add_marker(args.directory,args.label)
    elif args.command=='export':print(json.dumps(export_bundle(args.directory,args.archive),indent=2))
    elif args.command=='compare':print(json.dumps(compare_populations(population_from_document(json.loads(args.reference.read_text(encoding='utf-8'))),population_from_document(json.loads(args.candidate.read_text(encoding='utf-8')))),indent=2))
    elif args.command=='snapshot':print(json.dumps(snapshot(args.pid,args.role,args.game_directory,args.output),indent=2))
    else:parser.print_help()

if __name__=='__main__':main()
