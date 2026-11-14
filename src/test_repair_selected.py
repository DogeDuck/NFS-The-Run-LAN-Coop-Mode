"""Transactional native mod repair, isolated tiny fixtures, no installed game."""
import hashlib,json,os,shutil,tempfile,unittest
from pathlib import Path
from build_test_package import delta
import test_launcher_bilingual as launcher
ROOT=Path(__file__).resolve().parent

class RepairSelectedTests(unittest.TestCase):
    ps=launcher.LauncherBilingualTests.ps
    literal=staticmethod(launcher.LauncherBilingualTests.literal)
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='coop-repair-');self.addCleanup(self.tmp.cleanup)
        self.directory=Path(self.tmp.name);self.environment=dict(os.environ,LOCALAPPDATA=str(self.directory))
        self.package=self.directory/'package';self.game=self.directory/'game';self.backup=self.directory/'backups'/'one'
        for folder in (self.package/'patches',self.game/'Scripts',self.backup):folder.mkdir(parents=True,exist_ok=True)
        core=ROOT/'outputs/TheRun-Coop-v0.7.7-RACESTART-CANDIDATE/Coop-Core.ps1'
        for p in (core,launcher.TOOLS/'Coop-Repair.ps1',launcher.TOOLS/'Coop-UserData.ps1'):shutil.copy2(p,self.package/p.name)
        self.expected={};self.before={}
        for stem,name in (('client','Need For Speed The Run.exe'),('server','NFSTR_Server.exe')):
            base=(stem+'-base').encode();after=(stem+'-cooppatched').encode()
            (self.package/'patches'/f'{stem}.json').write_text(json.dumps(delta(name,base,after)))
            (self.backup/name).write_bytes(base);(self.game/name).write_bytes(b'corrupted-'+stem.encode())
            self.expected[name]=after;self.before[name]=(self.game/name).read_bytes()
        (self.package/'patches/support-files.json').write_text('[]')
        (self.game/'Scripts/NFSTR_DefinitiveEdition.ini').write_bytes(b'MyPersonalFPS=144\r\n')
        manifest=dict(version='1.0-TEST',client_sha256=hashlib.sha256(self.expected['Need For Speed The Run.exe']).hexdigest(),server_sha256=hashlib.sha256(self.expected['NFSTR_Server.exe']).hexdigest(),files=[])
        for p in self.package.rglob('*'):
            if p.is_file():manifest['files'].append(dict(path=p.relative_to(self.package).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
        (self.package/'package-manifest.json').write_text(json.dumps(manifest))
    def call(self,code,success=True):
        prefix="$ErrorActionPreference='Stop';. "+self.literal(self.package/'Coop-Repair.ps1')+';$p=Get-CoopRepairPlan '+self.literal(self.game)+' '+self.literal(self.package)+' '+self.literal(self.backup.parent)+';'
        return self.ps(prefix+code,success=success)
    def test_apply_reconstructs_exact_targets_and_keeps_personal_ini(self):
        before=(self.game/'Scripts/NFSTR_DefinitiveEdition.ini').read_bytes()
        self.call('Invoke-CoopRepairPlan $p '+self.literal(self.directory/'repair-backup')+'|ConvertTo-Json')
        for name,after in self.expected.items():
            self.assertEqual((self.game/name).read_bytes(),after)
            self.assertEqual((self.directory/'repair-backup'/name).read_bytes(),self.before[name])
        self.assertEqual((self.game/'Scripts/NFSTR_DefinitiveEdition.ini').read_bytes(),before)
    def test_second_failure_rolls_back_first_native_file(self):
        self.call("$script:n=0;Invoke-CoopRepairPlan $p "+self.literal(self.directory/'repair-backup')+" {param($row)$script:n++;if($script:n -eq 2){throw 'simulated disk failure'}}",success=False)
        for name,before in self.before.items():self.assertEqual((self.game/name).read_bytes(),before)
    def test_missing_verified_source_blocks_all_writes(self):
        (self.backup/'NFSTR_Server.exe').unlink()
        self.call('Invoke-CoopRepairPlan $p '+self.literal(self.directory/'repair-backup'),success=False)
        for name,before in self.before.items():self.assertEqual((self.game/name).read_bytes(),before)
    def test_package_tampering_is_rejected_before_any_repair(self):
        (self.package/'patches/client.json').write_text('{}')
        self.call('$p.Ready',success=False)
        for name,before in self.before.items():self.assertEqual((self.game/name).read_bytes(),before)
    def test_check_only_never_creates_backups_or_modifies_targets(self):
        result=json.loads(self.call('@{Ready=$p.Ready;Count=$p.Changes.Count;SaveRestore=$p.SaveRestore}|ConvertTo-Json').stdout)
        self.assertEqual(result,dict(Ready=True,Count=2,SaveRestore=False))
        for name,before in self.before.items():self.assertEqual((self.game/name).read_bytes(),before)
    def test_bundled_de_addon_repaired_without_changing_its_personal_ini(self):
        addon=self.package/'addons/NFSTR_DefinitiveEdition.asi';addon.parent.mkdir();addon.write_bytes(b'checked-addon')
        path=self.package/'package-manifest.json';manifest=json.loads(path.read_text())
        manifest['files'].append(dict(path=addon.relative_to(self.package).as_posix(),bytes=addon.stat().st_size,sha256=hashlib.sha256(addon.read_bytes()).hexdigest()))
        path.write_text(json.dumps(manifest))
        self.call('Invoke-CoopRepairPlan $p '+self.literal(self.directory/'repair-backup')+'|ConvertTo-Json')
        self.assertEqual((self.game/'Scripts/NFSTR_DefinitiveEdition.asi').read_bytes(),b'checked-addon')
        self.assertEqual((self.game/'Scripts/NFSTR_DefinitiveEdition.ini').read_bytes(),b'MyPersonalFPS=144\r\n')

if __name__=='__main__':unittest.main()
