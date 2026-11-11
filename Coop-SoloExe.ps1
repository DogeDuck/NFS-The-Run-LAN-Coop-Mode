# Laeuft unter PowerShell 7 (Start-Solo/Start-Coop) UND Windows PowerShell 5.1 (Restore-Installation.cmd startet
# powershell.exe): daher kein #requires und nur .NET-Framework-kompatible Aufrufe.
# Solo ohne Koop-Code. Die Koop-Patches stecken in der Spiel-EXE und wirken sonst auch im Einzelspieler
# (z.B. Select-Strassenreset statt Checkpoint-Reset, Koop-Story-Hooks). patches\client.json beschreibt
# LAN-Grund-EXE -> Koop-EXE vollstaendig (Originalbytes je Bereich + angehaengte Bytes). Daraus wird fuer
# eine Solo-Sitzung die LAN-Grund-EXE exakt (SHA256) zurueckgebaut und danach die Koop-EXE wieder eingesetzt.
# Das Paket enthaelt dafuer keine Spiel-EXE. Eine Markerdatei neben der EXE erlaubt die Wiederherstellung,
# falls eine Solo-Sitzung abbricht (Start-Coop, Start-Solo und Restore-Installation pruefen sie).
$script:SoloExeName='Need For Speed The Run.exe'
$script:SoloProcessName='Need For Speed The Run'
$script:SoloMarkerName='Need For Speed The Run.exe.solo-session.json'

function Get-SoloSha256([byte[]]$Bytes){
    $sha=[Security.Cryptography.SHA256]::Create()
    try{return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
}
function Get-SoloFileSha256([string]$Path){
    # Windows PowerShell5.1 can inherit a PS7-only PSModulePath from a launcher.
    # Keep the safety check independent of auto-loaded utility modules.
    $stream=[IO.File]::OpenRead($Path)
    $sha=[Security.Cryptography.SHA256]::Create()
    try{return ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant()}
    finally{$sha.Dispose();$stream.Dispose()}
}
function Test-SoloGameRunning{return [bool]@(Get-Process -Name $script:SoloProcessName -ErrorAction SilentlyContinue).Count}

function Read-SoloDelta([string]$Path){
    if(!(Test-Path -LiteralPath $Path -PathType Leaf)){throw 'Koop-Patchbeschreibung fehlt: patches\client.json'}
    $d=Get-Content -LiteralPath $Path -Raw|ConvertFrom-Json
    if($d.FileName -ne $script:SoloExeName -or $d.OriginalSha256 -notmatch '^[0-9a-f]{64}$' -or $d.PatchedSha256 -notmatch '^[0-9a-f]{64}$' -or
       [int64]$d.OriginalLength -le 0 -or [int64]$d.PatchedLength -lt [int64]$d.OriginalLength -or $d.OriginalSha256 -eq $d.PatchedSha256){
        throw 'Ungueltige Koop-Patchbeschreibung.'
    }
    return $d
}

# Koop-EXE -> LAN-Grund-EXE: abschneiden auf die Originallaenge und Originalbytes je Bereich zurueckschreiben.
function ConvertTo-SoloBaseBytes([byte[]]$Coop,$Delta){
    if($Coop.Length -ne [int64]$Delta.PatchedLength -or (Get-SoloSha256 $Coop) -ne $Delta.PatchedSha256){throw 'Koop-EXE stimmt nicht mit dem Paket ueberein.'}
    $base=New-Object byte[] ([int]$Delta.OriginalLength)
    [Array]::Copy($Coop,$base,$base.Length)
    foreach($run in $Delta.Changes){
        $before=[Convert]::FromBase64String($run.Before)
        $offset=[int64]$run.Offset
        if($before.Length -ne ([Convert]::FromBase64String($run.After)).Length -or $offset -lt 0 -or $offset+$before.Length -gt $base.Length){throw 'Ungueltiger Patchbereich.'}
        [Array]::Copy($before,0,$base,[int]$offset,$before.Length)
    }
    if((Get-SoloSha256 $base) -ne $Delta.OriginalSha256){throw 'Rueckbau der Spiel-EXE ohne Koop-Code fehlgeschlagen.'}
    return ,$base
}

# LAN-Grund-EXE -> Koop-EXE (wie New-CoopPatchedBytes im Installer).
function ConvertTo-SoloCoopBytes([byte[]]$Base,$Delta){
    if($Base.Length -ne [int64]$Delta.OriginalLength -or (Get-SoloSha256 $Base) -ne $Delta.OriginalSha256){throw 'Spiel-EXE ohne Koop-Code stimmt nicht mit dem Paket ueberein.'}
    $result=New-Object byte[] ([int]$Delta.PatchedLength)
    [Array]::Copy($Base,$result,$Base.Length)
    foreach($run in $Delta.Changes){
        $before=[Convert]::FromBase64String($run.Before);$after=[Convert]::FromBase64String($run.After)
        $offset=[int64]$run.Offset
        if($before.Length -ne $after.Length -or $offset -lt 0 -or $offset+$before.Length -gt $Base.Length){throw 'Ungueltiger Patchbereich.'}
        for($i=0;$i -lt $before.Length;$i++){if($Base[$offset+$i] -ne $before[$i]){throw 'Patchsignatur stimmt nicht.'}}
        [Array]::Copy($after,0,$result,[int]$offset,$after.Length)
    }
    $append=[Convert]::FromBase64String($Delta.Append)
    if($Base.Length+$append.Length -ne $result.Length){throw 'Ungueltige Patchlaenge.'}
    [Array]::Copy($append,0,$result,$Base.Length,$append.Length)
    if((Get-SoloSha256 $result) -ne $Delta.PatchedSha256){throw 'Pruefsumme der Koop-EXE stimmt nicht.'}
    return ,$result
}

# Schreibt zuerst eine geprueft vollstaendige Temp-Datei und ersetzt dann die EXE in einem Schritt.
function Write-SoloExe([string]$Path,[byte[]]$Bytes,[string]$Expected){
    $tmp=$Path+'.solo-write'
    if(Test-Path -LiteralPath $tmp){Remove-Item -LiteralPath $tmp -Force}
    try{
        [IO.File]::WriteAllBytes($tmp,$Bytes)
        if((Get-SoloFileSha256 $tmp) -ne $Expected){throw 'Geschriebene Spiel-EXE stimmt nicht.'}
        $last=$null
        for($i=0;$i -lt 20;$i++){
            try{[IO.File]::Replace($tmp,$Path,[NullString]::Value);$last=$null;break}catch{$last=$_;Start-Sleep -Milliseconds 500}
        }
        if($last){throw $last}
    }finally{if(Test-Path -LiteralPath $tmp){Remove-Item -LiteralPath $tmp -Force}}
    if((Get-SoloFileSha256 $Path) -ne $Expected){throw 'Spiel-EXE konnte nicht verifiziert werden.'}
}

# coop = Koop-EXE dieses Pakets, base = LAN-Grund-EXE ohne Koop-Code, unknown = nicht anfassen.
function Get-SoloExeState([string]$Game,$Delta){
    $hash=Get-SoloFileSha256 (Join-Path $Game $script:SoloExeName)
    if($hash -eq $Delta.PatchedSha256){return 'coop'}
    if($hash -eq $Delta.OriginalSha256){return 'base'}
    return 'unknown'
}

function Set-SoloMarker([string]$Game,$Delta){
    $marker=Join-Path $Game $script:SoloMarkerName
    [ordered]@{Purpose='Solo session without co-op code; co-op EXE is restored afterwards.';CoopSha256=$Delta.PatchedSha256;BaseSha256=$Delta.OriginalSha256;Created=(Get-Date).ToString('o');ProcessId=$PID}|
        ConvertTo-Json|Set-Content -LiteralPath $marker -Encoding utf8
}

# Setzt nach einer (auch abgebrochenen) Solo-Sitzung die Koop-EXE wieder ein. Ohne Marker passiert nichts.
# Rueckgabe: none | running | already-coop | restored | foreign (unbekannte EXE, nichts veraendert).
function Restore-SoloCoopExe([string]$Game,[string]$DeltaPath){
    $marker=Join-Path $Game $script:SoloMarkerName
    if(!(Test-Path -LiteralPath $marker -PathType Leaf)){return 'none'}
    if(Test-SoloGameRunning){return 'running'}
    $delta=Read-SoloDelta $DeltaPath
    $exe=Join-Path $Game $script:SoloExeName
    $bytes=[IO.File]::ReadAllBytes($exe)
    $hash=Get-SoloSha256 $bytes
    if($hash -eq $delta.PatchedSha256){Remove-Item -LiteralPath $marker;return 'already-coop'}
    if($hash -ne $delta.OriginalSha256){return 'foreign'}
    Write-SoloExe $exe (ConvertTo-SoloCoopBytes $bytes $delta) $delta.PatchedSha256
    Remove-Item -LiteralPath $marker
    return 'restored'
}
