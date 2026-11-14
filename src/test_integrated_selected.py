"""Actual enhanced installer on tiny temp-game fixtures, personal data and rollback."""
import hashlib,json,os,shutil,tempfile,unittest
from pathlib import Path
import test_launcher_bilingual as launcher
from build_integrated_selected_candidate import personalize_installer,preserve_core_settings,ROOT,INSTALLER
from build_test_package import delta

class IntegratedSelectedTests(unittest.TestCase):
    ps=launcher.LauncherBilingualTests.ps
    literal=staticmethod(launcher.LauncherBilingualTests.literal)
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='coop-integration-');self.addCleanup(self.tmp.cleanup)
        self.directory=Path(self.tmp.name);self.environment=dict(os.environ,LOCALAPPDATA=str(self.directory))
        self.pkg=self.directory/'package';self.game=self.directory/'game';self.state=self.directory/'TheRunStoryCoop'
        for p in (self.pkg/'patches',self.pkg/'addons/music25',self.pkg/'config',self.game/'Scripts',self.state):p.mkdir(parents=True,exist_ok=True)
        (self.pkg/'Install-Coop.ps1').write_text(personalize_installer((INSTALLER/'Install-Coop.ps1').read_text(encoding='utf-8-sig')),encoding='utf-8-sig')
        core=(ROOT/'outputs/TheRun-Coop-v0.7.7-RACESTART-CANDIDATE/Coop-Core.ps1').read_text(encoding='utf-8-sig')
        core=preserve_core_settings(core)
        core=core.replace("$script:CoopStateRoot=Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'TheRunStoryCoop'",'$script:CoopStateRoot='+self.literal(self.state))
        self.assertNotIn("GetFolderPath('LocalApplicationData')",core,'Test must not resolve real Windows personal state')
        (self.pkg/'Coop-Core.ps1').write_text(core,encoding='utf-8-sig')
        (self.pkg/'Coop-PowerShellRuntime.ps1').write_text('function Resolve-CoopPowerShell7 {return $PSHOME}')
        self.before={}
        for stem,name in (('client','Need For Speed The Run.exe'),('server','NFSTR_Server.exe')):
            original=(stem+'old').encode();patched=(stem+'new').encode();self.before[name]=original
            (self.game/name).write_bytes(original);(self.pkg/'patches'/f'{stem}.json').write_text(json.dumps(delta(name,original,patched)))
        (self.pkg/'patches/support-files.json').write_text('[]')
        self.ini={'Scripts/NFSTR_LANOnlineHelper.ini':b'ClientName=Mine\r\nCustom=Keep\r\n','Scripts/NFSTR_DefinitiveEdition.ini':b'[RENDER]\r\nFPSLimit=144\r\n'}
        for p,v in self.ini.items():(self.game/p).write_bytes(v)
        (self.pkg/'config/NFSTR_LANOnlineHelper.ini').write_text('ClientName=Default')
        (self.pkg/'addons/NFSTR_DefinitiveEdition.ini').write_text('FPSLimit=240')
        (self.pkg/'addons/NFSTR_DefinitiveEdition.asi').write_bytes(b'test-addon')
        (self.state/'launcher.json').write_text(json.dumps(dict(MusicMix=False,HudAlpha='Dim',UnknownSetting='keep')))
        (self.state/'settings.json').write_text(json.dumps(dict(GameDirectory='old',FutureSetting=42)))
        self.set_music()
    def set_music(self,fail=False):
        script="param($GamePath,$Mode,[switch]$CheckOnly);if($CheckOnly){return};"
        script+="throw 'simulated music failure'" if fail else "[IO.File]::WriteAllText((Join-Path $GamePath 'music-mode.txt'),$Mode)"
        (self.pkg/'addons/music25/NFS-Audio-Patch.ps1').write_text(script)
        files={str(p.relative_to(self.pkg/'addons')).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.pkg/'addons').rglob('*') if p.is_file() and p.name!='manifest.json'}
        (self.pkg/'addons/manifest.json').write_text(json.dumps({'files':files}))
    def install(self,check=False,success=True):
        return self.ps('& '+self.literal(self.pkg/'Install-Coop.ps1')+' -GameDirectory '+self.literal(self.game)+(' -CheckOnly' if check else ''),success=success)
    def test_install_keeps_exact_personal_inis_music_choice_and_unknown_settings(self):
        self.install()
        for p,v in self.ini.items():self.assertEqual((self.game/p).read_bytes(),v)
        self.assertEqual((self.game/'music-mode.txt').read_text(),'Restore')
        data=json.loads((self.state/'settings.json').read_text(encoding='utf-8-sig'));self.assertEqual(data['FutureSetting'],42)
        self.assertEqual(json.loads((self.state/'launcher.json').read_text())['UnknownSetting'],'keep')
        self.assertEqual((self.game/'Need For Speed The Run.exe').read_bytes(),b'clientnew')
    def test_late_failure_rolls_back_native_files_and_new_addon(self):
        self.set_music(fail=True);self.install(success=False)
        for name,before in self.before.items():self.assertEqual((self.game/name).read_bytes(),before)
        for p,v in self.ini.items():self.assertEqual((self.game/p).read_bytes(),v)
        self.assertFalse((self.game/'Scripts/NFSTR_DefinitiveEdition.asi').exists())
    def test_checkonly_makes_no_files_or_config_changes(self):
        before={p.relative_to(self.game).as_posix():p.read_bytes() for p in self.game.rglob('*') if p.is_file()}
        result=json.loads(self.install(check=True).stdout)
        self.assertEqual(result['Status'],'verified')
        self.assertFalse(any(x['RelativePath'].endswith('.ini') for x in result['Changes']))
        self.assertEqual(before,{p.relative_to(self.game).as_posix():p.read_bytes() for p in self.game.rglob('*') if p.is_file()})
        self.assertFalse((self.state/'InstallBackups').exists())
    def test_damaged_personal_settings_refuse_install_before_native_writes(self):
        damaged=b'{broken-settings';(self.state/'settings.json').write_bytes(damaged)
        self.install(success=False)
        self.assertEqual((self.state/'settings.json').read_bytes(),damaged)
        for name,before in self.before.items():self.assertEqual((self.game/name).read_bytes(),before)
        self.assertFalse((self.game/'Scripts/NFSTR_DefinitiveEdition.asi').exists())

if __name__=='__main__':unittest.main()
