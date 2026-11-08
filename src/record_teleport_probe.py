"""Explicit bounded LAN-server probe. No game launches, save edits or disk patches.

Default invocation is help. --run is required to open/modify a running server.
Not live-tested. Do not use during solo play.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import time
import uuid
import hashlib
from probe_windows_backend import open_backend
from probe_lifecycle import CallProbe, call_bytes
from teleport_probe_adapter import SITE, TARGET, SERVER_SHA256, REQUIRED_STATS_BYTES, make_code
from teleport_ring_reader import RingTracker

ROOT = Path(__file__).resolve().parent
RESEARCH = Path(r'C:\Users\hatty\Documents\Codex\2026-10-28\es-x20\work\the-run')
SERVER = Path(r'X:\EA Games\Need for Speed The Run\Need for Speed The Run\NFSTR_Server.exe')


def validate_clients(ids):
    from coop_diagnostics import Reader, sample, BUILD
    path = SERVER.with_name('Need For Speed The Run.exe')
    if hashlib.sha256(path.read_bytes()).hexdigest().upper() != BUILD:
        raise ValueError('Client build mismatch')
    for pid in ids:
        reader = Reader(pid, path)
        try:
            state = sample(reader)
            if state.get('singleplayer') != 0 or state.get('connection') != 3:
                raise ValueError('Both live clients must be connected in LAN mode')
        finally:
            reader.close()


def save_manifest(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, indent=2), encoding='utf-8')
    temporary.replace(path)


def mission(api):
    try:
        context = struct.unpack('<I', api.read(0x28E5C80, 4))[0]
        asset = struct.unpack('<I', api.read(context + 0x10, 4))[0]
        return str(uuid.UUID(bytes_le=api.read(asset - 16, 16)))
    except (OSError, ValueError):
        return None


def run(seconds, session_path):
    if not 1 <= seconds <= 300:
        raise ValueError('Use a bounded 1..300 second capture')
    session = json.loads(session_path.read_text(encoding='utf-8-sig'))
    clients = session.get('ClientProcessIds', [])
    pid = session.get('ServerProcessId')
    if len(clients) != 2 or len(set(clients)) != 2 or not isinstance(pid, int) or pid <= 0:
        raise ValueError('Requires two-client LAN session, not solo')
    validate_clients(clients)
    backend = open_backend(pid, SERVER, SERVER_SHA256)
    probe = None
    manifest = {}
    manifest_path = None
    try:
        api = backend.api
        if api.read(SITE, 5) != call_bytes(SITE, TARGET):
            raise ValueError('Server CALL differs; no allocation or patch performed')
        base = api.allocate(8192)
        stats = base + 4096
        code = make_code(base, stats)
        api.write(base, code)
        if api.read(base, len(code)) != code:
            raise OSError('Adapter readback mismatch')
        if api.read(stats, REQUIRED_STATS_BYTES) != bytes(REQUIRED_STATS_BYTES):
            raise ValueError('Stats allocation not zeroed')
        api.protect(base, 4096, 0x20)
        api.flush(base, len(code))
        destination = ROOT / 'outputs' / ('teleport-live-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        destination.mkdir()
        manifest_path = destination / 'recovery.json'
        manifest = dict(status='prepared', pid=pid, process_creation_time=api.creation_time,
                        path=str(SERVER), server_sha256=SERVER_SHA256, base=base, stats=stats,
                        site=SITE, original=call_bytes(SITE, TARGET).hex(),
                        patch=call_bytes(SITE, base).hex(), pages_retained_until_process_exit=True)
        save_manifest(manifest_path, manifest)  # Durable recovery data BEFORE changing CALL.
        probe = CallProbe(backend, SITE, TARGET, base, SERVER_SHA256)
        probe.install()
        manifest['status'] = 'recording'
        save_manifest(manifest_path, manifest)
        tracker = RingTracker()
        start = time.monotonic_ns()
        previous = None
        print(f'Recording server PID {pid} for <= {seconds}s: {destination}', flush=True)
        with (destination / 'events.jsonl').open('x', encoding='utf-8') as output:
            while (time.monotonic_ns() - start) / 1e9 < seconds:
                state = tracker.consume(api.read(stats, REQUIRED_STATS_BYTES), api.read(stats, REQUIRED_STATS_BYTES))
                state['challenge'] = mission(api)
                key = json.dumps(state, sort_keys=True)
                if state['new_events'] or key != previous:
                    output.write(json.dumps(dict(mono_us=(time.monotonic_ns() - start) // 1000, **state)) + '\n')
                    output.flush()
                    previous = key
                time.sleep(0.05)
    finally:
        cleanup_error = None
        if probe and probe.installed and not backend.unsafe:
            try:
                manifest['restore'] = probe.restore()
            except Exception as exc:
                cleanup_error = exc
                manifest['restore_error'] = str(exc)
        if manifest_path:
            manifest['status'] = ('unsafe_suspended' if backend.unsafe else
                                  'recovery_required' if cleanup_error or probe and probe.installed else 'stopped')
            manifest['backend_suspended'] = backend.suspended
            try:
                save_manifest(manifest_path, manifest)
            finally:
                backend.api.close()
        else:
            backend.api.close()
        if cleanup_error:
            raise cleanup_error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--seconds', type=int, default=120)
    parser.add_argument('--session', type=Path, default=RESEARCH / 'local/lan-test-processes.json')
    args = parser.parse_args()
    if not args.run:
        parser.print_help()
        return
    run(args.seconds, args.session)


if __name__ == '__main__':
    main()
