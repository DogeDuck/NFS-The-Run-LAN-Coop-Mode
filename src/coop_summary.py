"""Short verdicts for the newest recorder outputs (token saver: read this instead of jsonl files).

  python coop_summary.py            newest of every kind
  python coop_summary.py --all 3    newest 3 of every kind

Covers outputs/grid-slots-*, garage-selection-*, player-race-progress-*, missing-lookup-*,
nitro-flames-*.json. Read-only. Never interprets missing data as success.
"""
import argparse
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'outputs'


def jsonl(path, limit=200000):
    rows = []
    if not path.is_file():
        return rows
    with path.open(encoding='utf-8', errors='replace') as f:
        for i, line in enumerate(f):
            if i >= limit:
                break
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    return rows


def status(directory):
    for name in ('status.json', 'recovery.json'):
        p = directory / name
        if p.is_file():
            try:
                return json.loads(p.read_text(encoding='utf-8')).get('status', '?')
            except ValueError:
                return 'unreadable'
    return 'no status file'


def grid_slots(d):
    rows = [r for r in jsonl(d / 'samples.jsonl') if r.get('complete')]
    if not rows:
        return ['no complete sample']
    trusted = [r for r in rows if r.get('grid', {}).get('trusted')]
    leak = sum(1 for r in trusted if r['verdict'].get('human_id_in_battle_slot'))
    last = rows[-1]['verdict']
    reserved = max(r['grid']['adapter']['reserved_counter'] for r in rows)
    stuck = {}
    for r in rows:
        for human, pending in r['verdict'].get('human_pending_spawns', {}).items():
            if pending:
                stuck[human] = stuck.get(human, 0) + 1
    out = ['samples %d, grid trusted %d, challenge %s' % (len(rows), len(trusted), rows[-1].get('challenge')),
           'human slots %s, npc slots %s' % (last.get('human_slots'), last.get('npc_slots')),
           'battle inputs (last) %s' % last.get('battle_start_inputs'),
           'human id in BattleStart slot: %d of %d trusted samples' % (leak, len(trusted)),
           'reserved second human counter max %d' % reserved]
    if stuck:
        out.append('pending spawn order (E18>0) seen for humans %s (samples)' % stuck)
    verdict = 'OK slot fix' if trusted and not leak and reserved else ('FAIL human in battle slot' if leak else 'UNCLEAR')
    return out + ['VERDICT: ' + verdict]


ORDER = ('selected_request_spawn_apply', 'source_async_order_submit', 'source_async_job_register', 'source_bundle_request',
         'source_spawn_complete', 'source_order_discard', 'spawn_notification_mode2_message')


def garage(d):
    rows = jsonl(d / 'events.jsonl')
    if not rows:
        return ['no events (hooks: %s)' % status(d)]
    counts = collections.Counter(r.get('branch') for r in rows)
    first = {}
    for r in rows:
        first.setdefault(r.get('branch'), r.get('time', '')[11:23])
    out = ['events %d, hook status %s' % (len(rows), status(d)),
           'counts: ' + ', '.join('%s=%d' % (k, v) for k, v in counts.most_common())]
    out += ['first %s at %s' % (k, first[k]) for k in ORDER if k in first]
    per_role = collections.defaultdict(collections.Counter)
    for r in rows:
        b = r.get('branch') or ''
        if b.startswith('route_') or b.startswith('pause_show_'):
            per_role[r.get('role')][b] += 1
    for role, c in sorted(per_role.items(), key=lambda x: str(x[0])):
        out.append('%s route/pause: %s' % (role, ', '.join('%s=%d' % kv for kv in sorted(c.items()))))
    qte = collections.defaultdict(collections.Counter)
    for r in rows:
        b = r.get('branch') or ''
        if b.startswith('qte_'):
            qte[r.get('role')][b] += 1
    for role, c in sorted(qte.items(), key=lambda x: str(x[0])):
        out.append('%s qte: %s' % (role, ', '.join('%s=%d' % kv for kv in sorted(c.items()))))
    if qte:
        g, h, sv = qte.get('GAST', {}), qte.get('HOST', {}), qte.get('SERVER', {})
        if not g.get('qte_client_trigger_pressed') and h.get('qte_client_trigger_pressed'):
            out.append('QTE: GAST input trigger never fires (Q1: QTE scene/trigger not active on guest)')
        elif g.get('qte_client_trigger_pressed') and not g.get('qte_client_send_eventsync_reached'):
            out.append('QTE: GAST presses but its QTE never succeeds/sends EventSync (guest QTE chain/ANT state)')
        elif g.get('qte_client_send_eventsync_reached') and sv.get('qte_server_eventsync_received', 0) > sv.get('qte_server_eventsync_fire', 0):
            out.append('QTE: server receives EventSync it cannot match (entity id lookup fails, id mapping)')
        elif g.get('qte_client_send_eventsync_reached'):
            out.append('QTE: GAST EventSync sent; this does not identify the QTE success instance or prove that guest input works')
    try:
        hooks = {h.get('name') for h in json.loads((d / 'recovery.json').read_text(encoding='utf-8')).get('hooks', [])}
    except (OSError, ValueError):
        hooks = set()
    if 'source_async_order_submit' not in hooks:
        return out + ['VERDICT: recorded without --completion hooks, no gas-station verdict possible']
    first_sel = min((x.get('time', '') for x in rows if x.get('branch') == 'selected_vehicle_apply'), default='~')
    after = [r.get('branch') for r in rows if r.get('time', '') >= min(
        (x.get('time', '') for x in rows if x.get('branch') == 'selected_vehicle_apply'), default='~')]
    orders, done = after.count('source_async_order_submit'), after.count('source_spawn_complete')
    out.append('after first selection: %d async orders, %d completed, %d bundle requests, %d discards (compare SP vs LAN)' % (
        orders, done, after.count('source_bundle_request'), after.count('source_order_discard')))
    if 'source_async_job_register' in hooks:
        out.append('after first selection: %d job registrations ([data+58]!=0), %d spawndata calls' % (
            after.count('source_async_job_register'), after.count('source_async_spawndata')))
        # SP reference 05.11: also 0 job registrations, yet orders complete via spawndata (127D3B0)
        # together with Mode2 spawn notifications -> job map is NOT the completion route.
        out.append('after first selection: %d Mode2 spawn notifications' % after.count('spawn_notification_mode2_message'))
        if orders and not done and not after.count('spawn_notification_mode2_message'):
            out.append('HINT: no Mode2 spawn notification after selection (SP reference gets one per completed order)')
    if 'server_bundle_ack_remove' in hooks:
        sent = collections.Counter(r.get('role') for r in rows if r.get('branch') == 'client_send_bundle_loaded' and r.get('time', '') >= first_sel)
        unl = collections.Counter(r.get('role') for r in rows if r.get('branch') in ('client_send_bundle_unloaded', 'client_send_bundle_unloaded_fix') and r.get('time', '') >= first_sel)
        got = after.count('server_bundle_ack_remove')
        out.append('handshake after first selection: client loaded msgs %s, unloaded msgs %s, server received %d' % (
            dict(sent) or 0, dict(unl) or 0, got))
        acc = collections.Counter(r.get('role') for r in rows if r.get('branch') in ('client_bundle_load_msg_accepted', 'client_bundle_unload_msg_reached') and r.get('time', '') >= first_sel)
        bc = sum(1 for r in rows if r.get('branch', '').startswith('server_bundle_state_broadcast') and r.get('time', '') >= first_sel)
        if 'server_bundle_state_broadcast' in hooks:
            out.append('handshake: server bundle broadcasts %d, client accepted bundle msgs %s' % (bc, dict(acc) or 0))
        if not sent and not unl and 'server_bundle_state_broadcast' in hooks and not acc:
            out.append('HANDSHAKE: clients never accept the server bundle request (not delivered, or dropped at E574E9 because [level+7FC]==0)')
        elif not sent and not unl and acc:
            out.append('HANDSHAKE: clients accept the bundle request but never report (client load never finishes, or [level+7FC]!=2 / [level+81C]==0 at E4CE90)')
        elif not sent and not unl:
            out.append('HANDSHAKE: clients never report bundle loaded/unloaded (client condition [level+7FC]==2 and [level+81C]!=0 not met?)')
        elif not got:
            out.append('HANDSHAKE: clients send, server never receives (message lost on the way)')
        else:
            out.append('HANDSHAKE: clients send and server receives; if Level+80C stays >0 the sender is not matched to the waiting player (ID mapping)')
    if 'source_async_create_request' in hooks:
        chain = (('source_async_create_request', 'create_request'), ('request_resource_load', 'resource_load'),
                 ('request_cb_resource', 'cb_resource'), ('request_cb_job_register', 'cb_job'),
                 ('source_spawn_complete', 'spawn_complete'))
        out.append('after first selection, request chain: ' + ' -> '.join('%s %d' % (label, after.count(k)) for k, label in chain))
        if after.count('source_async_create_request') and not after.count('request_cb_resource'):
            out.append('HINT: requests created but load-ready callback 127C970 never ran (resource never ready on this process)')
    if orders and done:
        return out + ['VERDICT: orders complete after selection (reference behaviour, e.g. SP)']
    if orders and not done and 'source_bundle_request' not in after and 'source_order_discard' not in after:
        return out + ['VERDICT: case (d) async order without bundle branch never completes (TANKSTELLE-SPAWNPFAD 05.11)']
    if 'source_bundle_request' in counts and not counts.get('source_spawn_complete'):
        out.append('VERDICT: bundle requested, never completed -> case (b) headless load (TANKSTELLE-SPAWNPFAD)')
    elif counts.get('source_order_discard'):
        out.append('VERDICT: order discarded -> case (c)')
    elif 'selected_request_spawn_apply' in counts and 'source_async_order_submit' not in counts:
        out.append('VERDICT: apply seen but no async order -> case (a)')
    else:
        out.append('VERDICT: no clear gas-station pattern (check that exactly one selection happened)')
    return out


def progress(d):
    rows = jsonl(d / 'samples.jsonl')
    if not rows:
        return ['no samples']
    by_role = collections.defaultdict(list)
    for r in rows:
        by_role[r.get('role')].append(r)
    out = ['samples %d' % len(rows)]
    for role, items in sorted(by_role.items()):
        fr = [i.get('client', {}).get('local_actor', {}).get('fraction') for i in items]
        fr = [x for x in fr if isinstance(x, (int, float))]
        lp = [i.get('client', {}).get('local_player_fraction') for i in items]
        lp = [x for x in lp if isinstance(x, (int, float))]
        actors = [len(i.get('ai_route', {}).get('actors', [])) for i in items if i.get('ai_route', {}).get('available')]
        servers = [p.get('fraction') for i in items for p in i.get('server', {}).get('players', [])]
        servers = [x for x in servers if isinstance(x, (int, float))]
        line = '%s: actor fraction %s..%s, player fraction %s..%s, route actors %s..%s' % (
            role, min(fr, default='-'), max(fr, default='-'), min(lp, default='-'), max(lp, default='-'),
            min(actors, default='-'), max(actors, default='-'))
        if servers:
            line += ', server human fraction %s..%s' % (min(servers), max(servers))
        out.append(line)
    return out


def missing(d):
    p = d / 'report.json'
    if not p.is_file():
        return ['no report (status %s)' % status(d)]
    r = json.loads(p.read_text(encoding='utf-8'))
    seen = r.get('observed_missing_lookups')
    n = len(seen) if isinstance(seen, list) else seen
    out = ['missing lookups observed: %s, status %s' % (n, status(d))]
    if isinstance(seen, list):
        out += ['  ' + json.dumps(x)[:160] for x in seen[:3]]
    else:
        # Recorder stores a count in report.json; keep native token details
        # available through this summary, without opening raw logs manually.
        keys = ('resolved_key', 'type_token', 'parent_token', 'returned_node', 'tree', 'caller')
        for row in jsonl(d / 'events.jsonl')[:3]:
            event = row.get('event', {})
            if isinstance(event, dict):
                out.append('lookup: ' + json.dumps({k: event[k] for k in keys if k in event}))
    if r.get('process_alive_at_end') is False:
        out.append('client exited during capture; missing lookup is evidence, not yet a proven cause or fix')
    return out


def nitro(p):
    j = json.loads(p.read_text(encoding='utf-8'))
    return ['status %s, scale %s, writes %d, restored %d' % (j.get('status'), j.get('scale'), len(j.get('writes', [])),
                                                          len(j.get('restored', [])))]


def vehicle_requests(path):
    j = json.loads(path.read_text(encoding='utf-8'))
    s = j.get('summary', {})
    out = ['%s pid %s: %d requests, %d not ready, %d with ready callback, %d resource entries' % (
        j.get('identity', {}).get('role'), j.get('identity', {}).get('pid'), s.get('requests', 0), s.get('not_ready', 0),
        s.get('with_ready_callback', 0), s.get('resource_entries', 0))]
    out += ['  name: ' + x for x in s.get('strings', [])[:12]]
    if not s.get('requests'):
        out.append('VERDICT: no pending vehicle request found (probe while stuck in gas station?)')
    return out


def native_faults(directory):
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8-sig'))
    lines = ['status %s, reason %s, snapshots %s' % (manifest.get('status'), manifest.get('stop_reason'), manifest.get('exception_snapshots'))]
    for path in sorted(directory.glob('exception-*.json'))[:4]:
        doc = json.loads(path.read_text(encoding='utf-8-sig'))
        event = doc.get('exception', {})
        regs = doc.get('registers', doc.get('crash', {}).get('registers', {}))
        lines.append('fault: code %s address %s first_chance %s' % (hex(event.get('code', 0)), hex(event.get('address', 0)), event.get('first_chance')))
        lines.append('registers: ' + json.dumps(regs))
        if doc.get('physics'):lines.append('physics: ' + json.dumps(doc['physics']))
        if doc.get('physics', {}).get('compartment_pointer'):
            from bridge_exception_snapshot import memory_from_document
            try:
                m=memory_from_document(doc['capture']);table=int(doc['physics']['compartment_pointer'],16)
                lines.append('physics compartment tree: case_flag=%s parent_index=%s root=%s' %
                             (m.u32(table+0x40),m.u32(table+0x4C),hex(m.u32(table+0x38))))
            except ValueError as exc:lines.append('compartment metadata unavailable: '+str(exc))
        if event.get('address') == 0x64112F and isinstance(regs.get('esi'), int):
            from bridge_exception_snapshot import memory_from_document
            import struct
            try:
                raw = memory_from_document(doc['capture']).read(regs['esi'], 24)
                words = struct.unpack('<6I', raw)
                lines.append('Havok request (native6410C0): compartment=%d asset=%s words=%s' %
                             (words[0], hex(words[1]), [hex(x) for x in words]))
            except (ValueError, OSError, KeyError) as exc:
                lines.append('Havok request unavailable: ' + str(exc))
        if doc.get('fault_code'):lines.append('fault instruction bytes: ' + doc['fault_code'][:128])
        lines.append('frame candidates: ' + json.dumps(doc.get('frame_pointer_candidates', [])[:8]))
        lines.append('stack candidates: ' + json.dumps(doc.get('stack_words', [])[:48]))
    return lines


def pause_hud(path):
    doc=json.loads(path.read_text(encoding='utf-8-sig'))
    out=[]
    for row in doc.get('clients',[]):
        out.append('%s pid %s: pause %s, HUD %s' % (row.get('role'),row.get('pid'),
            row.get('.pausest','adapter not installed'),row.get('.hudstat','adapter not installed')))
    return out+['Counters are hook evidence; the user must confirm driving and visible HUD behaviour.']


KINDS = (('pause-hud-state-*.json',pause_hud),('bridge-exception-*', native_faults), ('grid-slots-*', grid_slots), ('garage-selection-*', garage), ('player-race-progress-*', progress),
         ('missing-lookup-*', missing), ('nitro-flames-*.json', nitro), ('vehicle-requests-*.json', vehicle_requests))


def summarize(newest=1, base=OUT):
    lines = []
    for pattern, fn in KINDS:
        items = sorted(base.glob(pattern), key=lambda p: p.stat().st_mtime)[-newest:]
        for item in items:
            lines.append('== %s' % item.name)
            try:
                lines += ['  ' + x for x in fn(item)]
            except Exception as exc:  # summary must never crash the session
                lines.append('  unreadable: %s' % exc)
    return lines or ['no recorder outputs found']


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--all', type=int, default=1, metavar='N')
    p.add_argument('--physics-dump', type=Path, help='Bounded Havok64112F context from an existing local game dump')
    p.add_argument('--directory', type=Path, help='Summarize only one recorder directory instead of historical unrelated captures')
    args=p.parse_args()
    if args.directory:
        import fnmatch
        fn=next((fn for pattern,fn in KINDS if fnmatch.fnmatch(args.directory.name,pattern)),None)
        if fn is None:p.error('Unknown recorder directory kind')
        print('\n'.join(fn(args.directory)))
    elif args.physics_dump:
        print('\n'.join(physics_dump(args.physics_dump)))
    else:print('\n'.join(summarize(args.all)))


def physics_dump(path):
    from inspect_cinematic_crash import inspect
    from minidump_memory import DumpMemory, MissingMemory
    import struct
    report=inspect(path)
    out=['dump %s fault %s %s' % (path.name,report['address'],report['exception'])]
    if report['address']!='0x64112f':return out+['Different native fault; no Havok interpretation.']
    memory=DumpMemory(path.read_bytes())
    try:
        req=struct.unpack('<6I',memory.read(int(report['registers']['esi'],16),24))
        out.append('compartment=%d asset=%s' % (req[0],hex(req[1])))
        asset=req[1]
        out.append('physics asset words: '+json.dumps([hex(x) for x in struct.unpack('<16I',memory.read(asset,64))]))
        array=memory.u32(asset+0x20);count=memory.u32(array-4) if array else 0
        if count>16:return out+['LOD array exceeds bounded16 entries; not followed.']
        refs=struct.unpack('<%dI'%count,memory.read(array,count*4)) if count else (memory.u32(asset+0x28),)
        for ref in refs:
            if not ref:continue
            try:
                words=struct.unpack('<8I',memory.read(ref,32))
                name=memory.optional(words[3],256) if words[3] else None
                out.append('physics resource ref %s words=%s name=%s' % (hex(ref),[hex(x) for x in words],
                    repr(name.split(b'\0')[0].decode('ascii','replace')) if name else 'not captured'))
            except MissingMemory as exc:out.append('LOD not captured: '+str(exc))
        compartment=memory.u32(0x2868654+req[0]*4) if req[0]<64 else 0
        out.append('resource compartment pointer '+hex(compartment))
    except MissingMemory as exc:out.append('not captured (not proof of unloaded memory): '+str(exc))
    return out


if __name__ == '__main__':
    main()
