. (Join-Path $PSScriptRoot 'Coop-Core.ps1')
$active=Join-Path $script:CoopStateRoot 'active-session.json'
if(!(Test-Path -LiteralPath $active)){Write-Output 'Keine gestartete Koop-Sitzung gefunden.';return}
$record=Get-Content -LiteralPath $active -Raw|ConvertFrom-Json
$game=Get-CoopGameDirectory $record.GameDirectory
foreach($entry in @(@{Record=$record.Client;Name='Need For Speed The Run.exe'},@{Record=$record.Server;Name='NFSTR_Server.exe'})){
    if($entry.Record){if($entry.Record.Path -ne (Join-Path $game $entry.Name)){throw 'Unerwarteter Prozesspfad in Sitzungsdatei.'};Stop-CoopOwnedProcess $entry.Record -Graceful}
}
Write-Output 'Koop-Spiel und zugehoeriger Server beendet.'
