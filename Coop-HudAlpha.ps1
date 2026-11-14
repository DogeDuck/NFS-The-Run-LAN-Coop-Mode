#requires -Version 7.0
# Persoenlicher Launcher-Schalter fuer den HUD-Patch (addons\hudalpha\NFS-HUD-Patch.ps1, Claude 14.11.2026).
# Nur dieser PC. Auswahl: Original (Standard) | Dim (Tacho-Hintergrund 15 %) | Clear (Tacho-Hintergrund aus).
# Vor dem Spielstart (Spiel geschlossen):
# - Dim/Clear: immer 'Apply -Variant' (idempotent; ein Update kann UI.sb ersetzt haben),
# - Original: nur 'Restore', wenn der Launcher zuvor selbst Dim/Clear gesetzt hat.
# Das Patch-Skript prueft alle Stellen vor dem Schreiben und setzt bei Fehlern zurueck.
function Get-CoopHudAlphaScript{return Join-Path $PSScriptRoot 'addons\hudalpha\NFS-HUD-Patch.ps1'}

# Rueckgabe: State = 'Dim' | 'Clear' | 'Original' | '' (unveraendert), Ran = ob das Skript lief.
function Invoke-CoopHudAlpha([string]$GameDirectory,[string]$Choice,[string]$LastApplied,[string]$ScriptPath=(Get-CoopHudAlphaScript)){
    if($Choice -notin @('Dim','Clear')){$Choice='Original'}
    if($Choice -eq 'Original' -and $LastApplied -notin @('Dim','Clear')){return [pscustomobject]@{State=$LastApplied;Ran=$false}}
    if(!(Test-Path -LiteralPath $ScriptPath -PathType Leaf)){throw 'HUD-Patch fehlt im Paket: addons\hudalpha\NFS-HUD-Patch.ps1'}
    if($Choice -eq 'Original'){[void](& $ScriptPath -GamePath $GameDirectory -Mode Restore)}
    else{[void](& $ScriptPath -GamePath $GameDirectory -Mode Apply -Variant $Choice)}
    return [pscustomobject]@{State=$Choice;Ran=$true}
}
