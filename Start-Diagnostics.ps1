param(
 [ValidateSet('Record','Mark','Export')][string]$Action='Record',
 [string]$PythonPath,[string]$Label,[ValidateRange(1,1800)][int]$Seconds=1800,
 [switch]$CheckOnly
)
$ErrorActionPreference='Stop'
$state=Join-Path $env:LOCALAPPDATA 'TheRunStoryCoop'
$root=Join-Path $state 'Diagnostics'
$latest=Join-Path $root 'latest-capture.txt'
$tool=Join-Path $PSScriptRoot 'diagnostics_tool\coop_diagnostic_capture.py'
if(!(Test-Path -LiteralPath $tool -PathType Leaf)){throw 'Diagnosewerkzeug fehlt. Das Entwicklungspaket vollstaendig entpacken.'}
if(!$PythonPath){
 $command=Get-Command python.exe -CommandType Application -ErrorAction SilentlyContinue|Select-Object -First 1
 if($command -and $command.Source -notlike '*\WindowsApps\*'){$PythonPath=$command.Source}
}
$pythonReady=$PythonPath -and (Test-Path -LiteralPath $PythonPath -PathType Leaf)
if($CheckOnly){
 [ordered]@{Status='configuration-check-only';PythonFound=[bool]$pythonReady;Action=$Action;ToolPresent=$true;SessionFilePresent=(Test-Path -LiteralPath (Join-Path $state 'active-session.json'));StartsGame=$false;OpensProcesses=$false}|ConvertTo-Json
 return
}
if(!$pythonReady){throw 'Python 3.10+ erforderlich. Alternativ -PythonPath mit dem vollstaendigen Pfad zu python.exe angeben. Das Spiel wird nicht veraendert.'}
if($Action -eq 'Record'){
 $session=Join-Path $state 'active-session.json'
 if(!(Test-Path -LiteralPath $session)){throw 'Zuerst eine Koop-Sitzung mit dem Starter beginnen.'}
 $record=Get-Content -LiteralPath $session -Raw|ConvertFrom-Json
 if($record.Status -ne 'running'){throw 'Die letzte Koop-Sitzung ist beendet. Zuerst Host oder Gast starten.'}
 $stamp=(Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8)
 $capture=Join-Path $root $stamp
 New-Item -Path $root -ItemType Directory -Force|Out-Null
 [IO.File]::WriteAllText($latest,$capture,[Text.Encoding]::UTF8)
 Write-Host 'Diagnose laeuft bis zum Zeitlimit oder Spielende. Dieses Fenster offen lassen.'
 Write-Host ('Aufzeichnung: '+$capture)
 & $PythonPath -u $tool record --session $session --output $capture --seconds $Seconds
 if($LASTEXITCODE -ne 0){throw 'Die Diagnose wurde mit einem Fehler beendet; Meldung oben beachten.'}
 Write-Host 'Diagnose abgeschlossen. Diagnose-Exportieren.cmd erstellt das lokale ZIP.'
 return
}
if(!(Test-Path -LiteralPath $latest)){throw 'Noch keine lokale Diagnoseaufzeichnung vorhanden.'}
$capture=[IO.Path]::GetFullPath(([IO.File]::ReadAllText($latest)).Trim())
$prefix=[IO.Path]::GetFullPath($root).TrimEnd('\')+'\'
if(!$capture.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)){throw 'Ungueltiger Diagnosepfad.'}
if($Action -eq 'Mark'){
 if(!$Label){$Label=Read-Host 'Kurze Markierung, z.B. HOST Ziel passiert'}
 & $PythonPath $tool mark $capture $Label
}else{
 $archive=Join-Path $root ((Split-Path -Leaf $capture)+'-'+(Get-Date -Format 'HHmmss')+'.zip')
 & $PythonPath $tool export $capture $archive
 if($LASTEXITCODE -eq 0){Write-Host ('Lokales Diagnosepaket: '+$archive)}
}
if($LASTEXITCODE -ne 0){throw 'Diagnoseaktion fehlgeschlagen; Meldung oben beachten.'}
