#requires -Version 7.0
# Persoenlicher Launcher-Schalter fuer den Koop-Audio-Mix (addons\music25\NFS-Audio-Patch.ps1). Nur dieser PC,
# keine gemeinsame Host-Option. Der Installer wendet den Mix immer an (Standard an). Vor dem Spielstart:
# - an:  nur anwenden, wenn der Launcher den Mix zuvor selbst entfernt hat (zuletzt 'Original'),
# - aus: immer wiederherstellen (ein Update/Neuinstallation kann den Mix wieder eingespielt haben).
# Das Audio-Skript prueft alle Stellen vor dem Schreiben, setzt bei Fehlern zurueck und schreibt nichts doppelt.
function Get-CoopMusicMixScript{return Join-Path $PSScriptRoot 'addons\music25\NFS-Audio-Patch.ps1'}

# Rueckgabe: State = 'Target' | 'Original' (zuletzt vom Launcher gesetzter Zustand), Ran = ob das Skript lief.
function Invoke-CoopMusicMix([string]$GameDirectory,[bool]$Enabled,[string]$LastApplied,[string]$ScriptPath=(Get-CoopMusicMixScript)){
    if($Enabled -and $LastApplied -ne 'Original'){return [pscustomobject]@{State='Target';Ran=$false}}
    if(!(Test-Path -LiteralPath $ScriptPath -PathType Leaf)){throw 'Musik-Patch fehlt im Paket: addons\music25\NFS-Audio-Patch.ps1'}
    $mode=if($Enabled){'Apply'}else{'Restore'}
    [void](& $ScriptPath -GamePath $GameDirectory -Mode $mode)
    return [pscustomobject]@{State=$(if($Enabled){'Target'}else{'Original'});Ran=$true}
}
