#requires -Version 7.0
# Einzelspieler mit allen Mods: Definitive Edition, Musik-Addon und Debug-Menue bleiben aktiv.
# Fuer die Sitzung wird in der Helper-INI nur EnableLANOnlineTweaks auf 0 gesetzt (kein LAN/Koop),
# EnableDebugModeMenus bleibt 1. Nach Spielende wird die INI byte-genau zurueckgestellt,
# sofern sie in der Zwischenzeit niemand anders veraendert hat. Spielstand wird nicht angefasst.
param([Parameter(Mandatory=$true)][string]$GameDirectory,[switch]$CheckOnly,[ValidateSet('auto','de','en')][string]$Language='auto',[switch]$ShowErrorDialog)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'Coop-Language.ps1')
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

$original=$null;$soloHash=$null
if(Test-Path -LiteralPath $ini){
    $original=[IO.File]::ReadAllBytes($ini)
    $text=[Text.Encoding]::ASCII.GetString($original)
    $solo=Get-SoloConfig $text
    if($CheckOnly){[ordered]@{Status='check-only';Language=$script:CoopLanguage;Changes=($solo -ne $text);LanTweaks=0;DebugMenus=($solo -match '(?m)^EnableDebugModeMenus = 1')}|ConvertTo-Json;return}
    if($solo -ne $text){[IO.File]::WriteAllText($ini,$solo,[Text.Encoding]::ASCII)}
    $soloHash=(Get-FileHash -LiteralPath $ini -Algorithm SHA256).Hash
}elseif($CheckOnly){[ordered]@{Status='check-only';Language=$script:CoopLanguage;Changes=$false;LanTweaks=$null}|ConvertTo-Json;return}
try{
    $p=Start-Process -FilePath $exe -WorkingDirectory $game -PassThru
    $p.WaitForExit()
}finally{
    if($original -and (Test-Path -LiteralPath $ini) -and (Get-FileHash -LiteralPath $ini -Algorithm SHA256).Hash -eq $soloHash){
        [IO.File]::WriteAllBytes($ini,$original)
    }
}
