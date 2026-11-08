"""Isolated candidate from frozen Claude v0.7.2, keeping unrelated UI/game changes out."""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from build_test_package import apply,reverse_apply,delta,copy_local_sources
from patch_claude_battle_botfilter import build as bot_filter
from patch_battle_phase_guard import build as client_guard
from patch_server_battle_phase_guard import build as server_guard

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'outputs/TheRun-Coop-v0.7.2-TEST-CANDIDATE'
DEST=ROOT/'outputs/TheRun-Coop-v0.7.2-BATTLE-PHASE-CANDIDATE'

def sha(data):return hashlib.sha256(data).hexdigest()
def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path,value):path.write_text(json.dumps(value,indent=2),encoding='utf-8')


def main():
    archive=Path(str(DEST)+'.zip')
    if DEST.exists() or archive.exists():raise ValueError('Candidate already exists; never overwrite')
    original_manifest=load(SOURCE/'package-manifest.json')
    for entry in original_manifest['files']:
        data=(SOURCE/entry['path']).read_bytes()
        if sha(data)!=entry['sha256'] or len(data)!=entry['bytes']:raise ValueError('Original Claude package changed: '+entry['path'])
    old={}
    for stem,backup in (('client','Need For Speed The Run.exe.lan-before-road-reset'),('server','NFSTR_Server.exe.headless-original')):
        old[stem]=apply((ROOT/'backups'/backup).read_bytes(),load(SOURCE/f'patches/{stem}.json'))
    filtered,_,bot_report=bot_filter(old['client'])
    client,_,client_report=client_guard(filtered)
    server,_,server_report=server_guard(old['server'])
    new={'client':client,'server':server}
    patches={}
    for stem in old:
        for path in (SOURCE/'patches').glob(stem+'*.json'):
            previous=load(path)
            before=reverse_apply(old[stem],previous)
            patch=delta(previous['FileName'],before,new[stem])
            if apply(before,patch)!=new[stem]:raise ValueError('Upgrade roundtrip failed')
            patches[path.name]=patch
        patch=delta('Need For Speed The Run.exe' if stem=='client' else 'NFSTR_Server.exe',old[stem],new[stem])
        if apply(old[stem],patch)!=new[stem]:raise ValueError('Claude roundtrip failed')
        patches[stem+'-v0_7_2-upgrade.json']=patch
    shutil.copytree(SOURCE,DEST)
    for name,patch in patches.items():write(DEST/'patches'/name,patch)
    installer=DEST/'Install-Coop.ps1';text=installer.read_text(encoding='utf-8-sig')
    marker="'-v0_7_1-upgrade')"
    if text.count(marker)!=1:raise ValueError('Original installer suffix contract changed')
    installer.write_text(text.replace(marker,"'-v0_7_1-upgrade','-v0_7_2-upgrade')"),encoding='utf-8')
    # Runtime helper/diagnostic hashes must refer to the candidate actually built.
    for path in DEST.rglob('*'):
        if not path.is_file() or path.suffix not in ('.ps1','.py'):continue
        text=path.read_text(encoding='utf-8-sig')
        replaced=text.replace(sha(old['client']).upper(),sha(client).upper()).replace(sha(old['server']).upper(),sha(server).upper())
        if replaced!=text:path.write_text(replaced,encoding='utf-8')
    status=load(DEST/'GAMEPLAY-STATUS.json')
    status.update(combined_package_gameplay_verified=False,
        isolated_bot_filter=bot_report,battle_client_phase_guard=client_report,
        battle_server_phase_guard=server_report,source_package=SOURCE.name,
        multiplayer_target='2-4; only2 local clients permitted,3/4 offline cases tested')
    write(DEST/'GAMEPLAY-STATUS.json',status)
    (DEST/'BATTLE-PHASE-TEST.md').write_text(
        'INTERNAL TEST CANDIDATE - NOT A PUBLISHED RELEASE\n'
        'Frozen original Claude v0.7.2 + bot filter + client/server duplicate Battle-start guards.\n'
        'Unrelated HUD experiments and in-progress launcher translations are excluded.\n'
        'Any teammate can beat the rival by countdown or the authored checkpoint. Each phase counts once.\n'
        'A second/late player must not defeat another rival or restart its timer by crossing the same checkpoint.\n'
        'Server guard runs before opponent re-activation; reset/enable permit a legitimate new attempt.\n'
        'No fake wins. No tank-station/timeout experiments. Initial AI control still needs Pause/Return or Select.\n'
        'New guards are offline-tested, not yet gameplay-verified. Native4-player spawn/result support remains incomplete.\n'
        'Back up current saves, never restore an old profile. Use pwsh. Test with2 local clients only.\n',encoding='utf-8')
    copy_local_sources(DEST/'src',('patch_claude_battle_botfilter.py','patch_battle_phase_guard.py',
        'patch_server_battle_phase_guard.py','test_claude_battle_botfilter.py','test_battle_phase_guard.py',
        'test_server_battle_phase_guard.py','record_battle_phase_flow.py'))
    files=[]
    for path in sorted(DEST.rglob('*')):
        if not path.is_file() or path.name=='package-manifest.json':continue
        relative=path.relative_to(DEST).as_posix()
        if path.suffix.lower() in ('.exe','.dll','.ebx','.sb','.toc','.dmp'):raise ValueError('Game binary must not be packaged')
        data=path.read_bytes();files.append(dict(path=relative,sha256=sha(data),bytes=len(data)))
    manifest=dict(version='0.7.2-BATTLE-PHASE-CANDIDATE',files=files,gameplay_verified=False,published=False,
                  client=dict(patched_sha256=sha(client),bot_filter=bot_report,phase_guard=client_report),
                  server=dict(patched_sha256=sha(server),phase_guard=server_report))
    write(DEST/'package-manifest.json',manifest)
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for path in DEST.rglob('*'):
            if path.is_file():z.write(path,DEST.name+'/'+path.relative_to(DEST).as_posix())
    receipt=dict(package=str(DEST),zip=str(archive),files=len(files),zip_sha256=sha(archive.read_bytes()),
                 client_sha256=sha(client),server_sha256=sha(server),installed=False,published=False)
    write(ROOT/'outputs/battle-phase-build-receipt.json',receipt)
    print(json.dumps(receipt))


if __name__=='__main__':main()
