"""Show an off-screen test form through the real launcher; never start a game."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from test_garage_window import TOOLS,PWSH

PROBE=r'''
param([int]$GamePid=0,[switch]$RelayOnly)
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public static class GarageLaunchProbe { [DllImport("kernel32.dll")] public static extern IntPtr GetConsoleWindow(); [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h); }'
$form=[Windows.Forms.Form]::new();$form.Text='Garage launch test'
$form.StartPosition='Manual';$form.Location=[Drawing.Point]::new(-5000,-5000);$form.ShowInTaskbar=$true
$timer=[Windows.Forms.Timer]::new();$timer.Interval=150
$timer.Add_Tick({
    $timer.Stop()
    [ordered]@{visible=[GarageLaunchProbe]::IsWindowVisible($form.Handle);console=([GarageLaunchProbe]::GetConsoleWindow() -ne [IntPtr]::Zero);gamePid=$GamePid;relay=[bool]$RelayOnly}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $PSScriptRoot 'result.json') -Encoding utf8
    $form.Close()
})
$timer.Start();[void]$form.ShowDialog();$timer.Dispose();$form.Dispose()
'''


@unittest.skipUnless(Path(PWSH).is_file(),'PowerShell7 missing')
class AutoStartTests(unittest.TestCase):
    def run_probe(self,folder,legacy=False):
        folder.mkdir(parents=True)
        (folder/'Garage-Fenster.ps1').write_text(PROBE,encoding='utf-8')
        shutil.copyfile(TOOLS/'Start-GarageWindow.ps1',folder/'Start-GarageWindow.ps1')
        if legacy:
            launch="$p=Start-Process -FilePath '%s' -ArgumentList '-NoProfile -STA -File \"%s\" -GamePid 4242 -RelayOnly' -WindowStyle Hidden -PassThru"%(PWSH,folder/'Garage-Fenster.ps1')
        else:
            launch="$p=& '%s' -GamePid 4242 -RelayOnly -PassThru"%(folder/'Start-GarageWindow.ps1')
        script=launch+"; if(!$p.WaitForExit(12000)){$p.Kill();throw 'Test form did not exit'}; if($p.ExitCode -ne 0){throw 'Test form failed'}"
        r=subprocess.run([PWSH,'-NoProfile','-Command',script],capture_output=True,text=True,timeout=25)
        self.assertEqual(r.returncode,0,r.stderr)
        return json.loads((folder/'result.json').read_text(encoding='utf-8-sig'))

    def test_visible_console_free_on_every_launch_with_quoted_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            for attempt in range(2):
                result=self.run_probe(Path(tmp)/('Garage mit Leerzeichen '+str(attempt)))
                self.assertTrue(result['visible'],result)
                self.assertFalse(result['console'],result)
                self.assertEqual(result['gamePid'],4242)
                self.assertTrue(result['relay'])

    def test_old_hidden_start_reproduces_missing_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=self.run_probe(Path(tmp)/'Legacy hidden',legacy=True)
            self.assertFalse(result['visible'],result)


if __name__=='__main__':unittest.main()
