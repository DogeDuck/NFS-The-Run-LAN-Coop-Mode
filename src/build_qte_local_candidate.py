"""Build a separate, opt-in QTE context candidate from the frozen0.7.4 release."""
import shutil
import zipfile
from pathlib import Path
from build_release_074_test import ROOT, DEST as SOURCE, load, write
from build_test_package import apply, reverse_apply, delta, sha
from patch_qte_local_binding import build

VERSION = '0.7.4-QTE-LOCAL-CANDIDATE'
DEST = ROOT / ('outputs/TheRun-Coop-v' + VERSION)


def main():
    archive = Path(str(DEST) + '.zip')
    if DEST.exists() or archive.exists():
        raise ValueError('Candidate exists; do not overwrite')
    for item in load(SOURCE / 'package-manifest.json')['files']:
        content = (SOURCE / item['path']).read_bytes()
        if len(content) != item['bytes'] or sha(content) != item['sha256']:
            raise ValueError('Source differs: ' + item['path'])
    original = apply((ROOT / 'backups/Need For Speed The Run.exe.lan-before-road-reset').read_bytes(), load(SOURCE / 'patches/client.json'))
    patched, report = build(original)
    updates = {}
    for path in (SOURCE / 'patches').glob('client*.json'):
        baseline = reverse_apply(original, load(path))
        result = delta('Need For Speed The Run.exe', baseline, patched)
        if apply(baseline, result) != patched:
            raise ValueError('Candidate delta roundtrip failed')
        updates[path.name] = result
    updates['client-v0_7_4-upgrade.json'] = delta('Need For Speed The Run.exe', original, patched)
    shutil.copytree(SOURCE, DEST)
    for name, patch in updates.items(): write(DEST / 'patches' / name, patch)
    for path in DEST.rglob('*'):
        if not path.is_file() or path.suffix not in ('.ps1', '.py') or 'src' in path.relative_to(DEST).parts:
            continue
        text = path.read_text(encoding='utf-8-sig')
        text = text.replace(sha(original), sha(patched)).replace(sha(original).upper(), sha(patched).upper())
        text = text.replace("Version='0.7.4-TEST'", "Version='" + VERSION + "'")
        if path.name == 'Install-Coop.ps1':
            marker = "'-v0_7_3-marcus-upgrade')"
            if text.count(marker) != 1: raise ValueError('Upgrade selector changed')
            text = text.replace(marker, "'-v0_7_3-marcus-upgrade','-v0_7_4-upgrade')")
        path.write_text(text, encoding='utf-8-sig')
    status = load(DEST / 'GAMEPLAY-STATUS.json')
    status.update(version=VERSION, qte_local_binding_experiment_enabled=True,
                  qte_local_binding=report, combined_package_gameplay_verified=False)
    write(DEST / 'GAMEPLAY-STATUS.json', status)
    (DEST / 'QTE-LOCAL-TEST.md').write_text(
        '# INTERN / INTERNAL – QTE local player context\n\n'
        'NOT installed/published. Do not use without joint test. Native client message receive E21C9A.\n'
        'LAN Story OOC only: construct received player events with the current local human.\n'
        'No fake success, event replay, readiness edits, actor teleport or EventSync mute.\n'
        'Offline ABI/scope checked for2-4 humans. NOT a proof of camera/streaming/QTE progress.\n'
        'Risk: a network broadcast for multiple humans might now repeat a local action; stop if a scene restarts. '
        'It cannot repair messages never delivered by the server. Host-only input is NOT implemented.\n\n'
        'Mit Nutzer: Save frisch sichern, nie Restore. pwsh -File start_local_checkpoint_test.ps1 '
        '-PackageDirectory outputs\\TheRun-Coop-v0.7.4-QTE-LOCAL-CANDIDATE\n'
        'Nur HOST10.4 direkt starten. Erst beide Szenen und erste Aufforderung prüfen, dann Dachstelle. '
        'Keine Gast-Eingabe bis zur Beobachtung; falls Aufforderung nur Gast, melden. '
        'Bestehenden --ant-identity Recorder nutzen, keine weiteren Proben bauen. Logs nur coop_summary.py.\n'
        'Nach Test auf0.7.4-TEST zurückpatchen; keinen Spielstand zurückspielen.\n', encoding='utf-8')
    files = []
    for path in sorted(DEST.rglob('*')):
        if path.is_file() and path.name != 'package-manifest.json':
            content = path.read_bytes()
            files.append(dict(path=path.relative_to(DEST).as_posix(), sha256=sha(content), bytes=len(content)))
    manifest = load(SOURCE / 'package-manifest.json')
    manifest.update(version=VERSION, files=files, client_sha256=sha(patched), gameplay_verified=False)
    write(DEST / 'package-manifest.json', manifest)
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as out:
        for path in sorted(DEST.rglob('*')):
            if path.is_file(): out.write(path, DEST.name + '/' + path.relative_to(DEST).as_posix())
    receipt = dict(version=VERSION, package=str(DEST), archive=str(archive), client_sha256=sha(patched),
        server_sha256=manifest['server_sha256'], sha256=sha(archive.read_bytes()), bytes=archive.stat().st_size,
        report=report, installed=False, published=False, gameplay_verified=False)
    write(ROOT / 'outputs/qte-local-candidate-build-receipt.json', receipt)
    print(receipt)


if __name__ == '__main__': main()
