"""Explicit event-driven bridge exception capture. No game launches or patches.

--run attaches a Windows debugger for1..300s. Debug events briefly stop the
client. Native exceptions are passed to the game's handlers, not suppressed.
Only the initial debugger-attach breakpoints are acknowledged. Without --run
this displays help; --replay uses saved JSON offline and opens no processes.
"""
import argparse
from collections import Counter
import datetime
import json
from pathlib import Path
import time
import hashlib
import zipfile
from bridge_crash_analysis import CONTRACT,verify_client
from bridge_exception_snapshot import build_snapshot,replay
from coop_diagnostics import ROOT,sample
from coop_diagnostic_capture import atomic_json
from coop_runtime_session import read_targets,open_reader,default_session_path
from exception_debug_backend import WindowsExceptionDebugger,ACCESS_VIOLATION

def export_bundle(directory,archive):
    manifest=directory/'manifest.json'
    if manifest.is_symlink() or not manifest.is_file() or manifest.stat().st_size>2*1024*1024:
        raise ValueError('Valid local exception manifest required')
    if json.loads(manifest.read_text(encoding='utf-8-sig')).get('status')!='stopped':
        raise ValueError('Stop/detach capture before exporting')
    if archive.exists():raise ValueError('Output archive exists')
    selected=[]
    for name in ('manifest.json',)+tuple('exception-'+str(index)+'.json' for index in range(1,5)):
        path=directory/name
        if path.is_symlink():raise ValueError('Symlink export refused')
        if path.is_file():
            if path.stat().st_size>2*1024*1024:raise ValueError('Oversized exception snapshot')
            selected.append(path)
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as out:
        for path in selected:out.write(path,path.name)
    return dict(archive=str(archive),sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=[path.name for path in selected])

def run(session,seconds=180,destination=None,all_faults=False):
    if type(seconds) is not int or not 1<=seconds<=300:raise ValueError('Use 1..300 seconds')
    targets=[target for target in read_targets(session) if target['role']!='SERVER']
    if len(targets)!=1:raise ValueError('Exactly one current local client session required')
    target=targets[0];verify_client(Path(target['path']).read_bytes())
    reader=None;debugger=None;manifest=None;captures=0;events=Counter();reason='error'
    destination=destination or ROOT/'outputs'/('bridge-exception-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    try:
        reader,digest=open_reader(target)
        state=sample(reader)
        if state.get('singleplayer')!=0 or state.get('connection')!=3:raise ValueError('Client is not connected in LAN')
        for address,expected in CONTRACT.items():
            if reader.read(address,len(expected))!=expected:raise ValueError('Live native contract differs')
        destination.mkdir(parents=True,exist_ok=False)
        manifest=dict(schema=1,status='prepared',target=target,client_sha256=digest,seconds=seconds,
                      writes_game_memory=False,sets_thread_context=False,starts_game=False,
                      debug_attach_changes_timing=True,network_upload=False,all_faults=all_faults)
        atomic_json(destination/'manifest.json',manifest)
        debugger=WindowsExceptionDebugger(target['pid']);debugger.attach()
        # Re-open by the session's exact creation identity while attached. This
        # catches PID/path changes before any exception data is interpreted.
        checked,_=open_reader(target);checked.close()
        manifest['status']='observing';atomic_json(destination/'manifest.json',manifest)
        print(json.dumps(dict(status='observing',directory=str(destination),seconds=seconds)),flush=True)
        end=time.monotonic()+seconds;reason='duration_limit'
        while debugger.attached and time.monotonic()<end:
            event=debugger.wait(100)
            if event is None:continue
            try:
                events[str(event['kind'])]+=1
                generic_fault = all_faults and event.get('kind')==1 and (event.get('code') in
                    (ACCESS_VIOLATION,0xC0000374,0xC0000409,0xC000001D) or event.get('first_chance') is False)
                if event.get('code')==ACCESS_VIOLATION or generic_fault:
                    events['access_violations']+=1
                    details=manifest.setdefault('access_violation_events',[])
                    if len(details)<16:
                        details.append({key:event.get(key) for key in ('address','first_chance','parameters','tid')})
                    if captures<4:
                        registers=debugger.context(event['tid'])
                        if all_faults:
                            from game_fault_snapshot import build_fault_snapshot
                            document=build_fault_snapshot(reader,registers,event)
                        else:document=build_snapshot(reader,registers,event)
                        if not all_faults and not document.get('lookup',{}).get('applicable') and event['address']!=0x4CD08B:
                            continue
                        document.update(at=datetime.datetime.now().astimezone().isoformat(),target=target,client_sha256=digest)
                        captures+=1;atomic_json(destination/('exception-'+str(captures)+'.json'),document)
                        # Keep observing briefly so first/second chance and exit
                        # are distinguishable; first chance alone is not fatal.
                        end=min(end,time.monotonic()+3);reason='native_fault_observed' if all_faults else 'bridge_exception_observed'
                if event['kind']==5:reason='process_exited'
            finally:debugger.continue_event()
    except KeyboardInterrupt:reason='interrupted'
    except BaseException as exc:
        if manifest is not None:manifest['capture_error']=type(exc).__name__+': '+str(exc)
        raise
    finally:
        detach_error=None
        try:
            if debugger:debugger.detach()
        except Exception as exc:detach_error=type(exc).__name__+': '+str(exc)
        finally:
            try:
                if manifest is not None:
                    manifest.update(status='detach_failed' if detach_error else 'stopped',stop_reason=reason,
                                    exception_snapshots=captures,event_counts=dict(events),detach_error=detach_error)
                    atomic_json(destination/'manifest.json',manifest)
            finally:
                if reader:reader.close()
        if detach_error:raise RuntimeError('Debugger detach requires attention: '+detach_error)
    return destination

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    choice=parser.add_mutually_exclusive_group();choice.add_argument('--run',action='store_true');choice.add_argument('--replay',type=Path);choice.add_argument('--export',type=Path)
    parser.add_argument('--session',type=Path);parser.add_argument('--seconds',type=int,default=180)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--all-faults',action='store_true',help='Capture non-bridge AV/heap/fail-fast/illegal-instruction and second-chance faults')
    args=parser.parse_args()
    if args.replay:
        if args.replay.stat().st_size>2*1024*1024:raise ValueError('Oversized snapshot JSON')
        print(json.dumps(replay(json.loads(args.replay.read_text(encoding='utf-8-sig'))),indent=2))
    elif args.export:
        if not args.output:parser.error('--export requires --output archive.zip')
        print(json.dumps(export_bundle(args.export,args.output),indent=2))
    elif args.run:run(args.session or default_session_path(),args.seconds,args.output,args.all_faults)
    else:parser.print_help()

if __name__=='__main__':main()
