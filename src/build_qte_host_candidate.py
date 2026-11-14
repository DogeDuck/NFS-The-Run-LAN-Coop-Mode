"""Build isolated local-actor + verified-host scene milestones; never install."""
from pathlib import Path
import json
import shutil
import zipfile
from build_release_077_candidate import ROOT,load,write,verify_manifest
from build_test_package import apply,reverse_apply,delta,sha,copy_local_sources
from offline_test_images import image
from patch_qte_spawn_local_bus import build as client_build
from patch_qte_host_milestones import build as server_build

SOURCE=ROOT/'outputs/TheRun-Coop-v0.7.7-RACESTART-CANDIDATE'
VERSION='0.7.7-RACESTART-QTE-HOST-ACTOR-CANDIDATE-R2'
DEST=ROOT/('outputs/TheRun-Coop-v'+VERSION)
NOTE='''# Local actors + HOST milestones / Lokale Akteure + HOST-Szenenfortschritt

Deutsch: Interner Testkandidat, NICHT installiert/veröffentlicht, kein bestätigter
QTE-Fix. (1) BasicControllable-Verknüpfungen wählen im LAN-Story-QTE die eigene
Figur wie die native Cinebot-Kamera. (2) Der anhand des ausdrücklich gewählten
Hostnamens verifizierte HOST löst zwei echte 10.4-Szenen-Meilensteine einmal aus:
kickandrun.OnStarted und herostealscar.OnFinished. Gastmeldungen zählen dort nicht
erneut. ANIMATIONS-MEILENSTEINE, KEINE Ladebestätigungen. Der alte READY-ACTOR-
Wartekandidat ist ZURÜCKGEZOGEN. Kein Warten auf alle Menschen an diesen Knoten.
Alle anderen EventSync-/Lade-Nachrichten bleiben nativ. R2: Umordnen der Menschenliste
oder Abmelden eines Gasts darf erledigte Schritte nicht erneut freigeben.
Retry/Etappenwechsel und
echte Quell-Subwelt-Ladevorgänge setzen die passende Instanz zurück. Hostname fehlt
oder passt nicht: konservativ originales Verhalten.

Native-byte-Test: Originalserver lässt eine verspätete zweite Meldung den bereits
geladenen Abschnitt entladen/neu laden. Host-Meilenstein zählt einmal. Die lokale falsche
Akteurzuordnung und ihre Korrektur sind ebenfalls mit echten Spielanweisungen
emuliert. Das ersetzt keinen Test von Welt, Kamera, Eingabe und kompletter QTE.
Host-only-Eingabe ist NICHT vollständig implementiert; Guest-Fail-NIS bleibt nativ.
Kein Start-Replay, allgemeines Gast-Mute, neuer
Frame-Hook, Polling oder Timeout. Keine weiteren experimentellen Fixes enthalten.

English: Internal test candidate, NOT installed/published; whole-QTE success is
unverified. Local human actor-link selection plus HOST-authoritative, once-per-
generation handling of kickandrun.OnStarted / herostealscar.OnFinished in 10.4.
These are ANIMATION milestones, NOT readiness. The former READY-ACTOR barrier is
WITHDRAWN. No waiting for every human at these nodes. Host is verified by explicit
name, never player0/list order. Retry/new mission and real source subworld reload
rearm the state. All other EventSync/loading messages remain native. Full host-only
input and guest failure handling are NOT implemented. No fabricated readiness,
timer, polling, ANT replay or broad guest mute. Emulation is not gameplay proof.

Live mit Nutzer / with user:
1. Spiel/Server beenden, frische Save-Sicherung (kein Restore), beide Mod-EXEs
   bytegenau sichern. Nur diesen Kandidaten installieren, keine Experimente stapeln.
   Persönliche Grafik-/Audio-Einstellungen vor Installation sichern und erhalten;
   der Installer-Check plant neben den EXEs auch INI-Änderungen.
2. pwsh -File start_local_checkpoint_test.ps1 -PackageDirectory
   outputs\\TheRun-Coop-v0.7.7-RACESTART-QTE-HOST-ACTOR-CANDIDATE-R2
   Höchstens 2 lokale Clients. Nur HOST lädt direkt 10.4. Kamera/Jack in beiden
   prüfen, dann zunächst nur HOST bedienen. Bei fehlender Szene oder Absturz stoppen.
3. Dach/Feuertreppe und kompletten Szenenabschluss prüfen; danach genau ein Retry.
   Host-only-Fortschritt nicht als garantiert voraussetzen. Bestehenden
   snapshot_qte_roles.py mit --host-candidate für Zähler nutzen, keine neuen Hooks.
4. Rückbau nur über die gesicherten EXEs mit beendetem Spiel. Saves nie zurückspielen.
'''


def main():
    archive=Path(str(DEST)+'.zip')
    if DEST.exists() or archive.exists():raise ValueError('Frozen candidate exists')
    manifest=load(SOURCE/'package-manifest.json');verify_manifest(SOURCE,manifest)
    client=image('client','integrated')
    server=(ROOT/'outputs/offline-3h-20261113/ghidra/NFSTR_Server_BCDAFBF8.exe').read_bytes()
    if (manifest['client_sha256'].lower(),manifest['server_sha256'].lower())!=(sha(client),sha(server)):
        raise ValueError('Source package native hashes differ')
    new_client,cr=client_build(client);new_server,sr=server_build(server)
    patches={}
    for stem,old,new,filename in (('client',client,new_client,'Need For Speed The Run.exe'),
                                  ('server',server,new_server,'NFSTR_Server.exe')):
        for path in (SOURCE/'patches').glob(stem+'*.json'):
            baseline=reverse_apply(old,load(path));patch=delta(filename,baseline,new)
            if apply(baseline,patch)!=new:raise ValueError('Delta roundtrip '+path.name)
            patches[path.name]=patch
        patches[stem+'-v0_7_7-upgrade.json']=delta(filename,old,new)
        if apply(old,patches[stem+'-v0_7_7-upgrade.json'])!=new:raise ValueError('DF/BC upgrade roundtrip')
    shutil.copytree(SOURCE,DEST)
    for name,patch in patches.items():write(DEST/'patches'/name,patch)
    text=(DEST/'Install-Coop.ps1').read_bytes().decode('utf-8-sig')
    if text.count("'-v0_7_3-marcus-upgrade','-v0_7_7-upgrade'))")!=1:raise ValueError('Installer suffix contract')
    for path in DEST.glob('*.ps1'):
        before=path.read_bytes().decode('utf-8-sig')
        after=before.replace("Version='"+manifest['version']+"'","Version='"+VERSION+"'")
        for old,new in ((client,new_client),(server,new_server)):
            after=after.replace(sha(old),sha(new)).replace(sha(old).upper(),sha(new).upper())
        if before!=after:path.write_bytes(b'\xef\xbb\xbf'+after.encode('utf-8'))
    status=load(DEST/'GAMEPLAY-STATUS.json')
    status.update(version=VERSION,source_package=SOURCE.name,native_gameplay_identical_to=None,
        qte_local_actor=cr,qte_host_milestones=sr,combined_package_gameplay_verified=False,
        guest_qte_synchronization_fixed=False,host_only_qte_input=False)
    write(DEST/'GAMEPLAY-STATUS.json',status)
    for name in ('QTE-HOST-ACTOR-TEST.md','CHANGELOG.md'):(DEST/name).write_text(NOTE,encoding='utf-8')
    copy_local_sources(DEST/'src',('qte_spawn_local_bus.py','patch_qte_spawn_local_bus.py',
        'test_qte_spawn_local_bus.py','build_qte_spawn_candidate.py','qte_host_milestones.py',
        'patch_qte_host_milestones.py','test_qte_host_milestones.py','build_qte_host_candidate.py',
        'snapshot_qte_roles.py','test_snapshot_qte_candidate.py','coop_summary.py','inspect_qte_spawn_dump.py'))
    files=[]
    for path in sorted(DEST.rglob('*')):
        if path.is_file() and path.name!='package-manifest.json':
            if path.suffix.lower() in ('.exe','.dll','.sb','.toc','.ebx','.dmp','.sqlite3'):
                raise ValueError('Game/private binary in package')
            data=path.read_bytes();files.append(dict(path=path.relative_to(DEST).as_posix(),bytes=len(data),sha256=sha(data)))
    manifest.update(version=VERSION,files=files,client_sha256=sha(new_client),server_sha256=sha(new_server))
    write(DEST/'package-manifest.json',manifest);verify_manifest(DEST,manifest)
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(DEST.rglob('*')):
            if path.is_file():z.write(path,DEST.name+'/'+path.relative_to(DEST).as_posix())
    receipt=dict(version=VERSION,package=str(DEST),archive=str(archive),bytes=archive.stat().st_size,
        sha256=sha(archive.read_bytes()),client_sha256=sha(new_client),server_sha256=sha(new_server),
        client=cr,server=sr,files=len(files),installed=False,published=False,gameplay_verified=False)
    write(ROOT/'outputs/qte-night-20261114/host-actor-build-receipt.json',receipt)
    print(json.dumps({k:receipt[k] for k in ('version','sha256','client_sha256','server_sha256','files')}))


if __name__=='__main__':main()
