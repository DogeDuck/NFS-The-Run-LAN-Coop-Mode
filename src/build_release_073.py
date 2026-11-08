"""Release only live-confirmed Battle code plus tested bilingual launcher/garage."""
import shutil,zipfile
from pathlib import Path
from build_battle_phase_candidate import ROOT,load,write,sha
from build_test_package import apply,reverse_apply,delta,copy_local_sources

SOURCE=ROOT/'outputs/TheRun-Coop-v0.7.2-BATTLE-PHASE-CANDIDATE'
DEST=ROOT/'release/TheRun-Coop-v0.7.3-TEST'
VERSION='0.7.3-TEST'
CLIENT='c3fba53c787f6b4edf97b142e2477f3fec4a8bf9ff0c6adacdf7beadd17cc0d6'
SERVER='c9ab0d36ff35d9cf2548bdc73a94d911cc2065a921fa4a4afac86ad2e593a988'

def main():
    archive=Path(str(DEST)+'.zip')
    if DEST.exists() or archive.exists():raise ValueError('Release exists; never overwrite')
    for entry in load(SOURCE/'package-manifest.json')['files']:
        data=(SOURCE/entry['path']).read_bytes()
        if len(data)!=entry['bytes'] or sha(data)!=entry['sha256']:raise ValueError('Source changed: '+entry['path'])
    client=apply((ROOT/'backups/Need For Speed The Run.exe.lan-before-road-reset').read_bytes(),load(SOURCE/'patches/client.json'))
    server=apply((ROOT/'backups/NFSTR_Server.exe.headless-original').read_bytes(),load(SOURCE/'patches/server.json'))
    if (sha(client),sha(server))!=(CLIENT,SERVER):raise ValueError('Wrong native source')
    shutil.copytree(SOURCE,DEST)
    old_clients=('C9D48E500EF82EFC642EDF2DB848A9072E56FBC114E283173D6E7E58BAC634A6','42746E48E5E20FC3EE96C54F30EB0B4D6070D48A966EB9483386AA18DB4C309E')
    old_server='B912B57BF013DC6AC37C2BC0DAE8367496776ED5429F7AFCE6B319015AE8512C'
    for template in (ROOT/'package_tools').iterdir():
        if not template.is_file():continue
        text=template.read_text(encoding='utf-8-sig')
        for old in old_clients:text=text.replace(old,CLIENT.upper())
        text=text.replace(old_server,SERVER.upper())
        text=text.replace("Version='0.2-TEST'","Version='"+VERSION+"'")
        text=text.replace('v0.3-Testpaket','v'+VERSION+'-Testpaket')
        (DEST/template.name).write_text(text,encoding='ascii' if template.suffix.lower()=='.cmd' else 'utf-8-sig')
    status=load(DEST/'GAMEPLAY-STATUS.json')
    status.update(version=VERSION,combined_package_gameplay_verified=False,
        battle_live_evidence='2.6: repeated HOST/GUEST checkpoint gives no extra point or timer restart; user completed race from start to finish.',
        bilingual_launcher_garage='32 targeted checks including existing regressions; newest UI not live-tested with two PCs.',
        qte_synchronization_fixed=False,ant_delta_experiment_included=False,
        multiplayer_target='2 tested; 3/4 modeled offline, full four-player gameplay unverified')
    write(DEST/'GAMEPLAY-STATUS.json',status)
    (DEST/'CHANGELOG.md').write_text(
        '# v0.7.3 TEST / TESTVERSION\n\n'
        '## English\n\n'
        '- Eliminator: ignore duplicate/late checkpoint phase starts; a second teammate crossing cannot defeat the next rival or restart its timer.\n'
        '- Filter native bots out of the teammate comparison. Existing NPC racers, team results and shared checkpoint time are retained.\n'
        '- English/German launcher and garage, personal language choice, neutral Launch-Coop.cmd / Install.cmd aliases, bilingual Radmin instructions.\n'
        '- Garage still opens with each client; vehicle/relay logic retained. Host/Join/Solo and saved host IP retained.\n'
        '- Live: one complete2.6 run and duplicate-checkpoint test passed. Three/four-human phase cases only emulated; only two players tested live.\n'
        '- QTE/cutscene synchronization, initial cutscene vehicle collisions,1.51 scripted ending/bridge, Chicago transition crash, gas stations and launcher difficulty remain open. Avoid gas stations; use the garage.\n'
        '- Internal negative-ANT-time guard is NOT enabled in this release. No unsafe gas/timeout experiments. Installer and some helper messages remain partly German; see README-EN. PowerShell7 is still a prerequisite.\n\n'
        '## Deutsch\n\n'
        '- Eliminator: doppelte/verspaetete Checkpoint-Starts werden verworfen. Mitspieler besiegen am selben Checkpoint keinen weiteren Gegner und starten den Timer nicht neu.\n'
        '- Bots aus Teamvergleich entfernt; KI-Gegner, Teamwertung und gemeinsame Checkpoint-Zeit bleiben erhalten.\n'
        '- Launcher/Garage Deutsch und Englisch, persoenliche Sprachwahl, neutrale Starter und zweisprachige Radmin-Anleitung.\n'
        '-2.6 einmal komplett und doppelter Checkpoint live bestanden;3/4 nur offline modelliert. Neue Oberflaeche noch kein Zwei-PC-Nachweis.\n'
        '- QTE/Kameras, Cutscene-Kollisionen,1.51, Chicago-Absturz, Tankstellen und Launcher-Schwierigkeit bleiben offen. Tankstellen meiden, Garage verwenden. ANT-Zeit-Experiment nicht enthalten.\n',encoding='utf-8')
    for name in ('README.md','LIESMICH.md'):
        p=DEST/name;s=p.read_text(encoding='utf-8-sig')
        p.write_text('# v'+VERSION+'\n\n'+s+'\n\n[Changes / Aenderungen](CHANGELOG.md)\n',encoding='utf-8-sig')
    copy_local_sources(DEST/'src',('patch_claude_battle_botfilter.py','patch_battle_phase_guard.py',
        'patch_server_battle_phase_guard.py','test_claude_battle_botfilter.py','test_battle_phase_guard.py',
        'test_server_battle_phase_guard.py','build_release_073.py'))
    for name in ('Start-Coop.ps1','Start-Solo.ps1'):
        p=DEST/name;s=p.read_text(encoding='utf-8-sig')
        changed=s.replace("Version='0.7.2-TEST'","Version='"+VERSION+"'")
        if changed!=s:p.write_text(changed,encoding='utf-8-sig')
    historical=DEST/'BATTLE-PHASE-TEST.md'
    if historical.is_file():historical.unlink()
    write(DEST/'validation.json',dict(successful=True,tests=55,failures=0,errors=0,
        command='python -m unittest test_launcher_bilingual test_launcher_garage_language test_car_preferences test_start_solo test_claude_battle_botfilter test_battle_phase_guard test_server_battle_phase_guard -q',
        limits='Targeted source checks. Native double-checkpoint and full2.6 run user-confirmed; newly combined bilingual package not live-tested.'))
    files=[]
    for p in sorted(DEST.rglob('*')):
        if not p.is_file() or p.name=='package-manifest.json':continue
        if p.suffix.lower() in ('.exe','.dll','.ebx','.sb','.toc','.dmp'):raise ValueError('Game binary found')
        data=p.read_bytes();files.append(dict(path=p.relative_to(DEST).as_posix(),sha256=sha(data),bytes=len(data)))
    write(DEST/'package-manifest.json',dict(version=VERSION,files=files))
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for entry in files:z.write(DEST/entry['path'],DEST.name+'/'+entry['path'])
        z.write(DEST/'package-manifest.json',DEST.name+'/package-manifest.json')
    receipt=dict(version=VERSION,package=str(DEST),archive=str(archive),sha256=sha(archive.read_bytes()),bytes=archive.stat().st_size,files=len(files),client_sha256=CLIENT,server_sha256=SERVER,published=False,installed=False)
    write(ROOT/'outputs/v0.7.3-build-receipt.json',receipt);print(receipt)

if __name__=='__main__':main()
