"""Read-only, bounded LAN recorder and offline scenario checks. No process writes."""
from pathlib import Path
import argparse
import ctypes as c
from ctypes import wintypes as w
import datetime
import hashlib
import json
import math
import struct
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parent
UPSTREAM = ROOT / 'external/coop-anything/tools/flight'
BUILD = 'C9D48E500EF82EFC642EDF2DB848A9072E56FBC114E283173D6E7E58BAC634A6'
RESEARCH = Path(r'C:\Users\hatty\Documents\Codex\2026-10-28\es-x20\work\the-run')
GAME = Path(r'X:\EA Games\Need for Speed The Run\Need for Speed The Run')


class Reader:
    def __init__(self, pid, expected):
        self.k = c.WinDLL('kernel32', use_last_error=True)
        self.k.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        self.k.OpenProcess.restype = w.HANDLE
        self.k.ReadProcessMemory.argtypes = [w.HANDLE, c.c_void_p, c.c_void_p, c.c_size_t, c.POINTER(c.c_size_t)]
        self.k.QueryFullProcessImageNameW.argtypes = [w.HANDLE, w.DWORD, w.LPWSTR, c.POINTER(w.DWORD)]
        self.k.CloseHandle.argtypes = [w.HANDLE]
        self.h = self.k.OpenProcess(0x410, False, pid)  # QUERY_INFORMATION | VM_READ only
        if not self.h:
            raise c.WinError(c.get_last_error())
        try:
            name = c.create_unicode_buffer(32768)
            length = w.DWORD(len(name))
            if not self.k.QueryFullProcessImageNameW(self.h, 0, name, c.byref(length)):
                raise c.WinError(c.get_last_error())
            if name.value.casefold() != str(expected).casefold():
                raise ValueError('PID/path mismatch')
        except BaseException:
            self.close()
            raise

    def read(self, address, size):
        b = c.create_string_buffer(size)
        n = c.c_size_t()
        if not self.k.ReadProcessMemory(self.h, address, b, size, c.byref(n)) or n.value != size:
            raise OSError('Memory unavailable during transition or process exit')
        return b.raw

    def u32(self, address):
        return struct.unpack('<I', self.read(address, 4))[0]

    def creation_time(self):
        """FILETIME ticks from the opened handle, not a possibly reused PID."""
        self.k.GetProcessTimes.argtypes = [w.HANDLE] + [c.POINTER(w.FILETIME)] * 4
        self.k.GetProcessTimes.restype = w.BOOL
        created, exited, kernel, user = (w.FILETIME() for _ in range(4))
        if not self.k.GetProcessTimes(self.h, c.byref(created), c.byref(exited), c.byref(kernel), c.byref(user)):
            raise c.WinError(c.get_last_error())
        return created.dwLowDateTime | (created.dwHighDateTime << 32)

    def is_alive(self):
        self.k.GetExitCodeProcess.argtypes = [w.HANDLE, c.POINTER(w.DWORD)]
        self.k.GetExitCodeProcess.restype = w.BOOL
        code = w.DWORD()
        if not self.k.GetExitCodeProcess(self.h, c.byref(code)):
            raise c.WinError(c.get_last_error())
        return code.value == 259

    def close(self):
        if self.h:
            self.k.CloseHandle(self.h)
            self.h = None


def sample(reader):
    result = {}
    try:
        online = reader.u32(0x2888F7C)
        result['singleplayer'] = reader.read(online + 8, 1)[0]
        result['connection'] = reader.u32(online + 0xA4)
        controller = reader.u32(0x28824E8)
        asset = reader.u32(controller + 0x10)
        result['challenge'] = str(uuid.UUID(bytes_le=reader.read(asset - 16, 16)))
        result['level'] = reader.read(0x289BDC8, 256).split(b'\0')[0].decode('ascii', 'replace')
    except OSError as exc:
        result['state_error'] = str(exc)
    try:
        player = reader.u32(reader.u32(0x2888F78) + 0xBC)
        result['player_id'] = reader.u32(player + 0x334)
        entity = reader.u32(player + 0x318)
        if reader.u32(entity) != 0x254D220:
            raise OSError('No verified local ClientVehicleEntity')
        vehicle = reader.u32(entity + 0xE4)
        if reader.u32(vehicle) != 0x2400150:
            raise OSError('No verified local NFSVehicle')
        body = reader.read(vehicle, 0x1884)
        position = struct.unpack_from('<3f', body, 0x10A0)
        health = struct.unpack_from('<f', body, 0x1878)[0]
        if not all(math.isfinite(x) for x in (*position, health)):
            raise OSError('Non-finite vehicle data')
        result['vehicle'] = dict(position=position, health=health,
                                 externally_controlled=bool(body[0xA7C]),
                                 animation_controlled=bool(body[0xA7D]),
                                 collisions_disabled=bool(body[0xAE3]))
        # Retain the native basis as evidence for later spawn recovery. Position
        # alone cannot safely reconstruct vehicle orientation or a world matrix.
        matrix = struct.unpack_from('<16f', body, 0x1070)
        axes = [matrix[i:i + 3] for i in (0, 4, 8)]
        if (all(math.isfinite(x) for x in matrix)
                and all(abs(sum(x*x for x in axis) - 1) < 0.05 for axis in axes)
                and all(abs(sum(a*b for a, b in zip(axes[i], axes[j]))) < 0.05
                        for i, j in ((0, 1), (0, 2), (1, 2)))):
            # The fourth words contain other physics state (not homogeneous
            # 0/0/0/1). Never expose this block as a native 4x4 teleport matrix.
            result['vehicle']['basis_candidate'] = [list(axis) for axis in axes]
        # Separate AI autopilot from physics animation flags; native F29820/12BC270.
        try:
            owner = reader.u32(reader.u32(reader.u32(entity + 0x80)) + 0xE0)
            result['vehicle']['owner_matches_local'] = owner == player
            wrapper = reader.u32(entity + 0x7C)
            component = reader.u32(wrapper + 8) if wrapper else 0
            if component and reader.u32(component) == 0x258F018:
                result['vehicle']['autopilot_enabled'] = bool(reader.read(component + 0x20, 1)[0])
            else:
                result['vehicle']['autopilot_unknown'] = True
        except OSError:
            result['vehicle']['autopilot_unknown'] = True
    except OSError as exc:
        result['vehicle_error'] = str(exc)
    return result


def export_cofr(rows, destination, wall_ms):
    """Native upstream format; observations are markers, never fabricated packets/digests."""
    sys.path.insert(0, str(UPSTREAM))
    import cofr
    for slot, role in enumerate(('HOST', 'GAST')):
        records = []
        for row in rows:
            state = row['clients'][role]
            records.append(dict(type=cofr.T_MARKER, mono_us=row['mono_us'], frame=row['sample'],
                                kind=4, text=json.dumps(state, sort_keys=True)))
        cofr.dump(str(destination / (role.lower() + '.cofr')),
                  dict(slot=slot, role=slot, reason=4, wall_unix_ms=wall_ms), records)


def analyze(rows, scenario):
    """Sustained observations, not proof of an engine cause or collision/stream readiness."""
    if not isinstance(scenario.get('grace_seconds'), (int, float)) or not math.isfinite(scenario['grace_seconds']) or scenario['grace_seconds'] <= 0:
        raise ValueError('grace_seconds must be finite and positive')
    grace = scenario['grace_seconds'] * 1_000_000
    since = {}
    findings = []
    fired = set()
    comparable = 0
    previous_time = None
    previous_comparable = False
    comparable_run = 0
    longest_comparable_run = 0
    for row in rows:
        stamp = row['mono_us']
        if previous_time is not None and stamp < previous_time:
            raise ValueError('Trace timestamps must be monotonic')
        gap = previous_time is not None and stamp - previous_time > scenario.get('max_sample_gap_seconds', 2) * 1_000_000
        if gap:
            since.clear()
            comparable_run = 0
        a, b = (row['clients'][r] for r in ('HOST', 'GAST'))
        checks = {}
        is_comparable = bool(a.get('challenge') and b.get('challenge'))
        comparable += int(is_comparable)
        if is_comparable:
            if previous_time is not None and previous_comparable and not gap:
                comparable_run += stamp - previous_time
            longest_comparable_run = max(longest_comparable_run, comparable_run)
        else:
            comparable_run = 0
        previous_time = stamp
        previous_comparable = is_comparable
        if a.get('challenge') and b.get('challenge'):
            checks['mission_mismatch'] = a['challenge'] != b['challenge'] or a.get('level') != b.get('level')
        for role, state in (('HOST', a), ('GAST', b)):
            checks[role + '_vehicle_unavailable'] = not bool(state.get('vehicle'))
            if scenario.get('expect_drivable') and state.get('vehicle'):
                v = state['vehicle']
                checks[role + '_control_flag_active'] = v['externally_controlled'] or v['animation_controlled']
                checks[role + '_autopilot_active'] = v.get('autopilot_enabled') is True
                checks[role + '_owner_mismatch'] = v.get('owner_matches_local') is False
        for key in sorted(set(since) | set(checks)):
            if not checks.get(key, False):
                since.pop(key, None)
            else:
                since.setdefault(key, row['mono_us'])
                if row['mono_us'] - since[key] >= grace and key not in fired:
                    findings.append(dict(observation=key, first_us=since[key], confirmed_us=row['mono_us']))
                    fired.add(key)
    return dict(verdict='observations_found' if findings else 'no_observation' if longest_comparable_run >= grace else 'insufficient_evidence',
                findings=findings, samples=len(rows), comparable_samples=comparable,
                limits='Polling is not atomic. No terrain readiness, QTE, timer, result or packet decoding. No automatic in-game replay.')


def triage(rows, scenario):
    """Small evidence packet: transition timeline, gaps and nearest failure samples."""
    report = analyze(rows, scenario)
    timeline = []
    previous = {}
    gaps = []
    last = None
    for index, row in enumerate(rows):
        stamp = row['mono_us']
        if last is not None:
            if stamp < last:
                raise ValueError('Trace timestamps must be monotonic')
            if stamp - last > 2_000_000:
                gaps.append(dict(after_us=last, before_us=stamp))
        last = stamp
        for role in ('HOST', 'GAST'):
            s = row['clients'][role]
            v = s.get('vehicle') or {}
            state = dict(challenge=s.get('challenge'), level=s.get('level'),
                         player_id=s.get('player_id'), vehicle_available=bool(v),
                         external=v.get('externally_controlled'), animation=v.get('animation_controlled'),
                         autopilot=v.get('autopilot_enabled'), owner_matches_local=v.get('owner_matches_local'))
            if previous.get(role) != state:
                if len(timeline) < 40:
                    timeline.append(dict(at_us=stamp, role=role, **state))
                previous[role] = state
    first = min((f['first_us'] for f in report['findings']), default=None)
    evidence = []
    if first is not None and rows:
        nearest = min(range(len(rows)), key=lambda i: abs(rows[i]['mono_us'] - first))
        evidence = rows[max(0, nearest - 2):nearest + 4]
    return dict(report=report, timeline=timeline, timeline_limit=40,
                sampling_gaps=gaps[:10], gap_count=len(gaps), evidence=evidence,
                caution='Sampling gaps weaken duration claims; positions do not prove terrain readiness. No engine cause inferred.')


def write_bundle(rows, scenario, destination):
    packet = triage(rows, scenario)
    (destination / 'triage.json').write_text(json.dumps(packet, indent=2), encoding='utf-8')
    report = packet['report']
    lines = [f"verdict={report['verdict']} samples={report['samples']} gaps={packet['gap_count']}"]
    for finding in report['findings'][:8]:
        lines.append(f"{finding['observation']}: first={finding['first_us']/1e6:.2f}s confirmed={finding['confirmed_us']/1e6:.2f}s")
    lines += ['Evidence: triage.json (at most 6 nearby samples, 40 state changes).', packet['caution']]
    (destination / 'brief.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return packet


def record(args):
    if not 1 <= args.seconds <= 600:
        raise ValueError('Capture must be bounded to 1..600 seconds')
    if not (UPSTREAM / 'cofr.py').is_file():
        raise ValueError('Missing pinned Flight writer; see diagnostics/README.md')
    scenario = json.loads(args.scenario.read_text(encoding='utf-8'))
    analyze([], scenario)  # Validate before opening any process or starting a capture.
    session = json.loads(args.session.read_text(encoding='utf-8-sig'))
    ids = session.get('ClientProcessIds', [])
    if len(ids) != 2 or len(set(ids)) != 2 or not session.get('ServerProcessId'):
        raise ValueError('Requires two LAN clients and server; solo sessions are deliberately refused')
    executable = GAME / 'Need For Speed The Run.exe'
    if hashlib.sha256(executable.read_bytes()).hexdigest().upper() != BUILD:
        raise ValueError('Unverified game build; refusing address-based capture')
    readers = []
    try:
        for pid in ids:
            readers.append(Reader(pid, executable))
        with_server = Reader(session['ServerProcessId'], GAME / 'NFSTR_Server.exe')
        with_server.close()
        if any(sample(r).get('singleplayer') != 0 for r in readers):
            raise ValueError('LAN mode not confirmed; no capture started')
        destination = ROOT / 'outputs' / ('coop-flight-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        destination.mkdir()
        wall_ms = time.time_ns() // 1_000_000
        start = time.monotonic_ns()
        rows = []
        print('Recording read-only to ' + str(destination), flush=True)
        try:
            with (destination / 'samples.jsonl').open('x', encoding='utf-8') as out:
                while (time.monotonic_ns() - start) / 1e9 < args.seconds:
                    row = dict(sample=len(rows), mono_us=(time.monotonic_ns() - start) // 1000,
                               clients={role: sample(r) for role, r in zip(('HOST', 'GAST'), readers)})
                    out.write(json.dumps(row) + '\n')
                    out.flush()
                    rows.append(row)
                    time.sleep(0.25)
        except KeyboardInterrupt:
            pass
        report = analyze(rows, scenario)
        (destination / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        (destination / 'scenario.json').write_text(json.dumps(scenario, indent=2), encoding='utf-8')
        write_bundle(rows, scenario, destination)
        # Keep independent JSON evidence even if optional COFR conversion fails.
        try:
            export_cofr(rows, destination, wall_ms)
        except (ImportError, OSError, ValueError) as exc:
            (destination / 'export-error.txt').write_text(str(exc), encoding='utf-8')
            print('COFR export failed; JSON samples/report retained.', file=sys.stderr)
        print(json.dumps(report, indent=2))
    finally:
        for reader in readers:
            reader.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    capture = commands.add_parser('record')
    capture.add_argument('--seconds', type=int, default=120)
    capture.add_argument('--session', type=Path, default=RESEARCH / 'local/lan-test-processes.json')
    capture.add_argument('--scenario', type=Path, default=ROOT / 'diagnostics/scenarios/transition.json')
    offline = commands.add_parser('analyze')
    offline.add_argument('trace', type=Path)
    offline.add_argument('--scenario', type=Path, default=ROOT / 'diagnostics/scenarios/transition.json')
    offline.add_argument('--bundle', action='store_true', help='Write bounded triage.json and brief.txt beside trace')
    args = parser.parse_args()
    if args.command == 'record':
        record(args)
    else:
        rows = [json.loads(line) for line in args.trace.read_text(encoding='utf-8').splitlines() if line.strip()]
        scenario = json.loads(args.scenario.read_text(encoding='utf-8'))
        if args.bundle:
            write_bundle(rows, scenario, args.trace.parent)
        print(json.dumps(analyze(rows, scenario), indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as exc:
        print('Capture/analysis stopped: ' + str(exc), file=sys.stderr)
        sys.exit(2)
