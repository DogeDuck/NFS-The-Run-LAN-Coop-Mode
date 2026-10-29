. (Join-Path $PSScriptRoot 'Coop-Core.ps1')
Assert-CoopClosed
$last=Join-Path $script:CoopStateRoot 'last-install.txt'
if(!(Test-Path -LiteralPath $last)){throw 'Keine mit diesem Installer gesicherte Installation gefunden.'}
$manifestPath=[IO.Path]::GetFullPath((Get-Content -LiteralPath $last -Raw).Trim())
$backupRoot=[IO.Path]::GetFullPath((Join-Path $script:CoopStateRoot 'InstallBackups')).TrimEnd('\')+'\'
if(!$manifestPath.StartsWith($backupRoot,[StringComparison]::OrdinalIgnoreCase)){throw 'Sicherungsmanifest liegt ausserhalb des Sicherungsordners.'}
$manifest=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
$backup=[IO.Path]::GetFullPath($manifest.BackupDirectory).TrimEnd('\')
if((Split-Path -Parent $manifestPath) -ne $backup){throw 'Sicherungsordner stimmt nicht mit Manifest ueberein.'}
$game=Get-CoopGameDirectory $manifest.GameDirectory
$allowed=@('Need For Speed The Run.exe','NFSTR_Server.exe','dinput8.dll','Scripts\NFSTR_LANOnlineHelper.asi','Scripts\NFSTR_LANOnlineHelper.ini','d3d11.dll')
$restore=@()
foreach($entry in $manifest.Files){
    if($entry.RelativePath -notin $allowed){throw 'Unerwarteter Dateipfad in Sicherungsmanifest.'}
    $target=Join-Path $game $entry.RelativePath
    $exists=Test-Path -LiteralPath $target -PathType Leaf
    $hash=if($exists){Get-CoopFileHash $target}else{$null}
    $already=($exists -eq $entry.BeforeExists) -and (!$exists -or $hash -eq $entry.BeforeSha256)
    if($already){continue}
    if($exists -ne $entry.AfterExists -or ($exists -and $hash -ne $entry.AfterSha256)){throw ('Datei wurde seit Installation geaendert: '+$entry.RelativePath)}
    if($entry.BeforeExists -and (Get-CoopFileHash (Join-Path $backup $entry.RelativePath)) -ne $entry.BeforeSha256){throw 'Originalsicherung stimmt nicht.'}
    $restore+=$entry
}
foreach($entry in $restore){
    $target=Join-Path $game $entry.RelativePath
    if($entry.BeforeExists){
        Copy-Item -LiteralPath (Join-Path $backup $entry.RelativePath) -Destination $target -Force
        if((Get-CoopFileHash $target) -ne $entry.BeforeSha256){throw 'Wiederherstellung konnte nicht verifiziert werden.'}
    }elseif(Test-Path -LiteralPath $target){Remove-Item -LiteralPath $target}
}
$manifest.Status='restored'
$manifest|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $manifestPath -Encoding utf8
Write-Output 'Der Zustand vor dieser Paketinstallation wurde wiederhergestellt. Spielstaende wurden nicht veraendert.'
