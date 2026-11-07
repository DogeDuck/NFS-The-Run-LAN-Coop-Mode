"""Build local two-player test package: scripts and deltas only, no game binaries."""
from pathlib import Path
import base64
import argparse
import hashlib
import json
import shutil
import zipfile
import ast
from patch_test_candidate import build_server, build_client
from bundle_coop_addons import bundle as bundle_addons

ROOT = Path(__file__).resolve().parent
GAME = Path(r'X:\EA Games\Need for Speed The Run\Need for Speed The Run')
VERSION='0.5-TEST'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def copy_local_sources(destination, entries):
    """Ship current patch sources and local imports, never binaries or backups."""
    pending=list(entries);seen=set()
    while pending:
        name=pending.pop()
        if name in seen:continue
        source=ROOT/name
        if not source.is_file():raise ValueError('Missing package source: '+name)
        seen.add(name)
        tree=ast.parse(source.read_text(encoding='utf-8-sig'))
        for node in ast.walk(tree):
            modules=[a.name for a in node.names] if isinstance(node,ast.Import) else [node.module] if isinstance(node,ast.ImportFrom) and node.module else []
            for module in modules:
                local=module.split('.')[0]+'.py'
                if (ROOT/local).is_file():pending.append(local)
        destination.mkdir(exist_ok=True)
        shutil.copyfile(source,destination/name)
    return sorted(seen)


def delta(name, before, after):
    if len(after) < len(before):
        raise ValueError('Shrinking deltas are unsupported')
    changes = []
    for block in range(0, len(before), 4096):
        end = min(block + 4096, len(before))
        if before[block:end] == after[block:end]:
            continue
        cursor = block
        while cursor < end:
            if before[cursor] == after[cursor]:
                cursor += 1
                continue
            start = cursor
            while cursor < end and before[cursor] != after[cursor]:
                cursor += 1
            changes.append(dict(Offset=start, Before=base64.b64encode(before[start:cursor]).decode(),
                                After=base64.b64encode(after[start:cursor]).decode()))
    return dict(FileName=name, OriginalSha256=sha(before), PatchedSha256=sha(after),
                OriginalLength=len(before), PatchedLength=len(after), Changes=changes,
                Append=base64.b64encode(after[len(before):]).decode())


def apply(before, patch):
    if sha(before) != patch['OriginalSha256']:
        raise ValueError('Wrong delta baseline')
    out = bytearray(before)
    for run in patch['Changes']:
        start = run['Offset']
        old, new = base64.b64decode(run['Before']), base64.b64decode(run['After'])
        if out[start:start + len(old)] != old or len(old) != len(new):
            raise ValueError('Bad delta signature')
        out[start:start + len(new)] = new
    out += base64.b64decode(patch['Append'])
    if len(out) != patch['PatchedLength'] or sha(out) != patch['PatchedSha256']:
        raise ValueError('Delta reconstruction failed')
    return bytes(out)


def reverse_apply(after,patch):
    """Recover exact research input in memory; never rewrite an installation."""
    if len(after)!=patch['PatchedLength'] or sha(after)!=patch['PatchedSha256']:
        raise ValueError('Wrong reverse-delta input')
    length=patch['OriginalLength']
    if not 0<=length<=len(after) or after[length:]!=base64.b64decode(patch['Append']):
        raise ValueError('Reverse append mismatch')
    out=bytearray(after[:length])
    for run in patch['Changes']:
        start=run['Offset'];old=base64.b64decode(run['Before']);new=base64.b64decode(run['After'])
        if start<0 or start+len(old)>length or len(old)!=len(new) or out[start:start+len(new)]!=new:
            raise ValueError('Reverse delta signature mismatch')
        out[start:start+len(old)]=old
    if sha(out)!=patch['OriginalSha256'] or apply(bytes(out),patch)!=after:
        raise ValueError('Reverse-delta reconstruction failed')
    return bytes(out)


def research_baseline(current,patch,additional_patches=()):
    if sha(current)==patch['OriginalSha256']:return current
    for candidate in additional_patches:
        if (candidate['OriginalSha256']!=patch['OriginalSha256'] or
                candidate['OriginalLength']!=patch['OriginalLength']):
            raise ValueError('Candidate uses a different research baseline')
        if sha(current)==candidate['PatchedSha256']:
            return reverse_apply(current,candidate)
    return reverse_apply(current,patch)


def installed_research_baseline(current,stem):
    """Accept the verified installed DEV candidate without reverting disk files."""
    if stem not in ('client','server'):raise ValueError('Unknown binary role')
    relative=f'patches/{stem}-research-upgrade.json'
    previous=json.loads((ROOT/'release/TheRun-Coop-v0.3-TEST'/relative).read_text(encoding='utf-8-sig'))
    candidate_path=ROOT/'outputs/TheRun-Coop-v0.4-DEV-final'/relative
    candidates=[]
    if candidate_path.is_file():
        candidate=json.loads(candidate_path.read_text(encoding='utf-8-sig'))
        expected={'client':'2cb4570c34e46cc74ccded44f8f38338c12a0edfbb33a74572b72fc6e11ad249',
                  'server':'22f1604cc40643dbcb18154cda3da627a63f0b34a4dfdfd7631ad99c9a81b768'}
        if candidate['PatchedSha256']!=expected[stem]:raise ValueError('Unrecognized DEV delta')
        candidates.append(candidate)
    v05_path=ROOT/f'outputs/TheRun-Coop-v0.5-TEST/{relative}'
    if v05_path.is_file():
        candidate=json.loads(v05_path.read_text(encoding='utf-8-sig'))
        approved={'client':'2cb4570c34e46cc74ccded44f8f38338c12a0edfbb33a74572b72fc6e11ad249',
                  'server':'4afb76c21d08439778dba038ad787618f752aa3c639a18a07a5b1672c0263c9d'}
        if candidate['PatchedSha256']!=approved[stem]:raise ValueError('Unrecognized v0.5 delta')
        candidates.append(candidate)
    v06_path=ROOT/f'outputs/TheRun-Coop-v0.6-TEST-Final/{relative}'
    if v06_path.is_file():
        candidate=json.loads(v06_path.read_text(encoding='utf-8-sig'))
        approved={'client':'95ba75bb168b2ffc38c4539e2287d8be31dcc55d2001d53c7c7a60696c839f14','server':'4afb76c21d08439778dba038ad787618f752aa3c639a18a07a5b1672c0263c9d'}
        if candidate['PatchedSha256']!=approved[stem]:raise ValueError('Unrecognized v0.6 delta')
        candidates.append(candidate)
    unload_path=ROOT/f'outputs/TheRun-Coop-v0.6-UNLOAD-ACK-CANDIDATE/{relative}'
    if unload_path.is_file():
        candidate=json.loads(unload_path.read_text(encoding='utf-8-sig'))
        approved={'client':'8140947e9b11cdfa4cac5d3c7f05820a96246f447399ed6adc6187355910d5c6',
                  'server':'4afb76c21d08439778dba038ad787618f752aa3c639a18a07a5b1672c0263c9d'}
        if candidate['PatchedSha256']!=approved[stem]:raise ValueError('Unrecognized unload-ack delta')
        candidates.append(candidate)
    combined_path=ROOT/f'outputs/TheRun-Coop-v0.6-HUD-PAUSE-SLOT-CANDIDATE/{relative}'
    if combined_path.is_file():
        candidate=json.loads(combined_path.read_text(encoding='utf-8-sig'))
        approved={'client':'4afc9b078f7c70044ab48c05cc3327dcbfb05ef489aab190c5a6640e8043ad29',
                  'server':'aeaf9c120b02a158cd3f52554fbfa1f2f0f18507da43d9c4aa00225c845249ff'}
        if candidate['PatchedSha256']!=approved[stem]:raise ValueError('Unrecognized HUD/pause/slot delta')
        candidates.append(candidate)
    return research_baseline(current,previous,candidates)


def main():
    global VERSION
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'release/TheRun-Coop-v0.5-TEST')
    parser.add_argument('--validation',type=Path,help='Optional completed offline test report to include')
    parser.add_argument('--team-finish-candidate',action='store_true',help='Build unverified dynamic team-result candidate, never install automatically')
    parser.add_argument('--version',choices=['0.6-CANDIDATE','0.6-TEST','0.7-TEST','0.7.1-TEST'],default='0.6-CANDIDATE',help='Version for the opt-in team-result build')
    parser.add_argument('--pause-ai',action='store_true',help='Opt-in DRAFT client: AI drives while the LAN pause menu is open (PAUSE-KI-2026-11-04.md); not gameplay verified')
    parser.add_argument('--pause-ai-no-state-guard',action='store_true',help='With --pause-ai: do not skip when entity+D0 is set (use if live SKIPPED_AI keeps rising)')
    parser.add_argument('--pause-ai-hud-state',action='store_true',help='With --pause-ai: use HUD PauseVisibilty transitions instead of the LAN-inactive ClientPauseGameMessage hook')
    parser.add_argument('--coop-hud',action='store_true',help='Opt-in native Career leaderboard in LAN Story HUD, suppress Story timer and Autolog stage-leader panel; unverified in game')
    parser.add_argument('--battle-team-finish',action='store_true',help='Opt-in DRAFT: BattleRace finishes every human together (ELIMINATOR-FINISH-2026-11-04.md); not gameplay verified')
    parser.add_argument('--gas-ack-timeout',action='store_true',help='Opt-in DRAFT: server continues gas station bundle queue when client acks never arrive; not gameplay verified')
    parser.add_argument('--gas-unload-ack',action='store_true',help='Opt-in client candidate: send native bundle-unloaded acknowledgement after E55260 completes; server timeout remains disabled')
    parser.add_argument('--reserve-authored-slots',action='store_true',help='Opt-in server slot reservation for the second human (SPAWNER-SLOT-2026-11-04.md); not gameplay verified')
    args=parser.parse_args()
    if args.pause_ai_hud_state and not args.pause_ai:
        parser.error('--pause-ai-hud-state requires --pause-ai')
    if args.version in ('0.7-TEST','0.7.1-TEST'):
        if not (args.team_finish_candidate and args.pause_ai and args.pause_ai_hud_state and args.pause_ai_no_state_guard and args.coop_hud and args.reserve_authored_slots):
            parser.error('v0.7 requires the reviewed combined feature set')
        if args.gas_ack_timeout or args.gas_unload_ack or args.battle_team_finish:
            parser.error('Unverified gas/battle experiments are not part of v0.7')
    if args.gas_unload_ack and args.gas_ack_timeout:
        parser.error('--gas-unload-ack cannot be combined with the unsafe server --gas-ack-timeout')
    if args.gas_unload_ack and not args.team_finish_candidate:
        parser.error('--gas-unload-ack requires --team-finish-candidate to retain the v0.6 baseline')
    if args.gas_unload_ack and args.output==ROOT/'release/TheRun-Coop-v0.5-TEST':
        args.output=ROOT/'outputs/TheRun-Coop-v0.6-UNLOAD-ACK-CANDIDATE'
    if args.reserve_authored_slots and args.output==ROOT/'release/TheRun-Coop-v0.5-TEST' and not args.team_finish_candidate:
        args.output=ROOT/'outputs/TheRun-Coop-SLOT-CANDIDATE'
    if args.team_finish_candidate:
        VERSION=args.version
        if args.output==ROOT/'release/TheRun-Coop-v0.5-TEST':
            args.output=ROOT/'outputs/TheRun-Coop-v0.6-CANDIDATE'
    validation=None
    if args.validation:
        validation=json.loads(args.validation.read_text(encoding='utf-8'))
        if validation.get('successful') is not True or validation.get('failures')!=0 or validation.get('errors')!=0:
            raise ValueError('Offline test report is not successful')
    source = ROOT / 'release/TheRun-Coop-Prototype-v0.1'
    destination = args.output.resolve()
    if destination.exists():
        raise ValueError('Test package already exists; inspect before replacing')
    client_original = (ROOT / 'backups/Need For Speed The Run.exe.lan-before-road-reset').read_bytes()
    server_original = (ROOT / 'backups/NFSTR_Server.exe.headless-original').read_bytes()
    v03={stem:json.loads((ROOT/f'release/TheRun-Coop-v0.3-TEST/patches/{stem}-research-upgrade.json').read_text(encoding='utf-8-sig')) for stem in ('client','server')}
    client_base=installed_research_baseline((GAME/'Need For Speed The Run.exe').read_bytes(),'client')
    client, _, client_report = build_client(client_base)
    if args.team_finish_candidate:
        from patch_team_finish_dynamic import build as add_team_finish
        client, _, team_report=add_team_finish(client)
        client_report.update(patched_sha256=sha(client),team_result=team_report)
    if args.pause_ai:
        # Opt-in DRAFT (PAUSE-KI-2026-11-04.md): native AI switch while the LAN pause menu is open.
        from patch_pause_ai import build as add_pause_ai
        client, _, pause_report=add_pause_ai(client,not args.pause_ai_no_state_guard,args.pause_ai_hud_state)
        client_report.update(patched_sha256=sha(client),pause_ai=pause_report)
    if args.coop_hud:
        from patch_coop_hud import build as add_coop_hud
        client, _, hud_report=add_coop_hud(client)
        client_report.update(patched_sha256=sha(client),coop_hud=hud_report)
    if args.gas_unload_ack:
        from patch_gas_unload_ack import build as add_gas_unload_ack
        client, _, unload_report=add_gas_unload_ack(client)
        client_report.update(patched_sha256=sha(client),gas_unload_ack=unload_report)
    server_base=installed_research_baseline((GAME/'NFSTR_Server.exe').read_bytes(),'server')
    server, _, report = build_server(server_base,args.reserve_authored_slots,args.battle_team_finish,args.gas_ack_timeout)
    # Validate every patch in memory BEFORE creating the package.
    patches = {}
    for stem, name, original, target in [('client', 'Need For Speed The Run.exe', client_original, client),
                                          ('server', 'NFSTR_Server.exe', server_original, server)]:
        baseline_patch = json.loads((source / f'patches/{stem}.json').read_text(encoding='utf-8-sig'))
        old_release = apply(original, baseline_patch)
        patches[stem] = delta(name, original, target)
        patches[stem + '-upgrade'] = delta(name, old_release, target)
        research_base = server_base if stem == 'server' else client_base
        patches[stem + '-research-upgrade'] = delta(name, research_base, target)
        previous=apply(research_base,v03[stem])
        patches[stem+'-v0_3-upgrade']=delta(name,previous,target)
        public_v04=ROOT/f'outputs/TheRun-Coop-v0.4-TEST-Addons-Final/patches/{stem}-research-upgrade.json'
        v04_patch=json.loads(public_v04.read_text(encoding='utf-8-sig'))
        v04_expected={'client':'2cb4570c34e46cc74ccded44f8f38338c12a0edfbb33a74572b72fc6e11ad249',
                      'server':'22f1604cc40643dbcb18154cda3da627a63f0b34a4dfdfd7631ad99c9a81b768'}
        if v04_patch['PatchedSha256']!=v04_expected[stem]:raise ValueError('Unrecognized public v0.4 baseline')
        previous_v04=apply(research_base,v04_patch)
        patches[stem+'-v0_4-upgrade']=delta(name,previous_v04,target)
        v05_patch=json.loads((ROOT/f'outputs/TheRun-Coop-v0.5-TEST/patches/{stem}-research-upgrade.json').read_text(encoding='utf-8-sig'))
        approved_v05={'client':'2cb4570c34e46cc74ccded44f8f38338c12a0edfbb33a74572b72fc6e11ad249','server':'4afb76c21d08439778dba038ad787618f752aa3c639a18a07a5b1672c0263c9d'}
        if v05_patch['PatchedSha256']!=approved_v05[stem]:raise ValueError('Unrecognized public v0.5 baseline')
        previous_v05=apply(research_base,v05_patch)
        patches[stem+'-v0_5-upgrade']=delta(name,previous_v05,target)
        # Installed v0.6 TEST (client 95BA75BB, server 4AFB76C2) must upgrade without the LAN base package.
        v06_patch=json.loads((ROOT/f'outputs/TheRun-Coop-v0.6-TEST-Final/patches/{stem}-research-upgrade.json').read_text(encoding='utf-8-sig'))
        approved_v06={'client':'95ba75bb168b2ffc38c4539e2287d8be31dcc55d2001d53c7c7a60696c839f14','server':'4afb76c21d08439778dba038ad787618f752aa3c639a18a07a5b1672c0263c9d'}
        if v06_patch['PatchedSha256']!=approved_v06[stem]:raise ValueError('Unrecognized public v0.6 baseline')
        previous_v06=apply(research_base,v06_patch)
        patches[stem+'-v0_6-upgrade']=delta(name,previous_v06,target)
        for key, patch in list(patches.items()):
            if key.startswith(stem):
                start = original if key == stem else research_base if key.endswith('research-upgrade') else previous if key.endswith('v0_3-upgrade') else previous_v04 if key.endswith('v0_4-upgrade') else previous_v05 if key.endswith('v0_5-upgrade') else previous_v06 if key.endswith('v0_6-upgrade') else old_release
                if apply(start, patch) != target:
                    raise ValueError('Roundtrip mismatch')
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns('package-manifest.json', 'validation.json', 'Start-Guest-voreingestellt.cmd'))
    for name, patch in patches.items():
        (destination / f'patches/{name}.json').write_text(json.dumps(patch, separators=(',', ':')), encoding='utf-8')
    installer = destination / 'Install-Coop.ps1'
    text = installer.read_text(encoding='utf-8-sig')
    marker = "$support=Get-Content -LiteralPath"
    insert = """# Accept upgrades from the previous release and the verified local test baseline.
$deltas=@(foreach($entry in $deltas){
    $selected=$entry
    $current=Join-Path $game $entry.FileName
    if(Test-Path -LiteralPath $current){
        $hash=Get-CoopFileHash $current
        $stem=if($entry.FileName -eq 'NFSTR_Server.exe'){'server'}else{'client'}
        foreach($suffix in @('-upgrade','-research-upgrade','-v0_3-upgrade','-v0_4-upgrade','-v0_5-upgrade','-v0_6-upgrade')){
            $candidate=Join-Path $PSScriptRoot ("patches\\"+$stem+$suffix+'.json')
            if(Test-Path -LiteralPath $candidate){
                $upgrade=Get-Content -LiteralPath $candidate -Raw|ConvertFrom-Json
                if($hash -eq $upgrade.OriginalSha256){$selected=$upgrade;break}
            }
        }
    }
    $selected
})
"""
    text = text.replace(marker, insert + marker, 1).replace("Version='0.1'", "Version='"+VERSION+"'")
    installer.write_text(text, encoding='utf-8-sig')
    start = destination / 'Start-Coop.ps1'
    start.write_text(start.read_text(encoding='utf-8-sig').replace("Version='0.1'", "Version='"+VERSION+"'"), encoding='utf-8-sig')
    # Canonical launcher sources override the historical prototype scripts.
    for template in (ROOT / 'package_tools').iterdir():
        if template.is_file():
            content = template.read_text(encoding='utf-8-sig')
            content = content.replace("Version='0.2-TEST'", "Version='"+VERSION+"'")
            content = content.replace('v0.3-Testpaket','v'+VERSION+'-Testpaket')
            content = content.replace(sha(client_base).upper(), sha(client).upper())
            (destination / template.name).write_text(content, encoding='ascii' if template.suffix.lower()=='.cmd' else 'utf-8-sig')
    diagnostic_directory=destination/'diagnostics_tool'
    diagnostic_directory.mkdir()
    for name in ('coop_diagnostic_capture.py','coop_runtime_session.py','coop_population.py','coop_diagnostics.py','coop_capture_summary.py',
                 'record_bridge_exception.py','exception_debug_backend.py','bridge_exception_snapshot.py','bridge_crash_analysis.py',
                 'lookup_registry_snapshot.py','inspect_cinematic_crash.py','minidump_memory.py','pe_image_readonly.py'):
        content=(ROOT/name).read_text(encoding='utf-8')
        if name=='coop_runtime_session.py':
            content=content.replace('CLIENT_BUILDS={',"CLIENT_BUILDS={'"+sha(client).upper()+"',",1)
            content=content.replace('SERVER_BUILDS={',"SERVER_BUILDS={'"+sha(server).upper()+"',",1)
        (diagnostic_directory/name).write_text(content,encoding='utf-8')
    (destination / 'LIESMICH.md').write_text('''# The Run Coop v0.4 TEST – experimentelles Addon-Paket

NEU: Checkpoint-Registrierung unterscheidet den echten menschlichen Fahrer von
einem speziellen KI-Teilnehmer mit derselben Besitzer-ID. Offline in x86 emuliert;
noch kein Gameplaynachweis für diese Änderung. Kein vollständiger KI-/Finishfix.
Der separate AI-Quota-Prototyp ist NICHT Bestandteil dieses Installers.

Beide brauchen eine eigene passende Spielinstallation und das unterstützte
LAN-Grundpaket v1 vom 29.05.2024. Keine Spieldateien enthalten.

1. Spiel und Server schließen. Install-Coop.cmd auf beiden PCs starten.
2. RADMIN-ANLEITUNG.md befolgen. Koop-Starten.cmd bietet Host/Gast und ein IP-Feld.
3. Im Host-Starter erst Enter drücken, wenn das Gast-Spielfenster offen ist.
4. Nur der Host startet die Story. Das Starterfenster bleibt währenddessen offen.
5. Stop-Coop.cmd beendet die eigene Sitzung; Restore-Installation.cmd stellt die
   vor der Installation gesicherten Dateien wieder her. Spielstände werden vor
   jedem Start gesichert und nicht automatisch zurückgeschrieben.

Enthalten: gemeinsame Checkpoint-Zeit, gezielte Spawnkorrektur für Mission 1.51,
experimenteller Resetmodus und Sitzungs-Fahrzeugfreigabe. Ein Unfall des Hosts
ließ den Gast in einem aufgezeichneten Test weiterfahren. Diese Paketkombination
ist noch nicht als Ganzes im Spiel getestet.

Select soll in 1.51 einen gemeinsamen Event-Neustart anfordern. Zeitablauf,
beide Autos zerstört und blockierte Eingaben sind noch nicht zuverlässig gelöst.
Automatischer Folgeevent-Wechsel ist offen. Nur als Diagnose-Workaround: Host
drückt einmal Next Challenge im Debugmenü, falls derselbe Event erneut beginnt.
Das überspringt Storyteile und garantiert keinen korrekten Folgespawn.

Bekannte Fehler: fehlende Gegner/Verfolgung in der zweiten getesteten Mission,
unvollständige Gast-Cutscenes, falsches Gastauto, fehlender Host-Sound/Nitroeffekt,
keine gemeinsame Pause. v0.3 wurde auf zwei PCs über Radmin gefahren, zeigte aber
Abstürze und Missionsfehler. Dieser v0.4-Kandidat ist noch nicht im Spiel getestet.
Optionale lesende Diagnose: DIAGNOSE.md (Python erforderlich).
Definitive Edition und Musik+25dB werden automatisch mitinstalliert; siehe ADDONS.md. Allgemeiner Car-Swap-Fix ist nicht enthalten.
''', encoding='utf-8')
    if validation is not None:
        (destination/'OFFLINE-TESTS.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
    # Versioned release notes replace the historical prototype text above.
    shutil.copyfile(ROOT/'package_tools/LIESMICH.md',destination/'LIESMICH.md')
    shutil.copyfile(ROOT/'config/story-spawn-stage2-events.json',destination/'SPAWN-EVENTS.json')
    if args.team_finish_candidate:
        readme=destination/'LIESMICH.md'
        body=readme.read_text(encoding='utf-8').replace('v0.5 TEST','v'+VERSION)
        body=body.replace('- Der neuere Teamwertungs-Prototyp und gemeinsame Overtaken-HUD sind nicht\n  Bestandteil dieser Version. Sieg/Verlust und Story-Fortschritt koennen weiter\n  abweichen oder ein Rennen wiederholen.', '- Dynamischer Teamwertungs-Kandidat fuer normale Story-Zielwertung enthalten.\n  Noch NICHT im Spiel getestet; keine Garantie fuer gescriptete Fehlschlaege,\n  Cutscene-Abschluesse oder Fortschritt. Gemeinsamer Overtaken-HUD fehlt.')
        readme.write_text(body+'\nTeamwertung ist experimentell; nur mode0-Zielwertung, gescriptete Fehlschlaege nicht allgemein geloest.\n\nOptionale Autoauswahl im Starter: jeder waehlt fuer sich vor Spielstart. Vor dem Rennen im Hauptmenue einmal VIEW CARS / AUTOS ANSEHEN oeffnen, dann zurueck und Rennen starten. Die Wahl bleibt fuer diese Sitzung erzwungen; fuer ein anderes Auto Spiel neu starten. Gescriptete Story-Autos koennen abweichen. Kein Tankstellenfix, noch kein Gameplaynachweis fuer diese neue Starterfunktion.\n',encoding='utf-8')
    if args.gas_ack_timeout:
        readme=destination/'LIESMICH.md'
        readme.write_text(readme.read_text(encoding='utf-8')+'\nTestkandidat Tankstelle: Server wartet nur noch begrenzt auf die Ladebestaetigung der Clients und macht dann weiter. Experiment, kann unsichtbare Autos oder Fehler beim Client verursachen. Noch NICHT im Spiel getestet.\n',encoding='utf-8')
    if args.gas_unload_ack:
        readme=destination/'LIESMICH.md'
        readme.write_text(readme.read_text(encoding='utf-8')+'\nTankstellen-Entlade-Ack: Offline gepruefter Client-Kandidat, NICHT im Spiel bestaetigt. Nach nativ abgeschlossenem Entladen sendet der Client die originale Unloaded-Nachricht; kein Server-Timeout. Nur nach gemeinsamem Test freigeben. Kein automatisches Installieren. Lokalen Teststarter ausschliesslich mit pwsh ausfuehren. Recorder --downstream --completion direkt nach dem Missionsladen starten; im HOST genau eine Autoauswahl bestaetigen, im GAST nichts. Erfolg braucht Entlade-Acks beider Clients, Server-Ack-Abbau, nachfolgendes Laden, Vorschau und Weiterfahren. GAS-/ALL-CANDIDATE sind kein Ersatz und duerfen fuer diesen Test nicht verwendet werden.\n',encoding='utf-8')
    if args.reserve_authored_slots:
        readme=destination/'LIESMICH.md'
        readme.write_text(readme.read_text(encoding='utf-8')+'\nTestkandidat Startplatz: Der Gast startet hinter dem originalen Solo-Feld, damit Eliminator-Gegner echte NPCs bleiben. Noch NICHT im Spiel getestet.\n',encoding='utf-8')
    if VERSION in ('0.7-TEST','0.7.1-TEST'):
        shutil.copyfile(ROOT/'RELEASE-0.7.md',destination/'LIESMICH.md')
        shutil.copyfile(ROOT/'RELEASE-0.7.md',destination/'CHANGELOG.md')
        shutil.copyfile(ROOT/'README-0.7.md',destination/'README.md')
        if VERSION=='0.7.1-TEST':
            for name in ('LIESMICH.md','CHANGELOG.md','README.md'):
                doc=destination/name
                text=doc.read_text(encoding='utf-8').replace('v0.7 TEST','v0.7.1 TEST').replace('v0.7-TEST','v0.7.1-TEST')
                note='\nGarage autostart hotfix: suppress only the PowerShell console (CreateNoWindow), keep the Garage window visible on every Host/Guest start. Game patches unchanged from v0.7.\n'
                doc.write_text(text+note,encoding='utf-8')
        copy_local_sources(destination/'src',('build_test_package.py','snapshot_pause_hud.py','coop_summary.py',
            'test_coop_hud.py','test_pause_hud_ai.py','test_garage_window.py','test_garage_autostart.py','test_package_delta.py'))
    car_catalogue=json.loads((destination/'Start-Cars.json').read_text(encoding='utf-8-sig'))
    car_choice_report=dict(saved_per_role_and_nickname=True,stock_cars=len(car_catalogue)-1,
                           helper_force_for_session=True,effective_on='next game launch',
                           event_transition_gameplay_verified=False,requires_initial_view_cars=True,
                           scripted_story_cars_may_override=True,powershell7_required=True)
    (destination/'GAMEPLAY-STATUS.json').write_text(json.dumps(dict(
        version=VERSION,ai=report['ai_gate'],spawn=report['story_start'],
        combined_package_gameplay_verified=False,garage_fix_included=False,
        pause_autodrive_included=args.pause_ai,team_result_adapter_included=args.team_finish_candidate,
        coop_hud_included=args.coop_hud,coop_hud=client_report.get('coop_hud'),
        second_human_slot_reservation_included=args.reserve_authored_slots,
        pause_ai_included=args.pause_ai,pause_ai=client_report.get('pause_ai'),
        battle_team_finish_included=args.battle_team_finish,battle_team_finish=report.get('battle_team_finish'),
        gas_ack_timeout_included=args.gas_ack_timeout,gas_ack_timeout=report.get('gas_ack_timeout'),
        gas_unload_ack_included=args.gas_unload_ack,gas_unload_ack=client_report.get('gas_unload_ack'),
        legacy_prelaunch_car_choice=car_choice_report,
        persistent_car_choice=dict(mode='server_per_human',relay_port=25211,
            effective_on='next vehicle spawn / Retry',requires_open_garage_window=True,
            shared_tcp_palette_error_fixed=True,guest_story_auto_release_supported=False),
        garage_console_free_visible_autostart=VERSION=='0.7.1-TEST',
        live_evidence_2026_11_07=dict(host_pause_ai=True,native_multiplayer_player_list_visible=True,
            first_npc_in_2_6_correct=True,guest_can_still_lose_battle_when_only_host_wins=True,
            exact_multiplayer_gap_values_verified=False) if VERSION in ('0.7-TEST','0.7.1-TEST') else None,
        team_result=client_report.get('team_result')),indent=2),encoding='utf-8')
    # CMD does not reliably accept a UTF-8 BOM before @echo. Historical copied
    # launchers and current templates must all begin with their real command.
    for command in destination.rglob('*.cmd'):
        command.write_text(command.read_text(encoding='utf-8-sig'),encoding='ascii')
    addon_manifest = bundle_addons(destination)
    files = []
    for path in sorted(destination.rglob('*')):
        if path.is_file():
            if path.suffix.lower() in {'.exe', '.dll', '.asi', '.ebx', '.sb', '.toc', '.dmp'}:
                relative = path.relative_to(destination).as_posix()
                allowed = 'addons/NFSTR_DefinitiveEdition.asi'
                expected = addon_manifest['files'].get('NFSTR_DefinitiveEdition.asi')
                if relative != allowed or sha(path.read_bytes()) != expected:
                    raise ValueError('Unapproved game/binary file in package')
            files.append(dict(path=path.relative_to(destination).as_posix(), sha256=sha(path.read_bytes()), bytes=path.stat().st_size))
    (destination / 'package-manifest.json').write_text(json.dumps(dict(version=VERSION, files=files, limitations=report['validation'], client=client_report,server=report,gameplay_verified=False,published=False), indent=2))
    archive = destination.parent / (destination.name + '.zip')
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as zipout:
        for path in destination.rglob('*'):
            if path.is_file():
                zipout.write(path, destination.name + '/' + path.relative_to(destination).as_posix())
    print(json.dumps(dict(package=str(destination), zip=str(archive), files=len(files), game_binaries=False)))


if __name__ == '__main__':
    main()
