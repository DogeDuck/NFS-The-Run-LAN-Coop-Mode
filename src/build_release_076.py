"""Correct updater and preserve frozen addon bytes. Never rewrite nested assets."""
import json
import shutil
import zipfile
from pathlib import Path
from build_release_074_test import ROOT, load, write
from build_test_package import sha

VERSION = '0.7.6-TEST'
SOURCE = ROOT / 'release/TheRun-Coop-v0.7.4-TEST'
DEST = ROOT / ('release/TheRun-Coop-v' + VERSION)


def main():
    archive = Path(str(DEST) + '.zip')
    if DEST.exists() or archive.exists(): raise ValueError('Release already exists')
    manifest = load(SOURCE / 'package-manifest.json')
    for item in manifest['files']:
        data = (SOURCE / item['path']).read_bytes()
        if sha(data) != item['sha256'] or len(data) != item['bytes']: raise ValueError('Frozen source differs')
    shutil.copytree(SOURCE, DEST)
    shutil.copyfile(ROOT / 'package_tools/Update-Coop.ps1', DEST / 'Update-Coop.ps1')
    shutil.copyfile(Path(__file__), DEST / 'src/build_release_076.py')
    for path in DEST.iterdir():
        if not path.is_file() or path.suffix not in ('.md', '.ps1'): continue
        before = path.read_text(encoding='utf-8-sig')
        after = before.replace('v0.7.4 TEST', 'v0.7.6 TEST').replace('v0.7.4-TEST', 'v0.7.6-TEST').replace("Version='0.7.4-TEST'", "Version='0.7.6-TEST'")
        if before != after: path.write_text(after, encoding='utf-8-sig')
    changelog = DEST / 'CHANGELOG.md'
    text = changelog.read_text(encoding='utf-8-sig')
    text = text.replace('## Deutsch', '## Deutsch\n\n- Ersetzt0.7.4/0.7.5: GitHub-Array korrekt eingelesen und unveränderte Addon-Dateien erhalten.0.7.5 wurde durch die Installationsvorprüfung abgefangen und nicht ins Spiel installiert. Native Spielpatches unverändert.\n', 1)
    text = text.replace('## English', '## English\n\n- Supersedes0.7.4/0.7.5: correct GitHub array handling and preserve original addon bytes. Installer preflight rejected0.7.5 before game files were written. Native gameplay patches unchanged.\n', 1)
    changelog.write_text(text, encoding='utf-8')
    status = load(DEST / 'GAMEPLAY-STATUS.json')
    status.update(version=VERSION, updater_array_fix=True, native_gameplay_identical_to='0.7.4-TEST', preserves_addon_checksums=True)
    write(DEST / 'GAMEPLAY-STATUS.json', status)
    validation = load(DEST / 'validation.json')
    validation.update(updater_live_available_check=True, supersedes='0.7.4/0.7.5 updater/packaging corrections')
    write(DEST / 'validation.json', validation)
    addon_manifest = load(DEST / 'addons/manifest.json')
    for name, digest in addon_manifest['files'].items():
        if sha((DEST / 'addons' / name).read_bytes()) != digest:
            raise ValueError('Addon changed: ' + name)
    files = []
    for path in sorted(DEST.rglob('*')):
        if path.is_file() and path.name != 'package-manifest.json':
            data = path.read_bytes()
            files.append(dict(path=path.relative_to(DEST).as_posix(), sha256=sha(data), bytes=len(data)))
    manifest.update(version=VERSION, files=files)
    write(DEST / 'package-manifest.json', manifest)
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as out:
        for path in sorted(DEST.rglob('*')):
            if path.is_file(): out.write(path, DEST.name + '/' + path.relative_to(DEST).as_posix())
    receipt = dict(version=VERSION, package=str(DEST), archive=str(archive), sha256=sha(archive.read_bytes()),
        bytes=archive.stat().st_size, files=len(files), client_sha256=manifest['client_sha256'],
        server_sha256=manifest['server_sha256'], published=False, installed=False)
    write(ROOT / 'outputs/v0.7.6-build-receipt.json', receipt)
    print(json.dumps(receipt))


if __name__ == '__main__': main()
