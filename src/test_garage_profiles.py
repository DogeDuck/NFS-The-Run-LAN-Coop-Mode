"""Personal garage favorites/presets: real PS7, isolated files, no game access."""
import json,os,tempfile,unittest
from pathlib import Path
import test_launcher_bilingual as launcher
TOOLS,PWSH=launcher.TOOLS,launcher.PWSH

@unittest.skipUnless(PWSH.is_file(),'PS7 missing')
class GarageProfilesTests(unittest.TestCase):
    ps=launcher.LauncherBilingualTests.ps
    literal=staticmethod(launcher.LauncherBilingualTests.literal)
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='coop-profiles-');self.addCleanup(self.tmp.cleanup)
        self.directory=Path(self.tmp.name);self.environment=dict(os.environ,LOCALAPPDATA=str(self.directory))
        self.path=self.directory/'garage-profiles.json'
    def call(self,body,success=True):
        return self.ps("$ErrorActionPreference='Stop';. "+self.literal(TOOLS/'Coop-GarageProfiles.ps1')+';$path='+self.literal(self.path)+';'+body,success=success)
    def test_favorites_and_presets_roundtrip_preserves_unknown_metadata(self):
        self.path.write_text(json.dumps(dict(Schema=1,Favorites=[],Presets={},Future={'keep':42})))
        result=self.call("$cars=Get-Content -Raw "+self.literal(TOOLS/'Garage-Cars.json')+"|ConvertFrom-Json;$catalog=@{Cars=@($cars)};$car=$catalog.Cars[0];$p=$car.Packs[0];$v=$p.Variants[0];Set-CoopGarageFavorite $car.Id $true $path;Set-CoopGarageFavorite $car.Id $true $path;Save-CoopGaragePreset 'My road car' @{CarId=$car.Id;Pack=$p.Pack;N=$v.N} $catalog $path;$r=Read-CoopGarageProfiles $path;@{Favorites=@($r.Favorites);Preset=$r.Presets['My road car'];Future=$r.Future}|ConvertTo-Json -Depth 5")
        data=json.loads(result.stdout);self.assertEqual(len(data['Favorites']),1);self.assertEqual(data['Future'],{'keep':42})
        self.assertTrue(data['Preset']['CarId'])
        self.call("Remove-CoopGaragePreset 'My road car' $path;Set-CoopGarageFavorite '"+data['Preset']['CarId']+"' $false $path")
        saved=json.loads(self.path.read_text());self.assertEqual(saved['Favorites'],[]);self.assertEqual(saved['Presets'],{})
    def test_corrupt_data_is_never_overwritten(self):
        self.path.write_bytes(b'{broken')
        self.call("Set-CoopGarageFavorite 'r35' $true $path",success=False)
        self.assertEqual(self.path.read_bytes(),b'{broken')
    def test_unknown_car_variant_and_bad_names_do_not_create_files(self):
        base="$cars=Get-Content -Raw "+self.literal(TOOLS/'Garage-Cars.json')+"|ConvertFrom-Json;$catalog=@{Cars=@($cars)};"
        self.call(base+"Save-CoopGaragePreset 'Test' @{CarId='missing';Pack='stock';N=1} $catalog $path",success=False)
        self.assertFalse(self.path.exists())
        self.call("Set-CoopGarageFavorite '../escape' $true $path",success=False)
        self.assertFalse(self.path.exists())
    def test_merge_preserves_all_unrelated_preferences(self):
        self.path.write_text(json.dumps({'MusicMix':False,'HudAlpha':'Dim','Plugin':{'value':1}}))
        self.call("Merge-CoopJsonObject $path @{DiagnosticsEnabled=$true}")
        self.assertEqual(json.loads(self.path.read_text()),{'MusicMix':False,'HudAlpha':'Dim','Plugin':{'value':1},'DiagnosticsEnabled':True})
    def test_presets_resolve_every_catalog_pack_without_memory_access(self):
        result=self.call("$cars=Get-Content -Raw "+self.literal(TOOLS/'Garage-Cars.json')+"|ConvertFrom-Json;$catalog=@{Cars=@($cars)};$n=0;foreach($c in $catalog.Cars){foreach($p in $c.Packs){foreach($v in $p.Variants){$r=Resolve-CoopGarageSelection $catalog @{CarId=$c.Id;Pack=$p.Pack;N=$v.N};if($r.Variant.VehicleKey -ne $v.VehicleKey){throw 'Wrong preset'};$n++}}};$n")
        self.assertGreater(int(result.stdout),100)

if __name__=='__main__':unittest.main()
