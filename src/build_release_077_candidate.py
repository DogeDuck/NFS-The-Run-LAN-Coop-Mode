"""Assemble current Solo/launcher/audio fixes into an OFFLINE candidate. Never installs/publishes.

Frozen0.7.6 native patches are preserved. Copy an explicit script cohort, keep addon bytes exact,
then regenerate every package checksum. Experimental gameplay patches are separate opt-ins.
"""
import argparse
import json
from pathlib import Path
import shutil
import zipfile

from build_test_package import copy_local_sources, sha

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'release/TheRun-Coop-v0.7.6-TEST'
VERSION='0.7.7-OFFLINE-CANDIDATE'
COHORT=('Start-Solo.ps1','Coop-SoloExe.ps1','Start-Coop.ps1','Restore-Installation.ps1',
        'Coop-Language.ps1','Connect-Coop.ps1','Coop-MusicMix.ps1')
# R4+ (Claude 11.11.): personal graphics settings in the launcher.
COHORT_R4=COHORT+('Coop-Graphics.ps1',)
COHORT_R5=COHORT_R4+('Start-CoopWindow.ps1',)
LEGACY_VERSIONS=('0.7.7-OFFLINE-CANDIDATE','0.7.7-OFFLINE-CANDIDATE-R2','0.7.7-OFFLINE-CANDIDATE-R3')


def cohort_for(version):
    if version in LEGACY_VERSIONS:return COHORT
    return COHORT_R4 if version=='0.7.7-OFFLINE-CANDIDATE-R4' else COHORT_R5


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')


def verify_manifest(directory,manifest):
    expected=set()
    for entry in manifest['files']:
        relative=entry['path']
        path=directory/relative
        if not path.resolve().is_relative_to(directory.resolve()):
            raise ValueError('Package path escapes its directory')
        data=path.read_bytes()
        if len(data)!=entry['bytes'] or sha(data)!=entry['sha256']:
            raise ValueError('Package file differs: '+relative)
        expected.add(relative)
    actual={p.relative_to(directory).as_posix() for p in directory.rglob('*')
            if p.is_file() and p.name!='package-manifest.json'}
    if actual!=expected:
        raise ValueError('Package contains missing or unlisted files')


STUB_OLD=("# Ein Startpunkt neben der Spiel-EXE (Koop + Solo). Restore-Installation entfernt ihn wieder.\r\n"
          "$stub=Join-Path $game 'The Run starten (Koop + Solo).cmd'\r\n")
EARLY_OLD="if(!$changes.Count){& $music -GamePath $game -Mode Apply;Save-CoopSettings $game;Write-Output 'Koop-Dateien sind bereits bereit.';return}"


def patch_installer_stub(text):
    """Claude 11.11.: the game-folder starter must follow the installed package even for script-only updates.

    The frozen 0.7.6 installer returns early ('bereits bereit') when no game file changes, before it rewrites
    'The Run starten (Koop + Solo).cmd'. A script-only update (e.g. 0.7.6 -> 0.7.7) then keeps starting the old
    package. Move the unchanged stub logic into a function and call it on both paths. A foreign file with the
    same name (without the TheRunStoryCoop-Starter marker) stays untouched, as before.
    """
    if text.count(STUB_OLD)!=1 or text.count(EARLY_OLD)!=1 or 'Set-CoopStarterStub' in text:
        raise ValueError('Frozen installer stub layout changed')
    start=text.index(STUB_OLD)
    end=text.index('\r\n',text.index('if(!(Test-Path -LiteralPath $stub)',start))+2
    body=text[start:end].split('\r\n')[1:-1]  # drop the comment line and the trailing empty element
    function=('# Startpunkt neben der Spiel-EXE (Koop + Solo) zeigt immer auf dieses Paket, auch bei reinen Skript-Updates.\r\n'
              '# Restore-Installation entfernt ihn wieder; eine fremde gleichnamige Datei bleibt unberuehrt.\r\n'
              'function Set-CoopStarterStub{\r\n'+''.join('    '+line+'\r\n' for line in body)+'}\r\n')
    text=text[:start]+'Set-CoopStarterStub\r\n'+text[end:]
    early="if(!$changes.Count){& $music -GamePath $game -Mode Apply;Save-CoopSettings $game;Set-CoopStarterStub;Write-Output 'Koop-Dateien sind bereits bereit.';return}"
    return text.replace(EARLY_OLD,function+early,1)


def build(destination,version=VERSION):
    VERSION=version
    if version not in LEGACY_VERSIONS+('0.7.7-OFFLINE-CANDIDATE-R4','0.7.7-OFFLINE-CANDIDATE-R5'):
        raise ValueError('Explicit internal candidate version required')
    destination=Path(destination).resolve()
    if not destination.is_relative_to(ROOT/'outputs'):
        raise ValueError('Offline candidates must stay under project outputs')
    archive=Path(str(destination)+'.zip')
    if destination.exists() or archive.exists():
        raise ValueError('Candidate already exists; never overwrite')
    old=load(SOURCE/'package-manifest.json')
    verify_manifest(SOURCE,old)
    addon_root=ROOT/'third_party/coop-addons'
    addons=load(addon_root/'manifest.json')
    for relative,digest in addons['files'].items():
        path=addon_root/relative
        if not path.resolve().is_relative_to(addon_root.resolve()) or sha(path.read_bytes())!=digest:
            raise ValueError('Addon source differs: '+relative)
    shutil.copytree(SOURCE,destination)
    cohort=cohort_for(VERSION)
    if VERSION not in LEGACY_VERSIONS:
        # Windows Script Host rejects a UTF-8 BOM (800A0408 at line 1); since 0.7.3 both entry points carried one.
        for path in destination.glob('*.vbs'):
            data=path.read_bytes()
            if data.startswith(b'\xef\xbb\xbf'):data=data[3:]
            if any(byte>127 for byte in data):raise ValueError('VBScript entry point must stay plain ASCII: '+path.name)
            path.write_bytes(data)
    for name in cohort:
        text=(ROOT/'package_tools'/name).read_text(encoding='utf-8-sig')
        for previous in ('0.2-TEST','0.7.6-TEST'):
            text=text.replace("Version='"+previous+"'","Version='"+VERSION+"'")
        # Do not let an internal candidate auto-install a public package while testing it.
        if name=='Connect-Coop.ps1':
            needle='Difficulty=1;AutoUpdate=$true;'
            if text.count(needle)!=1:raise ValueError('Launcher default marker changed')
            text=text.replace(needle,'Difficulty=1;AutoUpdate=$false;',1)
        (destination/name).write_text(text,encoding='utf-8-sig',newline='\r\n')
    if VERSION=='0.7.7-OFFLINE-CANDIDATE-R5':
        entry=(ROOT/'package_tools/Launch-Coop.vbs').read_bytes()
        if entry.startswith(b'\xef\xbb\xbf') or any(byte>127 for byte in entry):
            raise ValueError('Launcher entry point must stay plain ASCII')
        (destination/'Launch-Coop.vbs').write_bytes(entry)
    # Merge verified exact addon files; never rewrite nested README/config encodings.
    for path in addon_root.rglob('*'):
        if path.is_file():
            relative=path.relative_to(addon_root)
            target=destination/'addons'/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,target)
    installer=destination/'Install-Coop.ps1'
    # Read bytes: read_text would turn the frozen CRLF into LF and break the exact layout checks below.
    text=installer.read_bytes().decode('utf-8-sig').replace("Version='0.7.6-TEST'","Version='"+VERSION+"'")
    if VERSION not in ('0.7.7-OFFLINE-CANDIDATE','0.7.7-OFFLINE-CANDIDATE-R2'):
        text=patch_installer_stub(text)  # R3+: starter also follows script-only updates
    installer.write_bytes(b'\xef\xbb\xbf'+text.encode('utf-8'))
    # Restore-Installation.cmd uses Windows PowerShell5.1 as well. Do not depend
    # on Get-FileHash auto-loading a utility module from an inherited PS7 path.
    core=destination/'Coop-Core.ps1'
    text=core.read_text(encoding='utf-8-sig')
    core_old="function Get-CoopFileHash([string]$Path){return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()}"
    replacement='''function Get-CoopFileHash([string]$Path){
    $stream=[IO.File]::OpenRead($Path)
    $sha=[Security.Cryptography.SHA256]::Create()
    try{return ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant()}
    finally{$sha.Dispose();$stream.Dispose()}
}'''
    if text.count(core_old)!=1:raise ValueError('Frozen core hash function changed')
    core.write_text(text.replace(core_old,replacement),encoding='utf-8-sig',newline='\r\n')
    notes='''# 0.7.7 offline candidate / Offline-Kandidat

## Deutsch
- Solo verwendet während der Sitzung die LAN-Grund-EXE ohne Koop-Code und stellt danach die Koop-EXE wieder her. Abgebrochene Sitzungen werden erkannt.
- Die Solo-Dateiprüfung funktioniert auch unter PowerShell5.1 mit einem geerbten PS7-Modulpfad.
- Claudes Musikmix und persönlicher Musik-Mix-Schalter enthalten: Global_Music+25dB, Szenen+8dB, Film-Seite Rennmusik+6dB/Autos-4dB. Vorgemischte Szenen heben auch Effekte/Dialog gemeinsam an.
- Schwierigkeit, Updater, Garage, NPC-/Team-/Battle-Fixes aus0.7.6 bleiben enthalten. Native Client-/Server-Patches unverändert.
- Nicht installiert/veröffentlicht und nicht als Gesamtpaket im Spiel getestet. QTE-Synchronisierung, Cutscene-Kollisionen und Tankstellen-Einfahrt bleiben offen. Verworfenes QTE-LOCAL nicht enthalten.
- Kandidaten-Autoupdate standardmäßig aus. Solo, Musikschalter und Hörtest als Nächstes mit Nutzer prüfen. Keine Spielstände zurückspielen.
- Ab R3: Der Starter im Spielordner folgt auch reinen Skript-Updates. Ab R4: persönliche Grafik-Einstellungen im Launcher (FPS, Schatten, Texturfilter, Sichtfeld; Standard = bisheriges Profil) und VBS-Starter ohne BOM (Launch-Coop.vbs, Garage-Fenster.vbs starteten seit 0.7.3 nicht).
- Ab R5: VBS-Launcher startet das sichtbare Formular in einem eigenen Prozess ohne Konsolenfenster; SW_HIDE betrifft nur den kurzen Bootstrap. Garage verwendet diesen Mechanismus bereits.

## English
- Solo uses the LAN base executable without co-op code during the session, then restores the co-op executable. Interrupted sessions can be recovered.
- Solo file verification also works in Windows PowerShell5.1 with an inherited PS7 module path.
- Includes Claude's audio mix and personal Music mix toggle: Global_Music+25dB, cinematic streams+8dB, Film side race music+6dB/cars-4dB. Premixed cinematic streams also raise their effects/dialogue.
- Preserves0.7.6 difficulty, updater, garage, NPC/team/Battle fixes. Native client/server patches are unchanged.
- Not installed/published or tested in-game as a combined package. QTE synchronization, cutscene collisions and automatic gas-station entry remain unresolved. Rejected QTE-LOCAL experiment is excluded.
- Candidate auto-update defaults to off. Next: joint Solo/audio-toggle/listening test. Never restore a player's save.
- From R3: the game-folder starter also follows script-only updates. From R4: personal graphics settings in the launcher (FPS, shadows, texture filtering, field of view; defaults = previous profile) and VBS entry points without BOM (Launch-Coop.vbs, Garage-Fenster.vbs failed since 0.7.3).
- From R5: the VBS launcher opens the visible form in a separate process without a console window; SW_HIDE only affects the short bootstrap. The garage already uses this mechanism.
'''
    (destination/'CHANGELOG.md').write_text(notes,encoding='utf-8')
    (destination/'ADDONS.md').write_text(notes,encoding='utf-8')
    status=load(destination/'GAMEPLAY-STATUS.json')
    status.update(version=VERSION,published=False,installed=False,combined_package_gameplay_verified=False,
                  native_gameplay_identical_to='0.7.6-TEST',solo_without_coop_code=True,
                  solo_hash_cmdlet_independent=True,core_hash_cmdlet_independent=True,
                  music_mix_toggle=True,cinematic_audio_mix=True,
                  guest_qte_synchronization_fixed=False,qte_local_binding_experiment_enabled=False,
                  cutscene_collision_fix_included=False)
    if VERSION not in LEGACY_VERSIONS:
        status.update(launcher_graphics_settings=True,vbs_entry_points_without_bom=True,installer_starter_follows_updates=True,
                      vsync_controlled_by_launcher=False)
    write(destination/'GAMEPLAY-STATUS.json',status)
    sources=copy_local_sources(destination/'src',(
        'build_release_077_candidate.py','offline_test_images.py','test_offline_test_images.py',
        'test_solo_without_coop_exe.py','test_solo_exe_ps5.py','test_start_solo.py',
        'build_audio_mix_cinema.py','render_audio_mix_cinema.py','test_audio_mix_cinema.py',
        'test_launcher_music_mix.py','test_launcher_bilingual.py','test_launcher_garage_language.py',
        'test_release_077_candidate.py')+(() if VERSION in LEGACY_VERSIONS else (
        'test_launcher_graphics.py','test_installer_starter_stub.py','test_vbs_launchers.py'))+
        (('test_vbs_window_visibility.py',) if VERSION=='0.7.7-OFFLINE-CANDIDATE-R5' else ()))
    write(destination/'validation.json',dict(offline_candidate=True,gameplay_verified=False,
        native_changes=False,source_cohort=list(cohort),sources=sources,
        note='See outputs/night-work-20261111-0046 for actual offline test receipts.'))
    for relative,digest in addons['files'].items():
        if sha((destination/'addons'/relative).read_bytes())!=digest:
            raise ValueError('Addon bytes changed during packaging')
    for stem in ('client','server'):
        if (destination/f'patches/{stem}.json').read_bytes()!=(SOURCE/f'patches/{stem}.json').read_bytes():
            raise ValueError('Baseline gameplay patch unexpectedly changed')
    files=[]
    for path in sorted(destination.rglob('*')):
        if path.is_file() and path.name!='package-manifest.json':
            if path.suffix.lower() in ('.exe','.dll','.sb','.toc','.ebx','.dmp','.sqlite3'):
                raise ValueError('Private or game binary cannot be packaged')
            data=path.read_bytes()
            files.append(dict(path=path.relative_to(destination).as_posix(),bytes=len(data),sha256=sha(data)))
    manifest=dict(old,version=VERSION,files=files,gameplay_verified=False)
    write(destination/'package-manifest.json',manifest)
    verify_manifest(destination,manifest)
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as output:
        for path in sorted(destination.rglob('*')):
            if path.is_file():output.write(path,destination.name+'/'+path.relative_to(destination).as_posix())
    receipt=dict(version=VERSION,package=str(destination),archive=str(archive),files=len(files),
        bytes=archive.stat().st_size,sha256=sha(archive.read_bytes()),
        client_sha256=manifest['client_sha256'],server_sha256=manifest['server_sha256'],
        installed=False,published=False,gameplay_verified=False)
    # Keep the frozen R2 receipt; later candidates get their own receipt file.
    legacy=VERSION in ('0.7.7-OFFLINE-CANDIDATE','0.7.7-OFFLINE-CANDIDATE-R2')
    write(ROOT/'outputs'/('v0.7.7-offline-build-receipt.json' if legacy else 'v'+VERSION+'-build-receipt.json'),receipt)
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/TheRun-Coop-v0.7.7-OFFLINE-CANDIDATE')
    parser.add_argument('--version',default=VERSION)
    args=parser.parse_args()
    print(json.dumps(build(args.output,args.version)))
