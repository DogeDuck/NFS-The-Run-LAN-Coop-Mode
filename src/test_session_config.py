"""Personal helper INI values survive a host/guest start configuration."""
import json,os,tempfile,unittest
from pathlib import Path
import test_launcher_bilingual as launcher

class SessionConfigTests(unittest.TestCase):
    ps=launcher.LauncherBilingualTests.ps
    literal=staticmethod(launcher.LauncherBilingualTests.literal)
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='coop-session-config-');self.addCleanup(self.tmp.cleanup)
        self.directory=Path(self.tmp.name);self.environment=dict(os.environ,LOCALAPPDATA=str(self.directory))
    def config(self,text,custom=False):
        source=self.directory/'source.ini';source.write_text(text,encoding='utf-8',newline='')
        code=". "+self.literal(launcher.TOOLS/'Coop-SessionConfig.ps1')+';$t=[IO.File]::ReadAllText('+self.literal(source)+");New-CoopSessionConfig $t 'Alice' 'ABCDEF01' $"+str(custom).lower()+'|ConvertTo-Json -Compress'
        return json.loads(self.ps(code).stdout)
    def test_personal_values_comments_and_unicode_survive(self):
        text='; Meine Übersicht\r\n[OnlineSettings]\r\nEnableLANOnlineTweaks = 0\r\nClientName = Old\r\n[GameSettings]\r\nDisablePrimaryDrivingAssists = 1\r\nCustomFutureOption = behalten\r\n[ServerSettings]\r\nCustomTrafficDensity = 0.25\r\n'
        result=self.config(text)
        for value in ('; Meine Übersicht\r\n','DisablePrimaryDrivingAssists = 1\r\n','CustomFutureOption = behalten\r\n','CustomTrafficDensity = 0.25\r\n'):
            self.assertIn(value,result)
        self.assertIn('ClientName = Alice',result);self.assertIn('EnableLANOnlineTweaks = 1',result)
        self.assertIn('ForceInitFlow = TheRun',result)
    def test_minimal_ini_gets_required_keys_and_custom_car_menu(self):
        result=self.config('[Personal]\nKeep = yes\n',custom=True)
        self.assertIn('[Personal]\nKeep = yes\n',result)
        self.assertIn('[OnlineSettings]',result);self.assertIn('ForceGarageCarHash = ABCDEF01',result)
        self.assertIn('ForceInitFlow = MainMenu',result)
        self.assertEqual(result.count('[GameSettings]'),1)
    def test_duplicate_required_key_is_refused_before_writing(self):
        source=self.directory/'source.ini';source.write_text('[OnlineSettings]\nClientName=a\nClientName=b\n')
        before=source.read_bytes()
        code='. '+self.literal(launcher.TOOLS/'Coop-SessionConfig.ps1')+';New-CoopSessionConfig ([IO.File]::ReadAllText('+self.literal(source)+")) 'Alice' '0'"
        self.ps(code,success=False);self.assertEqual(source.read_bytes(),before)

if __name__=='__main__':unittest.main()
