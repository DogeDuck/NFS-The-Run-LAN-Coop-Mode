#requires -Version 7.0
# Einzelspieler wie im Originalspiel; Definitive Edition, Musik-Addon und Debug-Menue bleiben aktiv.
# Die Koop-Patches stecken in der Spiel-EXE und wuerden sonst auch hier wirken (z.B. nur Select-Strassenreset
# statt Checkpoint-Reset, Koop-Story-Hooks). Fuer die Sitzung wird deshalb die LAN-Grund-EXE ohne Koop-Code
# exakt aus patches\client.json zurueckgebaut und nach Spielende die Koop-EXE wieder eingesetzt (SHA256-geprueft,
# siehe Coop-SoloExe.ps1). In der Helper-INI wird nur EnableLANOnlineTweaks auf 0 gesetzt (kein LAN/Koop),
# EnableDebugModeMenus bleibt 1. Nach Spielende wird die INI byte-genau zurueckgestellt, sofern sie in der
# Zwischenzeit niemand anders veraendert hat. Spielstand wird nicht angefasst.
param([Parameter(Mandatory=$true)][string]$GameDirectory,[switch]$CheckOnly,[ValidateSet('auto','de','en')][string]$Language='auto',[switch]$ShowErrorDialog,
      [string]$DeltaPath=(Join-Path $PSScriptRoot 'patches\client.json'))
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'Coop-Language.ps1')
. (Join-Path $PSScriptRoot 'Coop-SoloExe.ps1')
$script:CoopLanguage=Get-CoopLanguage $Language
trap {
    $message=ConvertTo-CoopUserError $_.Exception.Message
    if($ShowErrorDialog -and !$CheckOnly){
        Add-Type -AssemblyName System.Windows.Forms
        [void][Windows.Forms.MessageBox]::Show($message,(Get-CoopText Title))
        exit 1
    }
    throw $message
}
$game=[IO.Path]::GetFullPath($GameDirectory)
$exe=Join-Path $game 'Need For Speed The Run.exe'
$ini=Join-Path $game 'Scripts\NFSTR_LANOnlineHelper.ini'
if(!(Test-Path -LiteralPath $exe)){throw (Get-CoopText MissingGame)}
if(!$CheckOnly -and @(Get-Process -Name 'Need For Speed The Run','NFSTR_Server' -ErrorAction SilentlyContinue).Count){throw (Get-CoopText Running)}

function Get-SoloConfig([string]$Text){
    $t=[regex]::Replace($Text,'(?m)^EnableLANOnlineTweaks\s*=.*$','EnableLANOnlineTweaks = 0')
    if($t -notmatch '(?m)^EnableDebugModeMenus\s*='){return $t}
    return [regex]::Replace($t,'(?m)^EnableDebugModeMenus\s*=.*$','EnableDebugModeMenus = 1')
}

$delta=if(Test-Path -LiteralPath $DeltaPath -PathType Leaf){Read-SoloDelta $DeltaPath}else{$null}
if(!$CheckOnly){
    if(!$delta){throw 'Koop-Patchbeschreibung fehlt: patches\client.json'}
    # Abgebrochene fruehere Solo-Sitzung: erst die Koop-EXE zuruecksetzen, dann normal weiter.
    [void](Restore-SoloCoopExe $game $DeltaPath)
}
$exeState=if($delta){Get-SoloExeState $game $delta}else{'unknown'}
# removed-for-session: Koop-EXE wird fuer die Sitzung ersetzt; none: EXE hat schon keinen Koop-Code.
$coopCode=@{coop='removed-for-session';base='none';unknown='unknown'}[$exeState]
if(!$CheckOnly -and $exeState -eq 'unknown'){throw 'Spiel-EXE passt nicht zu diesem Koop-Paket.'}

$original=$null;$solo=$null;$text=$null
if(Test-Path -LiteralPath $ini){
    $original=[IO.File]::ReadAllBytes($ini)
    $text=[Text.Encoding]::ASCII.GetString($original)
    $solo=Get-SoloConfig $text
}
if($CheckOnly){
    if($null -ne $original){[ordered]@{Status='check-only';Language=$script:CoopLanguage;Changes=($solo -ne $text);LanTweaks=0;DebugMenus=($solo -match '(?m)^EnableDebugModeMenus = 1');CoopCode=$coopCode}|ConvertTo-Json}
    else{[ordered]@{Status='check-only';Language=$script:CoopLanguage;Changes=$false;LanTweaks=$null;CoopCode=$coopCode}|ConvertTo-Json}
    return
}

$soloHash=$null;$swapped=$false;$restoreState=$null
try{
    if($null -ne $original){
        if($solo -ne $text){[IO.File]::WriteAllText($ini,$solo,[Text.Encoding]::ASCII)}
        $soloHash=(Get-FileHash -LiteralPath $ini -Algorithm SHA256).Hash
    }
    if($exeState -eq 'coop'){
        $base=ConvertTo-SoloBaseBytes ([IO.File]::ReadAllBytes($exe)) $delta
        Set-SoloMarker $game $delta
        $swapped=$true
        Write-SoloExe $exe $base $delta.OriginalSha256
        $base=$null
    }
    $p=Start-Process -FilePath $exe -WorkingDirectory $game -PassThru
    $p.WaitForExit()
    # Auch ein vom Spiel selbst neu gestarteter Prozess muss beendet sein, bevor die Koop-EXE zurueckkommt.
    while(Test-SoloGameRunning){Start-Sleep -Seconds 2}
}finally{
    $restoreError=$null
    if($swapped){try{$restoreState=Restore-SoloCoopExe $game $DeltaPath}catch{$restoreError=$_}}
    if($original -and (Test-Path -LiteralPath $ini) -and (Get-FileHash -LiteralPath $ini -Algorithm SHA256).Hash -eq $soloHash){
        [IO.File]::WriteAllBytes($ini,$original)
    }
}
# Marker bleibt dann liegen; der naechste Start (Koop oder Solo) setzt die Koop-EXE zurueck.
if($swapped -and ($restoreError -or $restoreState -notin @('restored','already-coop'))){throw 'Koop-EXE konnte nach dem Solo-Spiel nicht wiederhergestellt werden.'}
