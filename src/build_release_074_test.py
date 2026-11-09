"""Build public 0.7.4 TEST. QTE-local-binding experiment is never enabled here."""
import json
import shutil
import zipfile
from pathlib import Path
from build_test_package import apply, reverse_apply, delta, copy_local_sources, sha
from patch_claude_story_bundle import build_client, build_server, SERVER
from patch_spawn_allowlist import build as marcus, catalogues

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'release/TheRun-Coop-v0.7.3-TEST'
VERSION = '0.7.4-TEST'
DEST = ROOT / ('release/TheRun-Coop-v' + VERSION)


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    archive = Path(str(DEST) + '.zip')
    if DEST.exists() or archive.exists():
        raise ValueError('Release already exists; never overwrite')
    for entry in load(SOURCE / 'package-manifest.json')['files']:
        data = (SOURCE / entry['path']).read_bytes()
        if len(data) != entry['bytes'] or sha(data) != entry['sha256']:
            raise ValueError('Source package changed: ' + entry['path'])
    old = {}
    for stem, backup in (('client', 'Need For Speed The Run.exe.lan-before-road-reset'),
                         ('server', 'NFSTR_Server.exe.headless-original')):
        old[stem] = apply((ROOT / 'backups' / backup).read_bytes(), load(SOURCE / f'patches/{stem}.json'))
    marcus_server = marcus(old['server'], *catalogues())
    if sha(marcus_server) != SERVER:
        raise ValueError('Unexpected Marcus baseline')
    catalog = load(ROOT / 'outputs/chicago-bundle-owner-catalog.json')
    client, client_report = build_client(old['client'], catalog)
    server, server_report = build_server(marcus_server, with_difficulty=True)
    new = dict(client=client, server=server)
    patches = {}
    for stem in old:
        for path in (SOURCE / 'patches').glob(stem + '*.json'):
            previous = load(path)
            baseline = reverse_apply(old[stem], previous)
            patch = delta(previous['FileName'], baseline, new[stem])
            if apply(baseline, patch) != new[stem]:
                raise ValueError('Native delta roundtrip failed: ' + path.name)
            patches[path.name] = patch
        filename = 'Need For Speed The Run.exe' if stem == 'client' else 'NFSTR_Server.exe'
        patches[stem + '-v0_7_3-upgrade.json'] = delta(filename, old[stem], new[stem])
    patches['server-v0_7_3-marcus-upgrade.json'] = delta('NFSTR_Server.exe', marcus_server, server)
    shutil.copytree(SOURCE, DEST)
    for template in (ROOT / 'package_tools').iterdir():
        if not template.is_file():
            continue
        text = template.read_text(encoding='utf-8-sig')
        (DEST / template.name).write_text(text, encoding='ascii' if template.suffix.lower() == '.cmd' else 'utf-8-sig')
    for name, patch in patches.items():
        write(DEST / 'patches' / name, patch)
    installer = DEST / 'Install-Coop.ps1'
    text = installer.read_text(encoding='utf-8-sig')
    marker = "'-v0_7_2-upgrade')"
    if text.count(marker) != 1:
        raise ValueError('Installer upgrade list changed')
    installer.write_text(text.replace(marker, "'-v0_7_2-upgrade','-v0_7_3-upgrade','-v0_7_3-marcus-upgrade')"), encoding='utf-8-sig')
    old_clients = ('C9D48E500EF82EFC642EDF2DB848A9072E56FBC114E283173D6E7E58BAC634A6',
                   '42746E48E5E20FC3EE96C54F30EB0B4D6070D48A966EB9483386AA18DB4C309E', sha(old['client']))
    old_servers = ('B912B57BF013DC6AC37C2BC0DAE8367496776ED5429F7AFCE6B319015AE8512C', sha(old['server']), SERVER)
    for path in DEST.rglob('*'):
        if not path.is_file() or path.suffix not in ('.ps1', '.py') or 'src' in path.relative_to(DEST).parts:
            continue
        text = path.read_text(encoding='utf-8-sig')
        for digest in old_clients:
            text = text.replace(digest.lower(), sha(client)).replace(digest.upper(), sha(client).upper())
        for digest in old_servers:
            text = text.replace(digest.lower(), sha(server)).replace(digest.upper(), sha(server).upper())
        for version in ('0.2-TEST', '0.7.2-TEST', '0.7.3-TEST'):
            text = text.replace("Version='" + version + "'", "Version='" + VERSION + "'")
        path.write_text(text, encoding='utf-8-sig')
    write(DEST / 'config/chicago-bundle-owner-catalog.json', catalog)
    status = load(DEST / 'GAMEPLAY-STATUS.json')
    status.update(version=VERSION, combined_package_gameplay_verified=False,
        claude_live_helpers='Host selection, guest vehicle10.5 v2, ordered helicopter ownership and OOC HUD tested separately in RAM on09Nov.',
        client_story_bundle=client_report, server_story_bundle=server_report,
        host_difficulty_included=True, difficulty_gameplay_verified=False,
        github_updater_included=True, updater_integrity_checks=True,
        guest_mute_included=False, guest_qte_synchronization_fixed=False,
        qte_local_binding_experiment_enabled=False, cutscene_collision_fix_included=False,
        gas_stations_blocked=False, powershell7_auto_install=False,
        current_qte_live='10.4: first load scene on GUEST; Retry scene on HOST; roof stalls with no prompt even after freecam off.',
        multiplayer_target='2 tested; selected adapters emulated for2-4. Full four-player campaign unverified.')
    write(DEST / 'GAMEPLAY-STATUS.json', status)
    validation = load(ROOT / 'outputs/night-work-20261110-0028/offline-validation.json')
    write(DEST / 'validation.json', dict(**validation, combined_package_gameplay_verified=False,
        limits='Targeted offline checks only. Native engine rendering/streaming and combined gameplay need joint live test.'))
    changelog = ROOT / 'RELEASE-NOTES-0.7.4.md'
    (DEST / 'CHANGELOG.md').write_text(changelog.read_text(encoding='utf-8'), encoding='utf-8')
    for name in ('README.md', 'LIESMICH.md', 'README-EN.md', 'README-DE.md'):
        path = DEST / name
        if path.is_file():
            path.write_text('# v' + VERSION + '\n\n[Changes / Änderungen](CHANGELOG.md)\n'
                '[Updates and difficulty / Updates und Schwierigkeit](UPDATES-DIFFICULTY.md)\n\n'
                + path.read_text(encoding='utf-8-sig'), encoding='utf-8-sig')
    shutil.copyfile(ROOT / 'UPDATES-DIFFICULTY-0.7.4.md', DEST / 'UPDATES-DIFFICULTY.md')
    copy_local_sources(DEST / 'src', ('patch_claude_story_bundle.py', 'build_release_074_test.py',
        'patch_spawn_allowlist.py', 'qte_local_event_adapter.py', 'patch_qte_local_binding.py',
        'test_qte_local_binding.py', 'build_qte_local_candidate.py', 'test_host_difficulty.py'))
    files = []
    for path in sorted(DEST.rglob('*')):
        if not path.is_file() or path.name == 'package-manifest.json':
            continue
        if path.suffix.lower() in ('.exe', '.dll', '.ebx', '.sb', '.toc', '.dmp'):
            raise ValueError('Game binary must not be packaged')
        data = path.read_bytes()
        files.append(dict(path=path.relative_to(DEST).as_posix(), sha256=sha(data), bytes=len(data)))
    write(DEST / 'package-manifest.json', dict(version=VERSION, files=files,
        client_sha256=sha(client), server_sha256=sha(server), gameplay_verified=False))
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as output:
        for path in sorted(DEST.rglob('*')):
            if path.is_file(): output.write(path, DEST.name + '/' + path.relative_to(DEST).as_posix())
    receipt = dict(version=VERSION, package=str(DEST), archive=str(archive), sha256=sha(archive.read_bytes()),
        bytes=archive.stat().st_size, files=len(files), client_sha256=sha(client), server_sha256=sha(server),
        installed=False, published=False)
    write(ROOT / 'outputs/v0.7.4-test-build-receipt.json', receipt)
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
