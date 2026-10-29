param([string]$GameDirectory,[string]$LanPackageDirectory,[switch]$CheckOnly)
. (Join-Path $PSScriptRoot 'Coop-Core.ps1')
$game=Get-CoopGameDirectory $GameDirectory
if(!$CheckOnly){Assert-CoopClosed}
$deltas=@(foreach($name in @('client.json','server.json')){Get-Content -LiteralPath (Join-Path $PSScriptRoot "patches\$name") -Raw|ConvertFrom-Json})
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
if(!$changes.Count){Save-CoopSettings $game;Write-Output 'Koop-Dateien sind bereits bereit.';return}
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
$manifest=[ordered]@{Version='0.1';GameDirectory=$game;BackupDirectory=$backup;Timestamp=(Get-Date).ToString('o');Status='backed-up';Files=$changes}
$manifestPath=Join-Path $backup 'install-manifest.json'
$manifest|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $manifestPath -Encoding utf8
foreach($entry in $changes){
    $target=Join-Path $game $entry.RelativePath
    if($entry.BeforeExists -and (Get-CoopFileHash $target) -ne $entry.BeforeSha256){throw 'Installation wurde zwischenzeitlich geaendert.'}
    if($entry.AfterExists){
        New-Item -Path (Split-Path -Parent $target) -ItemType Directory -Force|Out-Null
        [IO.File]::WriteAllBytes($target,$staged[$entry.RelativePath])
        if((Get-CoopFileHash $target) -ne $entry.AfterSha256){throw 'Installierte Datei stimmt nicht mit dem Patch ueberein.'}
    }else{Remove-Item -LiteralPath $target}
}
$manifest.Status='installed'
$manifest|ConvertTo-Json -Depth 6|Set-Content -LiteralPath $manifestPath -Encoding utf8
Save-CoopSettings $game
$manifestPath|Set-Content -LiteralPath (Join-Path $script:CoopStateRoot 'last-install.txt') -Encoding utf8
Write-Output 'Koop-Patch installiert. Zum Hosten Start-Host.cmd, zum Beitreten Start-Guest.cmd verwenden.'
Write-Output "Originaldateien: $backup"
