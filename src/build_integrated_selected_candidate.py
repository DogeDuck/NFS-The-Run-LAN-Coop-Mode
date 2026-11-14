"""One current R2 + launcher/HUD/R4 basis. Build only; never install or publish."""
import argparse,base64,gzip,json,re,shutil,zipfile
from pathlib import Path
from build_release_077_candidate import ROOT,load,write,verify_manifest
from build_test_package import sha,apply,reverse_apply,delta,copy_local_sources
from offline_test_images import image
from patch_qte_spawn_local_bus import build as actor_build
from patch_qte_host_milestones import build as host_build

SOURCE=ROOT/'outputs/TheRun-Coop-v0.7.7-RACESTART-QTE-HOST-ACTOR-CANDIDATE-R2'
INSTALLER=ROOT/'outputs/TheRun-Coop-v0.7.7-INSTALLER-NIGHT-R4'
OUT=ROOT/'outputs/offline-selected-20261114-2133'
FRONTEND=('Coop-VersionCleanup.ps1','Coop-UpdateStage.ps1','Coop-PowerShellRuntime.ps1','Bootstrap-PowerShell7.ps1')

def replace_once(text,old,new):
    if text.count(old)!=1:raise ValueError('Source contract differs: '+old[:100])
    return text.replace(old,new,1)

def pin_garage_scripts(server_text,unlock_text,client,server):
    """A new native cohort must not accidentally keep old garage SHA allowlists."""
    from pe_image_readonly import PE32
    getter=re.search(r"GarageServerGetter='([0-9a-f]+)'",server_text)
    if not getter or PE32(server).read(0x13EAF90,len(getter[1])//2).hex()!=getter[1]:
        raise ValueError('Garage server native getter differs')
    pattern=r"\$script:GarageServerBuilds=@\([\s\S]*?\)\s*(?=\$script:GarageServerGetter)"
    server_text,count=re.subn(pattern,"$script:GarageServerBuilds=@('"+sha(server).upper()+"')\n",server_text)
    if count!=1:raise ValueError('Garage server allowlist contract differs')
    unlock_text=replace_once(unlock_text,'C9D48E500EF82EFC642EDF2DB848A9072E56FBC114E283173D6E7E58BAC634A6',sha(client).upper())
    return server_text,unlock_text

def assert_slider_audio(script):
    encoded=re.search(r"\$encoded='([^']+)'",script)
    if not encoded:raise ValueError('Missing audio payload')
    payload=json.loads(gzip.decompress(base64.b64decode(encoded[1])))
    if payload.get('music_db')!=0 or not {'Original','Target'}<=set(payload.get('states',[])):
        raise ValueError('Only slider mix without global music boost may be shipped')
    if "[ValidateSet('Apply','Restore')]" not in script:
        raise ValueError('Audio must expose only Apply current target / Restore original')
    return payload

def personalize_installer(text):
    anchor="$specialK=Join-Path $game 'd3d11.dll'"
    text=replace_once(text,anchor,"""# Personal INIs are preserved byte-exactly; defaults are used only when missing.
foreach($relative in @('Scripts\\NFSTR_LANOnlineHelper.ini','Scripts\\NFSTR_DefinitiveEdition.ini')){
 $existing=Join-Path $game $relative
 if(Test-Path -LiteralPath $existing -PathType Leaf){$staged[$relative]=[IO.File]::ReadAllBytes($existing)}
}
foreach($name in @('launcher.json','settings.json')){
 $personal=Join-Path $script:CoopStateRoot $name
 if(Test-Path -LiteralPath $personal){
  if((Get-Item -LiteralPath $personal).Length -gt 262144){throw 'Personal settings too large / Persoenliche Einstellungen zu gross.'}
  $parsed=Get-Content -LiteralPath $personal -Raw|ConvertFrom-Json -ErrorAction Stop
  if($parsed -isnot [pscustomobject]){throw 'Personal settings must be an object / Persoenliche Einstellungen muessen ein Objekt sein.'}
 }
}
"""+anchor)
    marker='function Invoke-CoopRetiredCleanupAfterSuccess {'
    helper="""function Invoke-CoopInstallMusic {
 $enabled=$true;$personal=Join-Path $script:CoopStateRoot 'launcher.json'
 if(Test-Path -LiteralPath $personal){try{$saved=Get-Content -LiteralPath $personal -Raw|ConvertFrom-Json;if($saved.MusicMix -is [bool]){$enabled=$saved.MusicMix}}catch{throw 'Personal settings damaged; original preserved / Persoenliche Einstellungen beschaedigt; Original bleibt erhalten.'}}
 & $music -GamePath $game -Mode $(if($enabled){'Apply'}else{'Restore'})
}
function Write-CoopInstallFile([string]$Path,[byte[]]$Bytes,[string]$Expected){
 $temporary=Join-Path ([IO.Path]::GetDirectoryName($Path)) ([IO.Path]::GetRandomFileName())
 try{
  [IO.File]::WriteAllBytes($temporary,$Bytes)
  if((Get-CoopFileHash $temporary) -ine $Expected){throw 'Staged file differs / Vorbereitete Datei weicht ab.'}
  if(Test-Path -LiteralPath $Path){[IO.File]::Replace($temporary,$Path,[NullString]::Value)}else{[IO.File]::Move($temporary,$Path)}
 }finally{if(Test-Path -LiteralPath $temporary){Remove-Item -LiteralPath $temporary}}
}
"""
    text=replace_once(text,marker,helper+marker)
    if text.count('& $music -GamePath $game -Mode Apply')!=2:raise ValueError('Two music success paths required')
    text=text.replace('& $music -GamePath $game -Mode Apply','Invoke-CoopInstallMusic')
    a=text.index('foreach($entry in $changes){',text.index("$manifestPath=Join-Path $backup 'install-manifest.json'"))
    b=text.index("$manifest.Status='installed'",a)
    block=text[a:b]
    block=replace_once(block,'    if($entry.AfterExists){','    $applied+= $entry\n    if($entry.AfterExists){')
    block=replace_once(block,'        [IO.File]::WriteAllBytes($target,$staged[$entry.RelativePath])',
                       '        Write-CoopInstallFile $target $staged[$entry.RelativePath] $entry.AfterSha256')
    text=text[:a]+"$applied=@()\ntry{\n"+block+"""}catch{
 $failure=$_;$restored=0
 foreach($entry in @($applied|Select-Object -Last 1000)){
  $target=Join-Path $game $entry.RelativePath
  if($entry.AfterExists -and (!(Test-Path -LiteralPath $target) -or (Get-CoopFileHash $target) -ne $entry.AfterSha256)){continue}
  if($entry.BeforeExists){
   $original=Join-Path $backup $entry.RelativePath
   if((Get-CoopFileHash $original) -ne $entry.BeforeSha256){continue}
   Write-CoopInstallFile $target ([IO.File]::ReadAllBytes($original)) $entry.BeforeSha256
  }elseif(Test-Path -LiteralPath $target){Remove-Item -LiteralPath $target}
  $restored++
 }
 $manifest.Status='failed-rollback-attempted';$manifest.RollbackFiles=$restored
 $manifest|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $manifestPath -Encoding utf8
 throw $failure
}
"""+text[b:]
    return text

def preserve_core_settings(text):
    a=text.index('function Save-CoopSettings(');b=text.index('function Assert-CoopClosed',a)
    text=text[:a]+"""function Save-CoopSettings([string]$Directory){
    [void][IO.Directory]::CreateDirectory($script:CoopStateRoot)
    $path=Join-Path $script:CoopStateRoot 'settings.json';$data=[ordered]@{}
    if(Test-Path -LiteralPath $path){$old=Get-Content -LiteralPath $path -Raw -Encoding utf8|ConvertFrom-Json -ErrorAction Stop;foreach($p in $old.PSObject.Properties){$data[$p.Name]=$p.Value}}
    $data.GameDirectory=$Directory;$tmp=Join-Path $script:CoopStateRoot ([IO.Path]::GetRandomFileName())
    try{[IO.File]::WriteAllText($tmp,($data|ConvertTo-Json -Depth 16),[Text.UTF8Encoding]::new($false));if(Test-Path -LiteralPath $path){[IO.File]::Replace($tmp,$path,[NullString]::Value)}else{[IO.File]::Move($tmp,$path)}}finally{if(Test-Path -LiteralPath $tmp){Remove-Item -LiteralPath $tmp}}
}
"""+text[b:]
    old="$resolved=[IO.Path]::GetFullPath($Requested.Trim('\"')).TrimEnd('\\')"
    new=old+"\n    if((Test-Path -LiteralPath $resolved -PathType Leaf) -and [IO.Path]::GetFileName($resolved) -ieq 'Need For Speed The Run.exe'){$resolved=[IO.Path]::GetDirectoryName($resolved)}"
    return replace_once(text,old,new)

def build(version='0.7.8-OFFLINE-CANDIDATE',cutscene=False,team4=False,stations=False,qte_delta=False):
    if not re.fullmatch(r'0\.7\.8-[A-Z0-9-]*CANDIDATE(?:-R[0-9]+)?',version):raise ValueError('Internal version only')
    dest=ROOT/('outputs/TheRun-Coop-v'+version);archive=Path(str(dest)+'.zip')
    if dest.exists() or archive.exists():raise ValueError('Frozen candidate exists; never overwrite')
    manifest=load(SOURCE/'package-manifest.json');verify_manifest(SOURCE,manifest)
    verify_manifest(INSTALLER,load(INSTALLER/'package-manifest.json'))
    old_client,_=actor_build(image('client','integrated'))
    raw_server=(ROOT/'outputs/offline-3h-20261113/ghidra/NFSTR_Server_BCDAFBF8.exe').read_bytes()
    old_server,_=host_build(raw_server)
    assert (sha(old_client),sha(old_server))==(manifest['client_sha256'],manifest['server_sha256'])
    client,server=old_client,old_server;native_parts={}
    if qte_delta:
        from patch_qte_delta_current import build as delta_build
        client,native_parts['qte_finite_negative_delta']=delta_build(client)
    if team4:
        from patch_team_finish_four import build as team_build
        client,native_parts['team_finish_four']=team_build(client)
    if cutscene:
        from patch_cutscene_ai import build as scene_build
        client,native_parts['cutscene']=scene_build(client)
    if stations:
        from patch_gas_entry_guard import build as station_build,R2 as station_source
        server,native_parts['station_entry']=station_build(server,station_source)
    shutil.copytree(SOURCE,dest)
    # Current own scripts and previews; frozen native deltas remain the base.
    for path in (ROOT/'package_tools').rglob('*'):
        if path.is_file():
            target=dest/path.relative_to(ROOT/'package_tools');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    for name in FRONTEND:shutil.copy2(ROOT/name,dest/name)
    for name in ('Install-Coop.ps1','Update-Coop.ps1','PowerShell7.cmd','Launch-Coop.vbs','Garage-Fenster.vbs'):
        shutil.copy2(INSTALLER/name,dest/name)
    server_script,unlock_script=pin_garage_scripts((dest/'Garage-Core.ps1').read_text(encoding='utf-8-sig'),
        (dest/'Unlock-Coop-Garage.ps1').read_text(encoding='utf-8-sig'),client,server)
    (dest/'Garage-Core.ps1').write_text(server_script,encoding='utf-8-sig')
    (dest/'Unlock-Coop-Garage.ps1').write_text(unlock_script,encoding='utf-8-sig')
    installer=personalize_installer((dest/'Install-Coop.ps1').read_text(encoding='utf-8-sig'))
    (dest/'Install-Coop.ps1').write_text(installer,encoding='utf-8-sig')
    core=preserve_core_settings((dest/'Coop-Core.ps1').read_text(encoding='utf-8-sig'))
    (dest/'Coop-Core.ps1').write_text(core,encoding='utf-8-sig')
    # Latest pinned addon cohort, including HUD and revised cinema mix.
    addons=load(ROOT/'third_party/coop-addons/manifest.json')
    assert_slider_audio((ROOT/'third_party/coop-addons/music25/NFS-Audio-Patch.ps1').read_text(encoding='utf-8-sig'))
    legacy_audio=dest/'addons/music25';slider_audio=dest/'addons/audio-slider'
    for checked in (legacy_audio,slider_audio):
        if not checked.resolve().is_relative_to(dest.resolve()):raise ValueError('Audio path escapes candidate')
    if legacy_audio.exists():legacy_audio.rename(slider_audio)
    shipped_addons={}
    for name,digest in addons['files'].items():
        p=ROOT/'third_party/coop-addons'/name
        if sha(p.read_bytes())!=digest:raise ValueError('Addon differs: '+name)
        shipped=name.replace('music25/','audio-slider/',1) if name.startswith('music25/') else name
        target=dest/'addons'/shipped;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
        shipped_addons[shipped]=digest
    addons['files']=shipped_addons
    write(dest/'addons/manifest.json',addons)
    for stem,old,new,filename in (('client',old_client,client,'Need For Speed The Run.exe'),
                                 ('server',old_server,server,'NFSTR_Server.exe')):
        if old==new:continue
        for path in (dest/'patches').glob(stem+'*.json'):
            base=reverse_apply(old,load(path));d=delta(filename,base,new)
            assert apply(base,d)==new;write(path,d)
        write(dest/('patches/'+stem+'-r2-upgrade.json'),delta(filename,old,new))
    if client!=old_client or server!=old_server:
        p=dest/'Install-Coop.ps1';s=p.read_text(encoding='utf-8-sig');s=replace_once(s,"'-v0_7_7-upgrade'))","'-v0_7_7-upgrade','-r2-upgrade'))");p.write_text(s,encoding='utf-8-sig')
    # Version record is read from the package, including direct CLI launches.
    p=dest/'Start-Coop.ps1';s=p.read_text(encoding='utf-8-sig')
    s=replace_once(s,"Version='0.2-TEST'","Version=([string](Get-Content -LiteralPath (Join-Path $PSScriptRoot 'package-manifest.json') -Raw|ConvertFrom-Json).version)")
    p.write_text(s,encoding='utf-8-sig')
    updater=dest/'Update-Coop.ps1';s=updater.read_text(encoding='utf-8-sig')
    s=s.replace("'launcher.json','language.json','car-preferences.json','settings.json'","'launcher.json','language.json','car-preferences.json','garage-selection.json','garage-profiles.json','settings.json'")
    updater.write_text(s,encoding='utf-8-sig')
    for path in dest.glob('*.ps1'):
        s=path.read_text(encoding='utf-8-sig')
        s=s.replace('addons\\music25','addons\\audio-slider').replace("'music25\\NFS-Audio-Patch.ps1'","'audio-slider\\NFS-Audio-Patch.ps1'")
        for old in (manifest['version'],'0.7.7-INSTALLER-NIGHT-R4'):s=s.replace("Version='"+old+"'","Version='"+version+"'")
        for a,b in ((old_client,client),(old_server,server)):
            if a!=b:s=s.replace(sha(a),sha(b)).replace(sha(a).upper(),sha(b).upper())
        path.write_text(s,encoding='utf-8-sig')
    status=load(dest/'GAMEPLAY-STATUS.json')
    status.update(version=version,source_package=SOURCE.name,combined_package_gameplay_verified=False,
        native_parts=native_parts,host_only_qte_input=False,guest_qte_autopass=False,
        garage_favorites_presets=True,version_control_channel=True,session_overview=True,
        diagnostics_opt_in=True,diagnostics_memory_hooks=False,repair_verified_sources=True,
        personal_ini_preservation=True,installer_r4_integrated=True,hud_background_variants=True,
        native_team4_candidate=team4,native_station_candidate=stations,native_cutscene_candidate=cutscene,
        qte_finite_negative_delta_candidate=qte_delta,
        server_ai_reference_guard_enabled=False,full_four_player_support=False,
        audio_slider_only=True,global_music_boost_db=0,fixed_music_25db_selectable=False,
        user_confirmed_highway20_fixed=True,user_confirmed_de_autosound_fixed=True)
    write(dest/'GAMEPLAY-STATUS.json',status)
    note='''# Internal integrated candidate / Gemeinsamer interner Kandidat

DE: Aktuelle R2-Basis + Garage-Favoriten/Sets, Sitzungsübersicht, Versionsprüfung,
freiwillige begrenzte Diagnose je Spieler unter TheRun-Coop-Logs, Reparatur aus
geprüften Quellen, R4-Installer/Updater/PS7/Altversionsschutz, Tacho-Auswahl.
Persönliche vorhandene INIs bleiben bytegenau erhalten, Musik-Auswahl bleibt persönlich.
Audio: ausschließlich Film-Experience-Reglermix, kein globaler +25-dB-Boost.
TCP25212 für die Host-Versionsprüfung zusätzlich zu UDP25200 und Garage TCP25211.
Host zuerst starten, dann Gäste. Die Übersicht meldet Launcher-Kontakte, keine
native Rennrangliste. Diagnose ist standardmäßig AUS, keine Hooks/Frida/Uploads.
Noch nicht installiert/veröffentlicht; gemeinsame Paketwirkung im Spiel ungeprüft.
Gast-Autopass und vollständige HOST-QTE sind nicht eingeschaltet. Kein Save-Restore.
Cutscene-Native ist nur in der ausdrücklich experimentellen Szenenvariante enthalten.

EN: Internal candidate. Current R2 + garage favorites/presets, session overview,
pre-launch host version check, opt-in bounded per-player logs, verified-source
repair, R4 installer/updater/portable PowerShell7, safe retired-package cleanup and
HUD choices. Existing personal INIs are preserved byte-exactly. Diagnostics default
Only the Film Experience slider mix is shipped; no global +25 dB boost is selectable.
OFF; no memory hooks, Frida or uploads. TCP25212 is required for the version check.
Start the host first. Session contacts are not native race standings. No automatic
guest QTE pass or complete host-only QTE implementation. Gameplay integration remains
unverified; not installed or published. No save restoration.
'''
    for name in ('INTEGRATED-CANDIDATE.md','CHANGELOG.md'):(dest/name).write_text(note,encoding='utf-8')
    for name,de in (('README.md',False),('README-DE.md',True),('README-EN.md',False)):
        p=dest/name
        if p.is_file():
            lead=('**Interner Kandidat '+version+' — kein neues Release.** Neu: Garage-Sets/Favoriten, freiwillige Diagnose, Sitzungsübersicht und Reparatur. Anleitung: [Sitzung und Diagnose](SESSION-DE.md). Gameplay-Grenzen: [Kandidatenstatus](INTEGRATED-CANDIDATE.md).\n\n' if de else
                  '**Internal candidate '+version+' — not a new public release.** New garage presets/favorites, opt-in diagnostics, session overview and repair. Read [session guide](SESSION-EN.md) and [candidate status](INTEGRATED-CANDIDATE.md).\n\n')
            p.write_text(lead+p.read_text(encoding='utf-8-sig'),encoding='utf-8')
    copy_local_sources(dest/'src',('build_integrated_selected_candidate.py','test_garage_profiles.py','test_session_tools.py','test_repair_selected.py','test_integrated_selected.py','test_integrated_native.py',
        'patch_team_finish_four.py','team_finish_four_adapter.py','patch_gas_entry_guard.py','gas_entry_guard_adapter.py',
        'patch_cutscene_ai.py','cutscene_ai_adapter.py','ant_scene_scope.py','server_ai_reference_guard.py',
        'patch_qte_delta_current.py','ant_delta_guard_adapter.py','coop_summary.py','test_launcher_diagnostic_summary.py','test_session_config.py','test_audio_slider_package.py'))
    files=[]
    for p in sorted(dest.rglob('*')):
        if p.is_file() and p.name!='package-manifest.json':
            if p.suffix.lower() in ('.exe','.dll','.sb','.toc','.ebx','.dmp','.sqlite3'):raise ValueError('Game/private binary in candidate')
            raw=p.read_bytes();files.append(dict(path=p.relative_to(dest).as_posix(),bytes=len(raw),sha256=sha(raw)))
    manifest.update(version=version,files=files,client_sha256=sha(client),server_sha256=sha(server))
    write(dest/'package-manifest.json',manifest);verify_manifest(dest,manifest)
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(dest.rglob('*')):
            if p.is_file():z.write(p,dest.name+'/'+p.relative_to(dest).as_posix())
    receipt=dict(package=str(dest),archive=str(archive),version=version,sha256=sha(archive.read_bytes()),files=len(files),client_sha256=sha(client),server_sha256=sha(server),cutscene=cutscene,team4=team4,stations=stations,qte_delta=qte_delta,installed=False,published=False,gameplay_verified=False)
    write(OUT/('integrated-'+version+'-receipt.json'),receipt)
    print(json.dumps(receipt));return dest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--version',default='0.7.8-OFFLINE-CANDIDATE');p.add_argument('--cutscene',action='store_true');p.add_argument('--team4',action='store_true');p.add_argument('--stations',action='store_true');p.add_argument('--qte-delta',action='store_true');a=p.parse_args();build(a.version,a.cutscene,a.team4,a.stations,a.qte_delta)
