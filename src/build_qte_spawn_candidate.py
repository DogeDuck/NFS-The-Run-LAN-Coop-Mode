"""Build one isolated local-actor QTE candidate on RACESTART; never install."""
from pathlib import Path
import json
import shutil
import zipfile
from build_release_077_candidate import ROOT, load, write, verify_manifest
from build_test_package import apply, reverse_apply, delta, sha, copy_local_sources
from offline_test_images import image
from patch_qte_spawn_local_bus import build

SOURCE=ROOT/'outputs/TheRun-Coop-v0.7.7-RACESTART-CANDIDATE'
VERSION='0.7.7-RACESTART-QTE-LOCAL-ACTOR-CANDIDATE'
DEST=ROOT/('outputs/TheRun-Coop-v'+VERSION)
NOTE='''# QTE local actor / Lokaler QTE-Akteur

Deutsch: Separater interner Testkandidat, NICHT installiert oder veröffentlicht.
Die allgemeine Verknüpfungsauflösung des Spiels verwendet beim BasicControllable-
Spawner den Bus der zuerst erzeugten Figur. Die Cinebot-Kamera sucht dagegen
ausdrücklich die eigene Figur. Der Kandidat benutzt diese lokale Zuordnung auch
für die allgemeinen Verknüpfungen: nur verbundener LAN-Story-QTE-Modus, nur diese
Spawner-Klasse, keine feste Spieler-ID. Solo/Fahr-Rennen bleiben nativ. Fehlt eine
passende lokale Figur, gilt weiterhin das originale Verhalten.

Die falsche Zuordnung lässt sich mit den echten Registrierungs-, Getter- und
Linkresolver-Bytes im Emulator reproduzieren und gezielt ändern. Das beweist
NICHT, dass Kamera, Szenenstart und komplette QTE im Spiel jetzt funktionieren.
Keine zusätzlichen Start-/Erfolgs-/Ladenachrichten, kein Start-Replay, keine
Szenenunterdrückung, kein Frame-Hook. Server unverändert. Host-only-Eingabe und
gemeinsamer QTE-Fortschritt sind NICHT implementiert.

English: Separate internal test candidate, NOT installed/published. In connected
LAN Story OOC only, BasicControllable spawn references resolve through the local
human's pawn bus, using the ownership criterion already used by native Cinebot.
No fixed player IDs, new events, ANT replay, frame hook or server changes. Native
fallback without a matching local pawn. Native-byte emulation proves changed
actor-link selection, NOT a functioning whole QTE. Host-only input and shared
QTE progress remain unimplemented.

Live test (with user): Save backup, no restore. Close game/server, back up exact
mod EXE, install this candidate ALONE. Use pwsh and explicit -PackageDirectory,
maximum 2 local clients. Load 10.4 directly. First inspect camera/Jack in BOTH;
then operate only HOST and compare progression through roof/stairs. On crash or
missing camera, stop. Do NOT stack old relay, guest mute, local-event rebinding,
GAS/ALL or cutscene-AI experiments. Retry once only after a stable first load.
Rollback: exact backed-up mod EXE with game stopped; never restore saves.
'''


def main():
    archive=Path(str(DEST)+'.zip')
    if DEST.exists() or archive.exists():raise ValueError('Frozen candidate already exists')
    manifest=load(SOURCE/'package-manifest.json');verify_manifest(SOURCE,manifest)
    old=image('client','integrated');new,report=build(old)
    if manifest['client_sha256'].lower()!=sha(old).lower():raise ValueError('Source client is not DF9F7069')
    patches={}
    for path in (SOURCE/'patches').glob('client*.json'):
        baseline=reverse_apply(old,load(path))
        patch=delta('Need For Speed The Run.exe',baseline,new)
        if apply(baseline,patch)!=new:raise ValueError('Delta roundtrip '+path.name)
        patches[path.name]=patch
    patches['client-v0_7_7-upgrade.json']=delta('Need For Speed The Run.exe',old,new)
    if apply(old,patches['client-v0_7_7-upgrade.json'])!=new:raise ValueError('DF upgrade roundtrip')
    shutil.copytree(SOURCE,DEST)
    for name,patch in patches.items():write(DEST/'patches'/name,patch)
    installer=(DEST/'Install-Coop.ps1').read_bytes().decode('utf-8-sig')
    if installer.count("'-v0_7_3-marcus-upgrade','-v0_7_7-upgrade'))")!=1:
        raise ValueError('Installer suffix contract')
    for path in DEST.glob('*.ps1'):
        before=path.read_bytes().decode('utf-8-sig')
        after=before.replace("Version='"+manifest['version']+"'","Version='"+VERSION+"'")
        after=after.replace(sha(old),sha(new)).replace(sha(old).upper(),sha(new).upper())
        if before!=after:path.write_bytes(b'\xef\xbb\xbf'+after.encode('utf-8'))
    status=load(DEST/'GAMEPLAY-STATUS.json')
    status.update(version=VERSION,source_package=SOURCE.name,native_gameplay_identical_to=None,
                  qte_local_actor=report,combined_package_gameplay_verified=False,
                  guest_qte_synchronization_fixed=False,host_only_qte_input=False)
    write(DEST/'GAMEPLAY-STATUS.json',status)
    for name in ('QTE-LOCAL-ACTOR-TEST.md','CHANGELOG.md'):
        (DEST/name).write_text(NOTE,encoding='utf-8')
    copy_local_sources(DEST/'src',('qte_spawn_local_bus.py','patch_qte_spawn_local_bus.py',
        'test_qte_spawn_local_bus.py','build_qte_spawn_candidate.py'))
    files=[]
    for path in sorted(DEST.rglob('*')):
        if path.is_file() and path.name!='package-manifest.json':
            if path.suffix.lower() in ('.exe','.dll','.sb','.toc','.ebx','.dmp','.sqlite3'):
                raise ValueError('Game/private binary in package')
            data=path.read_bytes();files.append(dict(path=path.relative_to(DEST).as_posix(),bytes=len(data),sha256=sha(data)))
    manifest.update(version=VERSION,files=files,client_sha256=sha(new))
    write(DEST/'package-manifest.json',manifest);verify_manifest(DEST,manifest)
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as out:
        for path in sorted(DEST.rglob('*')):
            if path.is_file():out.write(path,DEST.name+'/'+path.relative_to(DEST).as_posix())
    receipt=dict(version=VERSION,package=str(DEST),archive=str(archive),bytes=archive.stat().st_size,
        sha256=sha(archive.read_bytes()),client_sha256=sha(new),server_sha256=manifest['server_sha256'],
        files=len(files),adapter=report,installed=False,published=False,gameplay_verified=False)
    write(ROOT/'outputs/qte-night-20261114/local-actor-build-receipt.json',receipt)
    print(json.dumps({k:receipt[k] for k in ('version','sha256','client_sha256','server_sha256','files')}))


if __name__=='__main__':main()
