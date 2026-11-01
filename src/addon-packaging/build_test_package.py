"""Build local two-player test package: scripts and deltas only, no game binaries."""
from pathlib import Path
import base64
import argparse
import hashlib
import json
import shutil
import zipfile
from patch_test_candidate import build_server, build_client
from bundle_coop_addons import bundle as bundle_addons

ROOT = Path(__file__).resolve().parent
GAME = Path(r'X:\EA Games\Need for Speed The Run\Need for Speed The Run')
VERSION='0.4-TEST'


def sha(data):
    return hashlib.sha256(data).hexdigest()


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
    return research_baseline(current,previous,candidates)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'release/TheRun-Coop-v0.4-DEV')
    parser.add_argument('--validation',type=Path,help='Optional completed offline test report to include')
    args=parser.parse_args()
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
    server_base=installed_research_baseline((GAME/'NFSTR_Server.exe').read_bytes(),'server')
    server, _, report = build_server(server_base)
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
        for key, patch in list(patches.items()):
            if key.startswith(stem):
                start = original if key == stem else research_base if key.endswith('research-upgrade') else previous if key.endswith('v0_3-upgrade') else old_release
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
        foreach($suffix in @('-upgrade','-research-upgrade','-v0_3-upgrade')){
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
            content = content.replace('v0.3-Testpaket','v0.4-Entwicklungspaket')
            content = content.replace(sha(client_base).upper(), sha(client).upper())
            (destination / template.name).write_text(content, encoding='ascii' if template.suffix.lower()=='.cmd' else 'utf-8-sig')
    diagnostic_directory=destination/'diagnostics_tool'
    diagnostic_directory.mkdir()
    for name in ('coop_diagnostic_capture.py','coop_runtime_session.py','coop_population.py','coop_diagnostics.py','coop_capture_summary.py',
                 'record_bridge_exception.py','exception_debug_backend.py','bridge_exception_snapshot.py','bridge_crash_analysis.py',
                 'lookup_registry_snapshot.py','inspect_cinematic_crash.py','minidump_memory.py','pe_image_readonly.py'):
        shutil.copyfile(ROOT/name,diagnostic_directory/name)
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
    (destination / 'package-manifest.json').write_text(json.dumps(dict(version=VERSION, files=files, limitations=report['validation'], client=client_report,gameplay_verified=False,published=False), indent=2))
    archive = destination.parent / (destination.name + '.zip')
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as zipout:
        for path in destination.rglob('*'):
            if path.is_file():
                zipout.write(path, destination.name + '/' + path.relative_to(destination).as_posix())
    print(json.dumps(dict(package=str(destination), zip=str(archive), files=len(files), game_binaries=False)))


if __name__ == '__main__':
    main()
