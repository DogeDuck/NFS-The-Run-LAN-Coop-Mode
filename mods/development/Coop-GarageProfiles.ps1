#requires -Version 7.0
. (Join-Path $PSScriptRoot 'Coop-UserData.ps1')
function Get-CoopGarageProfilesPath {
 param([string]$StateDirectory=(Join-Path $env:LOCALAPPDATA 'TheRunStoryCoop'))
 return Join-Path $StateDirectory 'garage-profiles.json'
}
function Read-CoopGarageProfiles {
 param([string]$Path=(Get-CoopGarageProfilesPath))
 $data=Read-CoopJsonObject $Path 131072
 if(!$data.Count){$data=[ordered]@{Schema=1;Favorites=@();Presets=[ordered]@{}}}
 if($data.Schema -ne 1 -or $data.Presets -isnot [System.Collections.IDictionary] -or @($data.Favorites).Count -gt 512 -or $data.Presets.Count -gt 32){throw 'Invalid garage profiles; file preserved / Ungueltige Garagenprofile; Datei bleibt erhalten.'}
 foreach($id in @($data.Favorites)){if($id -isnot [string] -or $id -notmatch '^[A-Za-z0-9_-]{1,96}$'){throw 'Invalid garage favorite / Ungueltiger Garagenfavorit.'}}
 return $data
}
function Resolve-CoopGarageSelection {
 param([Parameter(Mandatory)]$Catalog,[Parameter(Mandatory)]$Selection)
 $id=[string]$Selection.CarId;$pack=[string]$Selection.Pack;$n=0
 if(![int]::TryParse([string]$Selection.N,[ref]$n)){throw 'Unknown car selection / Unbekannte Autoauswahl.'}
 $cars=@($Catalog.Cars|Where-Object Id -CEQ $id)
 if($cars.Count -ne 1){throw 'Unknown car selection / Unbekannte Autoauswahl.'}
 $packs=@($cars[0].Packs|Where-Object Pack -CEQ $pack)
 if($packs.Count -ne 1){throw 'Unknown style pack / Unbekanntes Style-Pack.'}
 $variants=@($packs[0].Variants|Where-Object N -EQ $n)
 if($variants.Count -ne 1){throw 'Unknown paint variant / Unbekannte Lackvariante.'}
 return [pscustomobject]@{Car=$cars[0];Pack=$packs[0];Variant=$variants[0]}
}
function Set-CoopGarageFavorite {
 param([Parameter(Mandatory)][string]$CarId,[bool]$Enabled,[string]$Path=(Get-CoopGarageProfilesPath))
 if($CarId -notmatch '^[A-Za-z0-9_-]{1,96}$'){throw 'Invalid car identifier / Ungueltige Fahrzeugkennung.'}
 $data=Read-CoopGarageProfiles $Path
 $ids=@($data.Favorites|Where-Object {$_ -cne $CarId})
 if($Enabled){$ids+= $CarId}
 if($ids.Count -gt 512){throw 'Too many favorites / Zu viele Favoriten.'}
 $data.Favorites=$ids;Write-CoopJsonObjectAtomic $Path $data
}
function Save-CoopGaragePreset {
 param([Parameter(Mandatory)][string]$Name,[Parameter(Mandatory)]$Selection,[Parameter(Mandatory)]$Catalog,[string]$Path=(Get-CoopGarageProfilesPath))
 $Name=$Name.Trim()
 if(!$Name -or $Name.Length -gt 48 -or $Name -match '[\x00-\x1F]'){throw 'Preset name: 1-48 characters / Setname: 1-48 Zeichen.'}
 [void](Resolve-CoopGarageSelection $Catalog $Selection)
 $data=Read-CoopGarageProfiles $Path
 if(!$data.Presets.Contains($Name) -and $data.Presets.Count -ge 32){throw 'Maximum 32 presets / Hoechstens 32 Fahrzeugsets.'}
 $data.Presets[$Name]=[ordered]@{CarId=[string]$Selection.CarId;Pack=[string]$Selection.Pack;N=[int]$Selection.N}
 Write-CoopJsonObjectAtomic $Path $data
}
function Remove-CoopGaragePreset {
 param([Parameter(Mandatory)][string]$Name,[string]$Path=(Get-CoopGarageProfilesPath))
 $data=Read-CoopGarageProfiles $Path;[void]$data.Presets.Remove($Name);Write-CoopJsonObjectAtomic $Path $data
}
