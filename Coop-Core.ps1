$ErrorActionPreference='Stop'
$script:CoopStateRoot=Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'TheRunStoryCoop'
function Get-CoopHash([byte[]]$Bytes){
    $sha=[Security.Cryptography.SHA256]::Create()
    try{return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
}
function Get-CoopFileHash([string]$Path){return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()}
function Get-CoopGameDirectory([string]$Requested){
    $settings=Join-Path $script:CoopStateRoot 'settings.json'
    if(!$Requested -and (Test-Path -LiteralPath $settings)){$Requested=(Get-Content -LiteralPath $settings -Raw|ConvertFrom-Json).GameDirectory}
    if(!$Requested){$Requested=Read-Host 'Vollstaendiger Spielordner (enthaelt die Spiel-EXE)'}
    $resolved=[IO.Path]::GetFullPath($Requested.Trim('"')).TrimEnd('\')
    if($resolved.Split('\') -contains 'THERUNBACKUP'){throw 'THERUNBACKUP wird nicht verwendet.'}
    if(!(Test-Path -LiteralPath (Join-Path $resolved 'Need For Speed The Run.exe') -PathType Leaf)){throw 'Im angegebenen Ordner fehlt die Spiel-EXE.'}
    return $resolved
}
function Save-CoopSettings([string]$Directory){
    New-Item -Path $script:CoopStateRoot -ItemType Directory -Force|Out-Null
    [ordered]@{GameDirectory=$Directory}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $script:CoopStateRoot 'settings.json') -Encoding utf8
}
function Assert-CoopClosed {
    if(@(Get-Process -Name 'Need For Speed The Run','NFSTR_Server' -ErrorAction SilentlyContinue).Count){throw 'Bitte Spiel und Testserver zuerst schliessen.'}
}
function New-CoopPatchedBytes([byte[]]$Bytes,$Delta){
    $hash=Get-CoopHash $Bytes
    if($hash -eq $Delta.PatchedSha256){return ,$Bytes}
    if($hash -ne $Delta.OriginalSha256 -or $Bytes.Length -ne $Delta.OriginalLength){throw ('Nicht unterstuetzte LAN-Dateiversion: '+$Delta.FileName)}
    $result=New-Object byte[] ([int]$Delta.PatchedLength)
    [Array]::Copy($Bytes,$result,$Bytes.Length)
    foreach($run in $Delta.Changes){
        $before=[Convert]::FromBase64String($run.Before)
        $after=[Convert]::FromBase64String($run.After)
        if($before.Length -ne $after.Length){throw 'Ungueltiger Patchbereich.'}
        for($i=0;$i -lt $before.Length;$i++){if($Bytes[[int]$run.Offset+$i] -ne $before[$i]){throw 'Patchsignatur stimmt nicht.'}}
        [Array]::Copy($after,0,$result,[int]$run.Offset,$after.Length)
    }
    $append=[Convert]::FromBase64String($Delta.Append)
    if($Bytes.Length+$append.Length -ne $result.Length){throw 'Ungueltige Patchlaenge.'}
    [Array]::Copy($append,0,$result,$Bytes.Length,$append.Length)
    if((Get-CoopHash $result) -ne $Delta.PatchedSha256){throw 'Pruefsumme der gepatchten Datei stimmt nicht.'}
    return ,$result
}
function Test-CoopReady([string]$Directory){
    $support=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'patches\support-files.json') -Raw|ConvertFrom-Json
    foreach($deltaName in @('client.json','server.json')){
        $delta=Get-Content -LiteralPath (Join-Path $PSScriptRoot "patches\$deltaName") -Raw|ConvertFrom-Json
        $path=Join-Path $Directory $delta.FileName
        if(!(Test-Path -LiteralPath $path) -or (Get-CoopFileHash $path) -ne $delta.PatchedSha256){throw 'Koop-Dateien fehlen oder wurden geaendert. Bitte Install-Coop.cmd ausfuehren.'}
    }
    foreach($entry in $support){
        $path=Join-Path $Directory $entry.RelativePath
        if(!(Test-Path -LiteralPath $path) -or (Get-CoopFileHash $path) -ne $entry.Sha256){throw ('LAN-Grunddatei fehlt/abweichend: '+$entry.RelativePath)}
    }
    if(Test-Path -LiteralPath (Join-Path $Directory 'd3d11.dll')){throw 'd3d11.dll ist noch aktiv. Bitte die Installation pruefen.'}
}
function Get-CoopProcessRecord($Process,[string]$Path){return [ordered]@{Id=$Process.Id;Path=$Path;StartTicks=$Process.StartTime.ToUniversalTime().Ticks}}
function Stop-CoopOwnedProcess($Record,[switch]$Graceful){
    if(!$Record){return}
    $process=Get-Process -Id ([int]$Record.Id) -ErrorAction SilentlyContinue
    if(!$process){return}
    if($process.Path -ne $Record.Path -or $process.StartTime.ToUniversalTime().Ticks -ne [long]$Record.StartTicks){throw 'Prozess-ID gehoert nicht mehr zu dieser Koop-Sitzung.'}
    if($Graceful -and $process.MainWindowHandle -ne 0){$process.CloseMainWindow()|Out-Null;if($process.WaitForExit(4000)){return}}
    Stop-Process -Id $process.Id
    $process.WaitForExit(10000)|Out-Null
}
