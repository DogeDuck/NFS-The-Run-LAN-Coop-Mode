"""Offline tests for the Koop-Garage window (package_tools/Garage-*.ps1, Garage-Cars.json).

No game process is touched. Memory mechanics are exercised on a private 32-bit cmd.exe
started and killed by the test (writes only into that throwaway process).
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT / 'package_tools'
PWSH = shutil.which('pwsh') or r'C:\Program Files\PowerShell\7\pwsh.exe'
CMD32 = Path(os.environ.get('WINDIR', r'C:\Windows')) / 'SysWOW64' / 'cmd.exe'


def pwsh(script, env=None):
    return subprocess.run([PWSH, '-NoProfile', '-STA', '-Command', script], capture_output=True, text=True,
                          timeout=120, env=env)


class CatalogueTests(unittest.TestCase):
    def test_catalogue_matches_start_cars(self):
        cars = json.loads((TOOLS / 'Garage-Cars.json').read_text(encoding='utf-8'))
        start = {c['Id']: c for c in json.loads((TOOLS / 'Start-Cars.json').read_text(encoding='utf-8-sig')) if c['Id'] != 'story'}
        regular = [c for c in cars if c.get('Category') != 'fun']
        self.assertEqual({c['Id'] for c in regular}, set(start))
        fun = [c for c in cars if c.get('Category') == 'fun']
        self.assertTrue(all(c['Source'] and len(c['Packs']) == 1 for c in fun))
        keys = [v['VehicleKey'] for c in cars for p in c['Packs'] for v in p['Variants']]
        self.assertEqual(len(keys), len(set(keys)))
        for c in regular:
            first = c['Packs'][0]
            self.assertEqual(first['Pack'], 'stock')
            self.assertEqual(first['Variants'][0]['VehicleKey'], start[c['Id']]['VehicleKey'])
            for p in c['Packs']:
                for v in p['Variants']:
                    self.assertEqual(int.from_bytes(bytes.fromhex(v['HelperHash']), 'little'), v['VehicleKey'])


@unittest.skipUnless(Path(PWSH).is_file(), 'PowerShell 7 missing')
class WindowTests(unittest.TestCase):
    def test_selftest_builds_window_without_game(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, LOCALAPPDATA=tmp)
            for options in ([], ['-RelayOnly']):
                with self.subTest(options=options):
                    r = subprocess.run([PWSH, '-NoProfile', '-STA', '-File', str(TOOLS / 'Garage-Fenster.ps1'), '-SelfTest', *options],
                                       capture_output=True, text=True, timeout=120, env=env)
                    self.assertEqual(r.returncode, 0, r.stderr)
                    self.assertIn('SELFTEST ok cars=', r.stdout)
            self.assertFalse(any(Path(tmp).rglob('*.json')))        # nothing saved by a self test

    def test_helper_hash_matches_installed_helper_and_retention_test(self):
        # Regression 06.11.: a typo in the pinned SHA blocked every live connection.
        import hashlib
        import re
        core = (TOOLS / 'Garage-Core.ps1').read_text(encoding='utf-8-sig')
        expected = re.search(r"GarageHelperSha = '([0-9A-F]+)'", core).group(1)
        self.assertEqual(len(expected), 64)
        self.assertIn(expected.lower(), (ROOT / 'test_car_helper_retention.py').read_text(encoding='utf-8'))
        asi = Path(r'X:/EA Games/Need for Speed The Run/Need for Speed The Run/Scripts/NFSTR_LANOnlineHelper.asi')
        if asi.is_file():
            self.assertEqual(hashlib.sha256(asi.read_bytes()).hexdigest().upper(), expected)

    def test_server_mode_pins_match_server_image(self):
        import re
        core = (TOOLS / 'Garage-Core.ps1').read_text(encoding='utf-8-sig')
        getter = re.search(r"GarageServerGetter='([0-9a-f]+)'", core).group(1)
        server = ROOT / 'backups/NFSTR_Server.exe.headless-original'
        if server.is_file():
            from pe_image_readonly import PE32
            self.assertEqual(PE32(server.read_bytes()).read(0x13EAF90, len(getter) // 2).hex(), getter)
        self.assertIn('4AFB76C21D08439778DBA038AD787618F752AA3C639A18A07A5B1672C0263C9D', core)
        self.assertNotIn('9E0137A9F329F4FE', core)     # unsafe gas-timeout server builds are not allowed
        self.assertNotIn('67B27E9381F76F64', core)

    def test_relay_applies_guest_slot_and_refuses_own_slot(self):
        script = r"""
. '%s'
$l=Start-GarageRelayListener 25299
$core='%s'
$job=Start-ThreadJob -ScriptBlock { param($c) . $c
    $r=@(); try{Send-GarageRelayRequest '127.0.0.1' 1 4242 25299;$r+='guest:OK'}catch{$r+=('guest:'+$_.Exception.Message)}
    try{Send-GarageRelayRequest '127.0.0.1' 0 4242 25299;$r+='own:OK'}catch{$r+=('own:'+$_.Exception.Message)}
    $r } -ArgumentList $core
$applied=@()
$C=@{Ok='palette intact'}
for($i=0;$i -lt 80 -and $job.State -notin 'Completed','Failed','Stopped';$i++){
    $applied+=Receive-GarageRelayRequests $l 0 { param($slot,$key)
        if($C.Ok -ne 'palette intact'){throw 'GUI palette shadowed by relay scope'}
        "OK" }
    Start-Sleep -Milliseconds 100 }
$l.Stop()
Receive-Job $job -Wait
'applied=' + ($applied -join ',')
""" % (TOOLS / 'Garage-Core.ps1', TOOLS / 'Garage-Core.ps1')
        r = pwsh(script)
        self.assertIn('guest:OK', r.stdout, r.stderr)
        self.assertIn('own:Host lehnt ab: fremder Slot', r.stdout, r.stderr)
        self.assertIn('applied=1', r.stdout, r.stderr)

    def test_refuses_non_server_process(self):
        r = pwsh(". '%s'; try{Open-GarageServer $PID}catch{$_.Exception.Message}" % (TOOLS / 'Garage-Core.ps1'))
        self.assertIn('kein The-Run-Server', r.stdout)

    def test_refuses_non_game_process(self):
        r = pwsh(". '%s'; try{Open-GarageHelper $PID}catch{$_.Exception.Message}" % (TOOLS / 'Garage-Core.ps1'))
        self.assertIn('kein The-Run-Prozess', r.stdout)

    def test_rejects_unknown_key_and_old_value(self):
        script = r"""
. '%s'
$cat=Get-GarageCatalog
$h=[pscustomobject]@{Handle=[IntPtr]::Zero;Address=[IntPtr]::Zero}
try{Set-GarageForcedKey $h 12345 $cat}catch{'unknown:'+$_.Exception.Message}
""" % (TOOLS / 'Garage-Core.ps1')
        r = pwsh(script)
        self.assertIn('unknown:Kennung steht nicht im Garage-Katalog.', r.stdout)

    def test_previews_are_local_and_validated(self):
        with tempfile.TemporaryDirectory() as tmp:
            img = Path(tmp) / 'shot.png'
            img.write_bytes(b'\x89PNG\r\n\x1a\n' + bytes(16))
            env = dict(os.environ, LOCALAPPDATA=tmp)
            script = r""". '%s'
$p=Save-GaragePreview '%s' 'nis_gtr_r35_08_pp1v3'
(Get-GaragePreviewPath 'nis_gtr_r35_08_pp1v3' 'R35') -eq $p
try{Save-GaragePreview '%s' '..\evil'}catch{'bad:'+$_.Exception.Message}""" % (TOOLS / 'Garage-Core.ps1', img, img)
            r = pwsh(script, env)
            self.assertIn('True', r.stdout, r.stderr)
            self.assertIn('bad:Ungueltiger Bildname.', r.stdout)
            self.assertTrue((Path(tmp) / 'TheRunStoryCoop/previews/nis_gtr_r35_08_pp1v3.png').is_file())

    @unittest.skipUnless(CMD32.is_file(), '32-bit cmd missing')
    def test_32bit_module_lookup_and_checked_write_on_throwaway_process(self):
        proc = subprocess.Popen([str(CMD32), '/k'], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            script = r"""
. '%s'
$h=[CoopGarage.Native]::OpenProcess(0x0438,$false,%d)
$wow=$false;[void][CoopGarage.Native]::IsWow64Process($h,[ref]$wow);"wow=$wow"
$m=Find-GarageModule $h 'cmd.exe';"found=$([bool]$m)"
# Scratch address: the PE header's DOS stub string inside the throwaway process.
$cat=Get-GarageCatalog
$key=[uint32]($cat.Cars[0].Packs[0].Variants[0].VehicleKey)
$helper=[pscustomobject]@{Handle=$h;Address=[IntPtr]($m.Base.ToInt64()+0x4C)}
try{Set-GarageForcedKey $helper $key $cat}catch{'guard:'+$_.Exception.Message}
$zero=[BitConverter]::GetBytes([uint32]0);$n=[IntPtr]::Zero
$prot=0
[void][CoopGarage.Native]::CloseHandle($h)
""" % (TOOLS / 'Garage-Core.ps1', proc.pid)
            r = pwsh(script)
            self.assertIn('wow=True', r.stdout, r.stderr)
            self.assertIn('found=True', r.stdout, r.stderr)
            self.assertIn('guard:Unerwarteter Altwert', r.stdout, r.stderr)    # never overwrites unknown data
        finally:
            proc.kill()
            proc.wait(timeout=10)
            proc.stdin.close()


if __name__ == '__main__':
    unittest.main()
