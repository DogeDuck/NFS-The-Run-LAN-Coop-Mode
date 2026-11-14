param([string]$GameDirectory,[string]$LanPackageDirectory,[switch]$CheckOnly)
. (Join-Path $PSScriptRoot 'Coop-Core.ps1')
$game=Get-CoopGameDirectory $GameDirectory
if(!$CheckOnly){Assert-CoopClosed}
$deltas=@(foreach($name in @('client.json','server.json')){Get-Content -LiteralPath (Join-Path $PSScriptRoot "patches\$name") -Raw|ConvertFrom-Json})
# Accept upgrades from the previous release and the verified local test baseline.
$deltas=@(foreach($entry in $deltas){
    $selected=$entry
    $current=Join-Path $game $entry.FileName
    if(Test-Path -LiteralPath $current){
        $hash=Get-CoopFileHash $current
        $stem=if($entry.FileName -eq 'NFSTR_Server.exe'){'server'}else{'client'}
        foreach($suffix in @('-upgrade','-research-upgrade','-v0_3-upgrade','-v0_4-upgrade','-v0_5-upgrade','-v0_6-upgrade','-v0_7_1-upgrade','-v0_7_2-upgrade','-v0_7_3-upgrade','-v0_7_3-marcus-upgrade','-v0_7_7-upgrade','-r2-upgrade','-native-r3-upgrade')){
            $candidate=Join-Path $PSScriptRoot ("patches\"+$stem+$suffix+'.json')
            if(Test-Path -LiteralPath $candidate){
                $upgrade=Get-Content -LiteralPath $candidate -Raw|ConvertFrom-Json
                if($hash -eq $upgrade.OriginalSha256){$selected=$upgrade;break}
            }
        }
    }
    $selected
})
$support=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'patches\support-files.json') -Raw|ConvertFrom-Json
if(!$LanPackageDirectory -and !$CheckOnly){
    $missingBase=$false
    foreach($delta in $deltas){
        $path=Join-Path $game $delta.FileName
        if(!(Test-Path -LiteralPath $path) -or (Get-CoopFileHash $path) -notin @($delta.OriginalSha256,$delta.PatchedSha256)){$missingBase=$true}
    }
    foreach($file in $support){$path=Join-Path $game $file.RelativePath;if(!(Test-Path -LiteralPath $path) -or (Get-CoopFileHash $path) -ne $file.Sha256){$missingBase=$true}}
    if($missingBase){$LanPackageDirectory=Read-Host 'Ordner des entpackten eigenen LAN-Grundpakets v1 vom 29.05.2024'}
}
$addonRoot=Join-Path $PSScriptRoot 'addons'
$addonManifest=Get-Content -LiteralPath (Join-Path $addonRoot 'manifest.json') -Raw|ConvertFrom-Json
foreach($item in $addonManifest.files.PSObject.Properties){
 $file=Join-Path $addonRoot $item.Name
 if((Get-CoopFileHash $file) -ne $item.Value){throw ('Addon-Pruefsumme stimmt nicht: '+$item.Name)}
}
$music=Join-Path $addonRoot 'audio-slider\NFS-Audio-Patch.ps1'
& $music -GamePath $game -CheckOnly
$staged=@{}
function Read-BaseFile([string]$Relative,[string[]]$AllowedHashes){
    $candidates=@((Join-Path $game $Relative))
    if($LanPackageDirectory){
        $source=[IO.Path]::GetFullPath($LanPackageDirectory.Trim('"'))
        if($source.Split('\') -contains 'THERUNBACKUP'){throw 'THERUNBACKUP wird nicht verwendet.'}
        $candidates+=Join-Path $source $Relative
    }
    foreach($candidate in $candidates){
        if(Test-Path -LiteralPath $candidate -PathType Leaf){
            $bytes=[IO.File]::ReadAllBytes($candidate)
            if((Get-CoopHash $bytes) -in $AllowedHashes){return ,$bytes}
        }
    }
    throw "Passende LAN-Grunddatei fehlt: $Relative. Das eigene LAN-Grundpaket v1 vom 29.05.2024 entpacken und dessen Ordner mit -LanPackageDirectory angeben."
}
foreach($delta in $deltas){
    $bytes=Read-BaseFile $delta.FileName @($delta.OriginalSha256,$delta.PatchedSha256)
    $staged[$delta.FileName]=New-CoopPatchedBytes $bytes $delta
}
foreach($file in $support){$staged[$file.RelativePath]=Read-BaseFile $file.RelativePath @($file.Sha256)}
$staged['Scripts\NFSTR_LANOnlineHelper.ini']=[IO.File]::ReadAllBytes((Join-Path $PSScriptRoot 'config\NFSTR_LANOnlineHelper.ini'))
foreach($name in @('NFSTR_DefinitiveEdition.asi','NFSTR_DefinitiveEdition.ini')){
 $staged[('Scripts\'+$name)]=[IO.File]::ReadAllBytes((Join-Path $addonRoot $name))
}
# Personal INIs are preserved byte-exactly; defaults are used only when missing.
foreach($relative in @('Scripts\NFSTR_LANOnlineHelper.ini','Scripts\NFSTR_DefinitiveEdition.ini')){
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
$specialK=Join-Path $game 'd3d11.dll'
$removeSpecialK=$false
if(Test-Path -LiteralPath $specialK){
    if((Get-CoopFileHash $specialK) -ne '97db9964b9a9bd7af12c885ee5d697b876f33c7753686feaa35b1f8893c8d398'){throw 'Unbekannte d3d11.dll: wird nicht automatisch veraendert.'}
    $removeSpecialK=$true
}
$changes=@(foreach($relative in $staged.Keys|Sort-Object){
    $target=Join-Path $game $relative
    $after=Get-CoopHash $staged[$relative]
    if(!(Test-Path -LiteralPath $target) -or (Get-CoopFileHash $target) -ne $after){[ordered]@{RelativePath=$relative;AfterSha256=$after;AfterExists=$true}}
})
if($removeSpecialK){$changes += [ordered]@{RelativePath='d3d11.dll';AfterSha256=$null;AfterExists=$false}}
if($CheckOnly){[ordered]@{Status='verified';GameDirectory=$game;Changes=$changes;ContainsGameExecutables=$false}|ConvertTo-Json -Depth 5;return}
. (Join-Path $PSScriptRoot 'Coop-PowerShellRuntime.ps1')
[void](Resolve-CoopPowerShell7)
# Startpunkt neben der Spiel-EXE (Koop + Solo) zeigt immer auf dieses Paket, auch bei reinen Skript-Updates.
# Restore-Installation entfernt ihn wieder; eine fremde gleichnamige Datei bleibt unberuehrt.
function Set-CoopStarterStub{
    $stub=Join-Path $game 'The Run starten (Koop + Solo).cmd'
    $body="@echo off`r`nrem TheRunStoryCoop-Starter`r`ncall `""+(Join-Path $PSScriptRoot 'Koop-Starten.cmd')+"`"`r`n"
    if(!(Test-Path -LiteralPath $stub) -or ((Get-Content -LiteralPath $stub -Raw) -match 'TheRunStoryCoop-Starter')){[IO.File]::WriteAllText($stub,$body,[Text.Encoding]::ASCII);Write-Output ('Starter neben der Spiel-EXE: '+$stub)}
}
function Invoke-CoopInstallMusic {
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
function Invoke-CoopRetiredCleanupAfterSuccess {
    if([IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($PSScriptRoot)) -ine [IO.Path]::GetFullPath($game).TrimEnd('\')){return}
    $stub=Join-Path $game 'The Run starten (Koop + Solo).cmd'
    if(!(Test-Path -LiteralPath $stub)){return}
    $body=[IO.File]::ReadAllText($stub)
    if(!$body.Contains('TheRunStoryCoop-Starter') -or !$body.Contains((Join-Path $PSScriptRoot 'Koop-Starten.cmd'))){return}
    try{
        . (Join-Path $PSScriptRoot 'Coop-VersionCleanup.ps1')
        $report=@(Invoke-CoopRetiredPackageCleanup -GameDirectory $game -ActivePackage $PSScriptRoot -Commit -NewInstallationVerified)
        $report|ConvertTo-Json -Depth 6|Set-Content -LiteralPath (Join-Path $script:CoopStateRoot 'cleanup-last.json') -Encoding utf8
    }catch{Write-Warning ('Old versions preserved / Alte Versionen erhalten: '+$_.Exception.Message)}
}
if(!$changes.Count){Invoke-CoopInstallMusic;Save-CoopSettings $game;Set-CoopStarterStub;Invoke-CoopRetiredCleanupAfterSuccess;Write-Output 'Koop-Dateien sind bereits bereit.';return}
$stamp=(Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8)
$backup=Join-Path $script:CoopStateRoot "InstallBackups\$stamp"
New-Item -Path $backup -ItemType Directory -Force|Out-Null
foreach($entry in $changes){
    $target=Join-Path $game $entry.RelativePath
    $entry.BeforeExists=Test-Path -LiteralPath $target -PathType Leaf
    $entry.BeforeSha256=$null
    if($entry.BeforeExists){
        $entry.BeforeSha256=Get-CoopFileHash $target
        $copy=Join-Path $backup $entry.RelativePath
        New-Item -Path (Split-Path -Parent $copy) -ItemType Directory -Force|Out-Null
        Copy-Item -LiteralPath $target -Destination $copy
        if((Get-CoopFileHash $copy) -ne $entry.BeforeSha256){throw 'Originalsicherung konnte nicht verifiziert werden.'}
    }
}
$manifest=[ordered]@{Version='0.7.8-TEST';GameDirectory=$game;BackupDirectory=$backup;Timestamp=(Get-Date).ToString('o');Status='backed-up';Files=$changes}
$manifestPath=Join-Path $backup 'install-manifest.json'
$manifest|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $manifestPath -Encoding utf8
$applied=@()
try{
foreach($entry in $changes){
    $target=Join-Path $game $entry.RelativePath
    if($entry.BeforeExists -and (Get-CoopFileHash $target) -ne $entry.BeforeSha256){throw 'Installation wurde zwischenzeitlich geaendert.'}
    $applied+= $entry
    if($entry.AfterExists){
        New-Item -Path (Split-Path -Parent $target) -ItemType Directory -Force|Out-Null
        Write-CoopInstallFile $target $staged[$entry.RelativePath] $entry.AfterSha256
        if((Get-CoopFileHash $target) -ne $entry.AfterSha256){throw 'Installierte Datei stimmt nicht mit dem Patch ueberein.'}
    }else{Remove-Item -LiteralPath $target}
}
Invoke-CoopInstallMusic
}catch{
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
$manifest.Status='installed'
$manifest|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $manifestPath -Encoding utf8
Save-CoopSettings $game
$manifestPath|Set-Content -LiteralPath (Join-Path $script:CoopStateRoot 'last-install.txt') -Encoding utf8
Set-CoopStarterStub
Invoke-CoopRetiredCleanupAfterSuccess
Write-Output 'Koop-Patch installiert. Zum Hosten Start-Host.cmd, zum Beitreten Start-Guest.cmd verwenden.'
Write-Output "Originaldateien: $backup"
