param(
 [ValidateSet('Capture','Export')][string]$Action='Capture',
 [string]$PythonPath,[string]$SessionFile,[ValidateRange(1,300)][int]$Seconds=180,
 [switch]$CheckOnly
)
$ErrorActionPreference='Stop'
$state=Join-Path $env:LOCALAPPDATA 'TheRunStoryCoop'
$root=Join-Path $state 'CrashDiagnostics'
$latest=Join-Path $root 'latest-capture.txt'
$tool=Join-Path $PSScriptRoot 'diagnostics_tool\record_bridge_exception.py'
if(!(Test-Path -LiteralPath $tool -PathType Leaf)){throw 'Die Absturzdiagnose fehlt. Entwicklungspaket vollstaendig entpacken.'}
if(!$PythonPath){
 $command=Get-Command python.exe -CommandType Application -ErrorAction SilentlyContinue|Select-Object -First 1
 if($command -and $command.Source -notlike '*\WindowsApps\*'){$PythonPath=$command.Source}
}
$ready=$PythonPath -and (Test-Path -LiteralPath $PythonPath -PathType Leaf)
$platformReady=$false
if($ready){
 $platform=& $PythonPath -c 'import sys,struct; print(int(sys.version_info >= (3,10) and struct.calcsize(chr(80))==8))'
 $platformReady=$LASTEXITCODE -eq 0 -and $platform -eq '1'
}
if($CheckOnly){
 [ordered]@{Status='configuration-check-only';PythonFound=[bool]$ready;Python64Bit310OrNewer=[bool]$platformReady;ToolPresent=$true;StartsGame=$false;AttachesDebugger=$false;WritesGameMemory=$false}|ConvertTo-Json
 return
}
if(!$platformReady){throw 'Absturzdiagnose braucht Python 3.10+ in 64 Bit. Die normale Koop-Mod funktioniert ohne dieses Zusatzwerkzeug.'}
if($Action -eq 'Capture'){
 if(!$SessionFile){$SessionFile=Join-Path $state 'active-session.json'}
 if(!(Test-Path -LiteralPath $SessionFile)){throw 'Zuerst Koop mit dem aktuellen Starter verbinden.'}
 $record=Get-Content -LiteralPath $SessionFile -Raw|ConvertFrom-Json
 if($record.Status -ne 'running'){throw 'Keine aktive Koop-Sitzung im Starter gefunden.'}
 $stamp=(Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8)
 $capture=Join-Path $root $stamp
 New-Item -Path $root -ItemType Directory -Force|Out-Null
 [IO.File]::WriteAllText($latest,$capture,[Text.Encoding]::UTF8)
 Write-Host 'Absturzdiagnose laeuft. Das Spiel kann beim Erfassen kurz anhalten.'
 Write-Host 'Sie beendet sich nach hoechstens fuenf Minuten. Dieses Fenster offen lassen.'
 & $PythonPath -B -u $tool --run --session $SessionFile --seconds $Seconds --output $capture
 if($LASTEXITCODE -eq 0){Write-Host 'Aufnahme beendet. Diagnose-Absturz-Exportieren.cmd erstellt das lokale ZIP.'}
}else{
 if(!(Test-Path -LiteralPath $latest)){throw 'Noch keine lokale Absturzaufnahme vorhanden.'}
 $capture=[IO.Path]::GetFullPath(([IO.File]::ReadAllText($latest)).Trim())
 $prefix=[IO.Path]::GetFullPath($root).TrimEnd('\')+'\'
 if(!$capture.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)){throw 'Ungueltiger Aufnahmepfad.'}
 $archive=Join-Path $root ((Split-Path -Leaf $capture)+'-'+(Get-Date -Format 'HHmmss')+'.zip')
 & $PythonPath -B $tool --export $capture --output $archive
 if($LASTEXITCODE -eq 0){Write-Host ('Lokales Diagnosepaket: '+$archive)}
}
if($LASTEXITCODE -ne 0){throw 'Absturzdiagnose meldet einen Fehler. Meldung oben beachten; kein Spiel wurde gestartet.'}
