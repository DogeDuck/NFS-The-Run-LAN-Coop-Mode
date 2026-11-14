"""Short verdicts for the newest recorder outputs (token saver: read this instead of jsonl files).

  python coop_summary.py            newest of every kind
  python coop_summary.py --all 3    newest 3 of every kind
  python coop_summary.py --launcher-logs PLAYER_LOG_FOLDER

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
        for key in ('.emptyhs','.btlleas'):
            if key in row:out.append('%s %s: %s'%(row.get('role'),key,row[key]))
    return out+['Counters are hook evidence; the user must confirm driving and visible HUD behaviour.']


def windows_game_faults(path):
    doc=json.loads(path.read_text(encoding='utf-8-sig'))
    out=[]
    for row in doc.get('events',[])[:5]:
        try:address=hex(int(doc['image_base'])+int(row['offset'],16))
        except (ValueError,TypeError,KeyError):address='unknown'
        out.append('%s: %s exception %s offset %s address %s' %
            (row.get('time'),row.get('app'),row.get('exception'),row.get('offset'),address))
    return (out or ['No matching Windows fault metadata found'])+['Windows metadata only; no stack/dump or confirmed race identity.']


def story_finish_flow(directory):
    """Summarize Claude's bounded Story/TooSlow probes without inferring wins."""
    if not directory.is_dir():raise FileNotFoundError('Recorder directory does not exist: '+str(directory))
    rows=jsonl(directory/'events.jsonl')
    recovery=directory/'recovery.json'
    manifest=json.loads(recovery.read_text(encoding='utf-8-sig')) if recovery.is_file() else {}
    counts=collections.defaultdict(collections.Counter)
    for hook in manifest.get('hooks',[]):
        counts[str(hook.get('role','?'))][str(hook.get('name','?'))]+=0
    results=collections.defaultdict(collections.Counter)
    states=collections.defaultdict(set)
    expired=0
    phase_events=collections.defaultdict(list)
    cinematic_results=collections.defaultdict(collections.Counter)
    scene_markers=collections.defaultdict(list)
    qte_identities=collections.defaultdict(list)
    for row in rows:
        role=str(row.get('role','?'));probe=str(row.get('probe','?'))
        counts[role][probe]+=1
        event=row.get('event') or {}
        if probe=='story_predicate':
            results[role][str(event.get('native_success','unknown'))]+=1
        if probe=='racer_state_request':
            states[role].add((str(event.get('racer_id')),str(event.get('state')),str(event.get('desired'))))
        if probe.startswith('script_vehicle_') and len(phase_events[role])<12:
            phase_events[role].append((probe,{k:event[k] for k in ('interaction','player_id','player','bot_byte','vehicle') if k in event}))
        if probe.startswith('battle_') and len(phase_events[role])<12:
            phase_events[role].append((probe,{k:event[k] for k in ('old_opponent','incoming_opponent','defeated_before','timer_before','requested_opponent') if k in event}))
        if probe.startswith('cin_') and event.get('lookup_status'):
            cinematic_results[role][probe+':'+str(event['lookup_status'])]+=1
        if probe.startswith('qte_') and len(qte_identities[role])<12:
            if probe.startswith('qte_player_') and 'target_event_hash' in event:
                # Legacy recorder mislabeled message+38. It is a raw bus key,
                # not an established event hash. Preserve the historical log.
                event=dict(event,message_key_38_raw=event['target_event_hash'])
            qte_identities[role].append((probe,{k:event[k] for k in
                ('asset_guid','network_entity_id','resolved','lookup_status','kind','receiver','event_hash','sender_player_id','callback_widget_id','completion_proven',
                 'source_event_hash','message_key_38_raw','route_flags','message_player_id','recipient_connection','native_route','delivery_proven') if k in event}))
        if probe.startswith(('cin_','qte_')):
            state=(row.get('observed_state') or {}).get(role,{})
            marker=(state.get('level'),state.get('challenge'))
            if marker not in scene_markers[role] and len(scene_markers[role])<8:scene_markers[role].append(marker)
        expired=max(expired,int(row.get('expired_events') or 0))
    hooks=collections.Counter(h.get('state','unknown') for h in manifest.get('hooks',[]))
    out=['events %d, hook status %s, hook states %s' % (len(rows),status(directory),dict(hooks))]
    if any(probe.startswith(('cin_','qte_')) for probes in counts.values() for probe in probes) and rows:
        for role,state in (rows[-1].get('observed_state') or {}).items():
            if isinstance(state,dict):out.append('%s last scene state: %s'%(role,{key:state[key] for key in ('level','challenge','player_id','state_error') if key in state}))
    for role,probes in sorted(counts.items()):
        out.append('%s probes: %s' % (role,', '.join('%s=%s'%x for x in sorted(probes.items()))))
        if results[role]:out.append('%s native predicate outcomes: %s' % (role,dict(results[role])))
        if states[role]:out.append('%s racer state requests (id,state,desired): %s' % (role,sorted(states[role])[:16]))
        for event in phase_events[role]:out.append('%s phase event: %s'%(role,event))
        if cinematic_results[role]:out.append('%s cinematic lookup results: %s'%(role,dict(cinematic_results[role])))
        for event in qte_identities[role]:out.append('%s QTE identity: %s'%(role,event))
        if scene_markers[role]:out.append('%s scenes observed (level,challenge): %s'%(role,scene_markers[role]))
    if expired:out.append('Ring overflow seen: at least %d expired events; absence is inconclusive.' % expired)
    if not rows:out.append('No recorded events; this does not prove that no failure/transition occurred.')
    return out+['Probe hits/requests are not proof of team victory, delivery, or the reason for a restart.']


def bundle_owner_preflight(path):
    doc=json.loads(path.read_text(encoding='utf-8-sig'));out=['All clients GUID-layout verified: '+str(doc.get('all_clients_verified'))]
    for row in doc.get('clients',[]):
        out.append('%s: matched=%d mismatched=%d unavailable=%d'%(row.get('role'),len(row.get('matches',[])),len(row.get('mismatches',[])),len(row.get('unavailable',[]))))
        for item in row.get('mismatches',[])[:4]:out.append('MISMATCH '+str(item))
    return out+['Read-only layout check, not physics/gameplay proof.']


def bundle_owner_test(directory):
    rows=jsonl(directory/'events.jsonl');out=['status '+status(directory)]
    recovery=directory/'recovery.json'
    if recovery.exists():out.append('restore '+str(json.loads(recovery.read_text(encoding='utf-8-sig')).get('restore','not recorded')))
    if rows:
        out.append('last counters '+str(rows[-1].get('counters',{})))
        out.append('last scene '+str({k:v for k,v in rows[-1].get('state',{}).items() if k in ('challenge','level','state_error')}))
    else:out.append('No samples; not proof of a working fix.')
    return out+['Owner fallback counts do not prove correct physics loading; confirm the10.31->10.4 transition in game.']


def owner_lookup(directory):
    import uuid
    rows=jsonl(directory/'events.jsonl');out=['status '+status(directory)]
    recovery=directory/'recovery.json'
    if recovery.exists():
        m=json.loads(recovery.read_text(encoding='utf-8-sig'));out.append('restore '+str(m.get('restore','not recorded')))
    if rows:
        head=[int(v,16) for v in rows[-1].get('head',[])]
        out.append('calls=%s registry_misses=%s fallbacks=%s'%(head[0] if head else '?',head[1] if len(head)>1 else '?',head[5] if len(head)>5 else '?'))
    bad=[r for r in rows if r.get('kind')=='bad_owner']
    out.append('recorded miss samples '+str(len(bad)))
    catalog=OUT/'chicago-bundle-owner-catalog.json'
    guid=json.loads(catalog.read_text())['asset_guid'] if catalog.exists() else None
    for row in bad[-2:]:
        blocks=row.get('blocks',{});out.append('partition names '+str(row.get('strings',[])[:2]))
        raw=blocks.get('parent_partition','')
        try:
            blob=bytes.fromhex(raw)
            if guid:
                pattern=uuid.UUID(guid).bytes_le
                offsets=[hex(i) for i in range(len(blob)-15) if blob[i:i+16]==pattern]
                out.append('prefab fileGUID matches in saved partition at '+str(offsets))
        except (ValueError,TypeError):pass
        registry=blocks.get('registry',[])
        out.append('registered story partitions '+str([r[3] for r in registry if len(r)==5 and '/sm_10_' in r[3]][:16]))
    return out+['Historic capture; a supplied test answer is not an automatic owner rule.']


def cinematic_pointer_hints(directory):
    """Bounded last-per-owner pointers for read-only follow-up; never live proof."""
    hints={}
    for row in jsonl(directory/'events.jsonl'):
        if row.get('probe')!='cin_actor_lookup':continue
        event=row.get('event') or {};key=(row.get('role'),event.get('context'))
        hints[key]=dict(role=row.get('role'),owner=event.get('context'),data=event.get('owner_data'),actor=event.get('resolved'))
    return list(hints.values())[-32:]


def cinematic_state(path):
    doc=json.loads(path.read_text(encoding='utf-8-sig'));out=[];guid_roles=collections.defaultdict(dict)
    for row in doc.get('clients',[]):
        role=row.get('role');scan=row.get('scan',{});entities=scan.get('entities',[])
        out.append('%s bounded=%s, scanned=%s bytes, native types=%s'%(role,scan.get('bounded'),scan.get('bytes_scanned'),dict(collections.Counter(e['type'] for e in entities))))
        for kind in ('ant_controller','ant_animatable'):
            selected=[e for e in entities if e['type']==kind]
            if kind=='ant_controller':
                out.append('%s ant_controller end_watch_enabled=%d; +20=0 does not mean stopped (IgnoreEnd leaves it zero)'%(role,sum(bool(e.get('end_watch_byte',e.get('active',0))) for e in selected)))
            else:
                out.append('%s %s activity_raw=%d nullANT=%d null_raw350=%d'%(role,kind,sum(bool(e.get('active_raw',e.get('active'))) for e in selected),sum(e.get('controller')=='0x0' for e in selected),sum(e.get('raw_350',e.get('mesh'))=='0x0' for e in selected)))
        if 'ant_delta_guard' in row:out.append('%s ANT delta guard: %s'%(role,row['ant_delta_guard']))
        if 'unavailable' in row:out.append('%s incomplete: %s'%(role,row['unavailable']))
        for direct in row.get('direct',[])[:12]:out.append('%s observed object: %s'%(role,direct))
        for e in entities:
            if e.get('guid') and e['type']=='ant_animatable':guid_roles[e['guid']][role]=(e.get('active_raw',e.get('active')),e.get('controller')!='0x0',e.get('raw_350',e.get('mesh'))!='0x0')
    mismatches=[(guid,roles) for guid,roles in guid_roles.items() if len(roles)>1 and len(set(roles.values()))>1]
    out.extend('shared GUID different (activityRaw,hasANT,raw350Nonzero): %s %s'%pair for pair in mismatches[:12])
    return out+['Bounded non-atomic scan: raw+350 is not a verified renderer/mesh contract. Missing hits do not prove missing entities; matching GUIDs do not establish camera ownership.']


def battle_state(path):
    doc=json.loads(path.read_text(encoding='utf-8-sig'));out=[]
    for row in doc.get('targets',[]):
        role=row.get('role');state=row.get('client',{}).get('state',{})
        if row.get('players') is not None:
            out.append('%s local id %s, players (id,bot,kind): %s'%(role,state.get('player_id'),
                [(p.get('id'),p.get('bot_byte'),p.get('kind')) for p in row['players']]))
        records=row.get('client',{}).get('records',[])
        if records:
            out.append('%s racers (id,kind,state,rank,progress): %s'%(role,
                [(r.get('id'),r.get('driver_kind'),r.get('state'),r.get('rank_raw'),r.get('percentage')) for r in records[:16]]))
            ids=collections.Counter(r.get('id') for r in records)
            if any(n>1 for n in ids.values()):out.append('%s duplicate racer IDs: %s; ID-only lookup is ambiguous.'%(role,[rid for rid,n in ids.items() if n>1]))
        if 'mode_fields_raw' in row:out.append('%s mode fields raw: %s'%(role,row['mode_fields_raw']))
        if 'mode_records_raw' in row:out.append('%s per-player raw records: %s'%(role,row['mode_records_raw'][:8]))
        if 'local_control' in row:out.append('%s vehicle control flags: %s'%(role,row['local_control']))
        for name, counters in row.get('guards',{}).items():
            out.append('%s %s counters: %s'%(role,name,counters))
        if 'battle_scan' in row:
            scan=row['battle_scan']
            out.append('%s Battle scan: %s entities, bounded=%s'%(role,len(scan.get('entities',[])),scan.get('bounded')))
            for entity in scan.get('entities',[])[:8]:out.append('%s Battle: %s'%(role,entity))
        if 'server' in row:out.append('%s registered racer counts: %s'%(role,row['server'].get('population',{}).get('counts')))
        if 'unavailable' in row:out.append('%s incomplete: %s'%(role,row['unavailable']))
    return out+['Read-only point-in-time snapshot. Raw mode fields need native type confirmation; flags alone do not prove control or victory.']


def helper_counters(directory):
    """Counters from the current native RAM helpers; never a gameplay verdict."""
    rows = [r for r in jsonl(directory / 'events.jsonl') if isinstance(r.get('counters'), dict)]
    if not rows:
        return ['no counter samples; helper status %s' % status(directory)]
    last = rows[-1]['counters']
    result = ['counter snapshots %d; helper status %s' % (len(rows), status(directory)),
              'last: ' + ', '.join('%s=%s' % (k, v) for k, v in last.items())]
    if directory.name.startswith('host-first-test-'):
        result.append('HOST matches observed: %s; native fallbacks: %s' % (last.get('host_hits', '?'), last.get('native', '?')))
    elif directory.name.startswith('guest-vehicle-test-'):
        result.append('extra-human entries %s, story entries %s, spawn requests %s' %
                      (last.get('enters', '?'), last.get('story_enters', '?'), last.get('arms', '?')))
    elif directory.name.startswith('host-difficulty-test-'):
        result.append('forced values %s; server choice %s; received client value %s' %
                      (last.get('forced', '?'), last.get('host_value', '?'), last.get('last_client_value', '?')))
    return result + ['Counter activity is not proof of visible scenes, control, difficulty or a completed mission.']


def ant_events(directory):
    rows = jsonl(directory / 'events.jsonl')
    events = [r for r in rows if r.get('site') in ('camera', 'controller')]
    counts = collections.Counter((r['site'], str(r.get('event'))) for r in events)
    callers = collections.Counter((r['site'], str(r.get('caller'))) for r in events)
    starts = [r for r in events if r['site'] == 'controller' and str(r.get('event')).lower() == '0xdc0efa5']
    lost = sum(r.get('lost', 0) for r in rows if isinstance(r.get('lost'), int))
    result = ['events %d; lost ring entries %d; helper status %s' % (len(events), lost, status(directory)),
              'by site/event: ' + ', '.join('%s/%s=%d' % (site, event, count) for (site, event), count in counts.most_common(12)),
              'controller Start observed %d; Bit15 true %d' % (len(starts), sum(r.get('flag_bit15') is True for r in starts)),
              'callers: ' + ', '.join('%s/%s=%d' % (site, caller, count) for (site, caller), count in callers.most_common(8))]
    identities = collections.Counter((r['site'], r.get('data_guid'), str(r.get('event'))) for r in events if r.get('data_guid'))
    if identities:
        ranked = sorted(identities.items(), key=lambda row: (row[0][0] != 'controller', -row[1]))[:12]
        result.extend('authored %s %s event %s: %d' % (site, guid, event, count)
                      for (site, guid, event), count in ranked)
        catalog = OUT / 'qte-controller-routes-20261109.json'
        if catalog.is_file():
            try:
                document = json.loads(catalog.read_text(encoding='utf-8'))
                labels = collections.defaultdict(set)
                for target in document.get('targets', []):
                    labels[target['guid']].add(target['asset'])
                for guid in dict.fromkeys(key[1] for key, _ in identities.most_common(10)):
                    if labels.get(guid):
                        result.append('GUID %s authored in %s' % (guid, ', '.join(sorted(labels[guid])[:3])))
                result.append('Authored links are hints; an instance GUID does not establish which runtime prefab copy emitted the event.')
            except (OSError, ValueError, KeyError) as exc:
                result.append('Authored labels unavailable: %s' % exc)
    return result + ['Start delivery alone does not prove actor binding, camera correctness or QTE completion; no events is not a global absence proof.']


def qte_roles(path):
    document = json.loads(path.read_text(encoding='utf-8-sig'))
    rows = []
    for target in document.get('targets', []):
        state = target.get('state', {})
        rows.append('%s: id=%s name=%s controllable=%s type=%s challenge=%s' %
                    (target['role'], state.get('player_id'), target.get('local_name'),
                     target.get('controllable'), target.get('controllable_vtable'), state.get('challenge')))
        if 'humans' in target:
            rows.append('SERVER real humans: %s' % target['humans'])
        if target.get('unavailable'):
            rows.append('%s unavailable: %s' % (target['role'], target['unavailable']))
    return rows


def subworld_events(directory):
    """Claude 11.11.: 10.4 chain per client - SubWorld handler E115E0 events plus the ANT probe lines."""
    rows = jsonl(directory / 'events.jsonl')
    world = [r for r in rows if r.get('site') == 'subworld']
    counts = collections.Counter(str(r.get('event')).lower() for r in world)
    enter = [r for r in world if str(r.get('event')).lower() == '0x1a8be1ad']
    starts = [r for r in rows if r.get('site') == 'controller' and str(r.get('event')).lower() == '0xdc0efa5']
    first = lambda items: items[0].get('time', '?') if items else '-'
    out = ['subworld events %d: %s' % (len(world), ', '.join('%s=%d' % kv for kv in counts.most_common(8)) or 'none'),
           'enter 0x1A8BE1AD %d (load already requested %d, first %s); ANT controller Start %d (first %s)'
           % (len(enter), sum(r.get('load_requested') is True for r in enter), first(enter), len(starts), first(starts))]
    instances = collections.defaultdict(collections.Counter)
    for row in world:
        instances[str(row.get('this'))][str(row.get('event')).lower()] += 1
    for address, events in sorted(instances.items())[:10]:
        out.append('subworld instance %s: %s' % (address, ', '.join('%s=%d' % item for item in events.most_common(8))))
    if not world:
        out.append('VERDICT: no SubWorld event reached this client -> chain stops before the client (server/network side).')
    elif not enter:
        out.append('VERDICT: SubWorld events but no enter 0x1A8BE1AD -> the 10.4 scene trigger did not reach this client.')
    elif not starts:
        out.append('VERDICT: enter reached this client but no ANT Start -> chain stops between OnLoaded/Init and the ANT controller.')
    else:
        out.append('VERDICT: enter and ANT Start both reached this client.')
    return out + ant_events(directory)[:1] + ['Compare HOST and GUEST folders of the same run; one client alone proves nothing.']


KINDS = (('qte-role-state-*.json', qte_roles), ('host-first-test-*', helper_counters), ('guest-vehicle-test-*', helper_counters),
         ('subworld-event-probe-*', subworld_events),
         ('host-difficulty-test-*', helper_counters), ('qte-hud-scope-test-*', helper_counters),
         ('ant-event-probe-*', ant_events), ('ant-event-identity-probe-*', ant_events),
         ('cinematic-state-*.json',cinematic_state),('battle-state-*.json',battle_state),('story-finish-flow-*',story_finish_flow),('windows-game-faults-*.json',windows_game_faults),('pause-hud-state-*.json',pause_hud),('bridge-exception-*', native_faults), ('grid-slots-*', grid_slots), ('garage-selection-*', garage), ('player-race-progress-*', progress),
         ('missing-lookup-*', missing), ('nitro-flames-*.json', nitro), ('vehicle-requests-*.json', vehicle_requests))


KINDS=(('helicopter-fault-*',native_faults),('bundle-owner-preflight-*.json',bundle_owner_preflight),('bundle-owner-test-*',bundle_owner_test),('owner-lookup-*',owner_lookup),('registry-lookup-*',owner_lookup),('fallback-lookup-*',owner_lookup))+KINDS


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


def cutscene_ai_summary(directory):
    last={}
    for path in sorted(directory.glob('cutscene-ai-*.jsonl'))[-4:]:
        for row in jsonl(path):
            for role in ('HOST','GAST'):
                if isinstance(row.get(role),dict):last[role]=row[role]
    out=[]
    for role,stats in sorted(last.items()):
        out.append('%s: ANT camera activations=%s releases=%s active=%s; AI on requests=%s off requests=%s; controllers restored=%s' %
                   (role,stats.get('ant_starts','not recorded'),stats.get('ant_stops','not recorded'),
                    stats.get('ant_camera_count','not recorded'),stats.get('ai_on','?'),stats.get('ai_off','?'),stats.get('restored','?')))
    states=sorted(directory.glob('cutscene-ai-*.state.json'))
    if states:
        try:
            state=json.loads(states[-1].read_text(encoding='utf-8-sig'))
            out.append('cleanup acknowledgments: '+json.dumps(state.get('restored',{}),sort_keys=True))
        except (ValueError,OSError,AttributeError):out.append('Cleanup state not yet readable; no acknowledgment inferred.')
    if not last:out.append('No recorded cutscene counters; no success inferred.')
    return out+['Counters do not prove visible camera/world, QTE progress or player control.']


def server_ai_guard_summary(path):
    try:
        data=json.loads(path.read_text(encoding='utf-8-sig'))
        if not isinstance(data,dict):raise ValueError('not an object')
    except (ValueError,OSError):return ['AI guard journal not yet readable; no success inferred.']
    out=['Exact bad AI getter interceptions: %s; restored=%s; cleanup=%s' %
            (data.get('hits','not recorded'),data.get('restored','not acknowledged'),data.get('cleanup','-')),
            'NULL fallback only; neither root cause nor correct race/AI behavior is proven.']
    if data.get('last_context'):out.append('Register context at interception: '+json.dumps(data['last_context'],sort_keys=True))
    for name,raw in data.get('heap_context_at_poll',{}).items():
        try:
            import struct
            values=struct.unpack('<8I',bytes.fromhex(raw))
            out.append('Later heap snapshot %s: %s (may already be reused)'%(name,[hex(v) for v in values]))
        except (ValueError,TypeError,struct.error):out.append('Later heap snapshot '+name+': unavailable')
    return out


def ant_start_relay_summary(directory):
    path=directory/'state.json'
    try:
        doc=json.loads(path.read_text(encoding='utf-8-sig'))
        if not isinstance(doc,dict):raise ValueError('not an object')
    except (ValueError,OSError):return ['Relay state not readable; no delivery inferred.']
    out=['ANT relay status=%s source=%s receiver=%s'%(doc.get('status'),doc.get('source'),doc.get('receiver'))]
    if doc.get('discovery'):out.append('Discovery: '+json.dumps(doc['discovery'],sort_keys=True))
    for row in doc.get('events',[])[:8]:
        source=row.get('source_event',{})
        out.append('Asset %s event %s: %s; matches=%s'%(source.get('guid'),hex(source.get('event',0)),
                   row.get('receiver_result'),row.get('matches','-')))
        if row.get('scan'):out.append('  bounded external discovery '+json.dumps(row['scan'],sort_keys=True))
    if doc.get('error'):out.append('Error: '+str(doc['error']))
    out.append('Restore: '+json.dumps(doc.get('restored',{}),sort_keys=True))
    return out+['Native handler return is not proof of actor/camera visibility, synchronized input or QTE success.']


def frida_ant_controller_summary(path):
    rows=jsonl(path);out=['Historical controller rows: %s'%len(rows)]
    out.append('Ready roles: '+str(sorted({r.get('role') for r in rows if r.get('site')=='ready'})))
    for row in [r for r in rows if r.get('site')=='error'][:2]:out.append('Observer error: '+str(row.get('detail'))[:240])
    for role in ('HOST','GAST'):
        starts=[r for r in rows if r.get('role')==role and r.get('site')=='controller' and str(r.get('ev')).lower() in ('dc0efa5','0xdc0efa5')]
        out.append('%s Start calls=%s'%(role,len(starts)))
        for row in starts[:2]:
            raw=row.get('ev_hex')
            try:
                import struct
                words=struct.unpack('<6I',bytes.fromhex(raw))
                out.append('  event words [0..5]: '+str([hex(x) for x in words]))
                local_bus=row.get('bus',row.get('data_proxy'))
                if local_bus is not None:
                    out.append('  event+8 equals controller+10: '+str(words[2]==local_bus))
            except (ValueError,TypeError,struct.error):out.append('  event prefix not captured')
            field='authored_data(+14)' if ('bus' in row or 'data_proxy' in row) else 'legacy_data_proxy(+10)'
            out.append('  controller=%s flags=%s %s=%s'%(row.get('self'),row.get('flags'),field,row.get('data')))
        binds=[r for r in rows if r.get('role')==role and r.get('site')=='controller_binding']
        out.append('%s controller bindings=%s'%(role,len(binds)))
        for row in binds[:2]:
            out.append('  owner=%s holder=%s old=%s desired=%s saved=%s end_behavior=%s'%
                       tuple(row.get(k) for k in ('owner','holder','old_controller','desired_controller','saved_controller','end_behavior')))
    cleanup=[r for r in rows if r.get('site')=='cleanup']
    if cleanup:out.append('Timed detach reports: '+str([(r.get('role'),r.get('detached')) for r in cleanup]))
    return out+['Word0 is a native event vtable/type header, not a proven sender pointer. Words beyond the base header are not a proven payload. No event/class semantics inferred from raw words alone.']


def qte_role_snapshot(path):
    doc=json.loads(path.read_text(encoding='utf-8-sig'))
    out=['QTE role snapshot: read_only=%s'%doc.get('read_only')]
    for row in doc.get('targets',[]):
        role=row.get('role','?');candidate=row.get('candidate') or {}
        out.append('%s local=%s controllable=%s unavailable=%s'%(role,row.get('local_name'),row.get('controllable'),row.get('unavailable')))
        if candidate.get('kind')=='local_actor':
            out.append('%s actor getters: native=%s local=%s'%(role,candidate.get('native_getters'),candidate.get('local_selections')))
        elif candidate.get('kind')=='ready_barrier':
            out.append('WITHDRAWN experiment: animation milestones were misclassified as readiness. Do not install that candidate.')
            out.append('%s readiness: stable=%s humans=%s counters=%s'%(role,candidate.get('stable'),candidate.get('human_count'),candidate.get('counters')))
            for e in candidate.get('entries',[]):
                out.append('  source group=%s arrived mask=%s closed=%s'%(e.get('source_group'),e.get('arrived_mask'),e.get('closed')))
        elif candidate.get('kind')=='host_milestones':
            out.append('%s host milestones: stable=%s humans=%s verified_host=%s counters=%s'%(role,candidate.get('stable'),candidate.get('human_count'),candidate.get('verified_host'),candidate.get('counters')))
            for e in candidate.get('entries',[]):
                out.append('  source group=%s host accepted=%s closed=%s'%(e.get('source_group'),bool(e.get('arrived_mask',0)&1),e.get('closed')))
    return out+['Resource Out/local-link counters do not prove world, camera, input or whole-QTE success.']


KINDS=(('qte-role-state-*.json',qte_role_snapshot),('ant-controller-*.jsonl',frida_ant_controller_summary),('ant-start-relay-*',ant_start_relay_summary),('cutscene-ai-*',cutscene_ai_summary),('server-ai-guard-*.json',server_ai_guard_summary))+KINDS


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--all', type=int, default=1, metavar='N')
    p.add_argument('--physics-dump', type=Path, help='Bounded Havok64112F context from an existing local game dump')
    p.add_argument('--native-dump', type=Path, help='Bounded native exception/register summary from an existing dump')
    p.add_argument('--qte-spawn-dump', type=Path, help='Local actor-bus selection in already captured dump memory; no live probes')
    p.add_argument('--dump-report', type=Path, help='Optional derived QTE dump report JSON')
    p.add_argument('--directory', type=Path, help='Summarize only one recorder directory instead of historical unrelated captures')
    p.add_argument('--launcher-logs', type=Path, help='Bounded opt-in per-player launcher diagnostics; no game-memory data')
    args=p.parse_args()
    if args.launcher_logs:
        print('\n'.join(launcher_diagnostics(args.launcher_logs)))
    elif args.directory:
        if not args.directory.exists():p.error('Recorder path does not exist')
        import fnmatch
        fn=next((fn for pattern,fn in KINDS if fnmatch.fnmatch(args.directory.name,pattern)),None)
        if fn is None:p.error('Unknown recorder directory kind')
        print('\n'.join(fn(args.directory)))
    elif args.qte_spawn_dump:
        from inspect_qte_spawn_dump import summarize as summarize_dump
        lines, report=summarize_dump(args.qte_spawn_dump)
        if args.dump_report:
            args.dump_report.write_text(json.dumps(report,indent=2),encoding='utf-8')
        print('\n'.join(lines))
    elif args.native_dump:
        print('\n'.join(native_dump(args.native_dump)))
    elif args.physics_dump:
        print('\n'.join(physics_dump(args.physics_dump)))
    else:print('\n'.join(summarize(args.all)))


def launcher_diagnostics(directory):
    """Only the three bounded, known log files. Never equate absent logs with success."""
    rows=[];bad=0;oversized=0
    for name in ('events.2.jsonl','events.1.jsonl','events.jsonl'):
        path=directory/name
        if not path.is_file():continue
        if path.stat().st_size>3*1024*1024:
            oversized+=1;continue
        with path.open(encoding='utf-8-sig',errors='replace') as stream:
            for index,line in enumerate(stream):
                if index>=30000:break
                if len(line)>16384:bad+=1;continue
                try:row=json.loads(line)
                except ValueError:bad+=1;continue
                if not isinstance(row,dict) or row.get('Type') not in ('sample','session-ended'):
                    bad+=1;continue
                rows.append(row)
    if not rows:
        return ['Launcher diagnostics: no readable samples. Logging may be disabled.',
                f'Invalid rows={bad}, oversized files={oversized}. No gameplay or crash verdict.']
    samples=[r for r in rows if r['Type']=='sample']
    last=rows[-1]
    out=[f"Launcher diagnostics: {last.get('Nickname','?')} ({last.get('Role','?')}), version {last.get('Version','?')}",
         f'Samples={len(samples)}, invalid rows={bad}, oversized files={oversized}']
    memory=[r['WorkingSetBytes'] for r in samples if type(r.get('WorkingSetBytes')) in (int,float) and r['WorkingSetBytes']>=0]
    if memory:out.append('Peak sampled working set: %.1f MiB'%(max(memory)/1024**2))
    peers=collections.Counter(r.get('PeerStatus','unknown') for r in samples)
    if peers:out.append('Launcher control channel: '+', '.join(f'{k}={v}' for k,v in sorted(peers.items(),key=lambda x:str(x[0]))))
    ended=[r for r in rows if r['Type']=='session-ended']
    if ended:
        code=ended[-1].get('ExitCode')
        if type(code) is int:
            unsigned=code&0xffffffff
            out.append('Game exit code: %d (0x%08X)'%(code,unsigned))
            if unsigned:out.append('Nonzero process exit; this log does not establish the cause.')
        else:out.append('No process exit code captured; helper may have ended before the game.')
    else:out.append('No end record captured; this alone is not proof of a crash.')
    out.append('CPU/RAM/launcher status only. No native race, QTE, camera, FPS or GPU verdict.')
    return out


def native_dump(path):
    from inspect_cinematic_crash import inspect
    report=inspect(path)
    module=report.get('fault_module') or {}
    out=['dump %s fault %s exception %s module %s+%s'%(path.name,report['address'],report['exception'],module.get('name'),module.get('offset')),
         'access parameters: %s'%report.get('exception_parameters'),
         'registers: %s'%report.get('registers')]
    out.append('stack words (first24, not a verified trace): %s'%report.get('stack',[])[:24])
    if report['address']=='0x2572b58' and report.get('stack',[None])[0]=='0x127bc0e':
        from minidump_memory import DumpMemory
        import struct
        memory=DumpMemory(path.read_bytes())
        native=memory.optional(0x127BC07,7)
        out.append('AI getter call-site bytes: '+(native.hex() if native else 'not captured'))
        if native is None or native==bytes.fromhex('8b018b5010ffd2'):
            for reg,size in (('ecx',32),('eax',32),('esi',0x80)):
                address=int(report['registers'][reg],16)
                raw=memory.optional(address,size)
                if raw:
                    offset=0x6C if reg=='esi' else 0
                    words=struct.unpack('<%dI'%((len(raw)-offset)//4),raw[offset:])
                    out.append('Candidate AI context %s%s words: %s'%(reg,'+6C' if offset else '',[hex(x) for x in words[:8]]))
            out.append('Receiver type/lifetime and NULL fallback behavior remain unresolved; missing code bytes are not a verified runtime call-site signature.')
    if report['address']=='0xb1496e':
        import struct
        from minidump_memory import DumpMemory
        memory=DumpMemory(path.read_bytes());frame=int(report['registers']['ebp'],16)
        raw=memory.optional(frame,20)
        if raw:
            parent,caller,output,delta_bits,params=struct.unpack('<5I',raw)
            delta=struct.unpack('<f',struct.pack('<I',delta_bits))[0]
            out.append('ANT ActorController::Update negative DeltaT assertion; argument=%r bits=%s caller=%s params=%s'%(delta,hex(delta_bits),hex(caller),hex(params)))
            for _ in range(3):
                raw=memory.optional(parent,8) if frame<parent<frame+65536 else None
                if raw is None:break
                frame=parent;parent,returned=struct.unpack('<II',raw)
                out.append('frame-pointer candidate return '+hex(returned))
    return out+['Minidump is historical evidence; exception site alone does not establish the cause or mission.']


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
