#requires -Version 7.0
param([Parameter(Mandatory)][string]$SessionFile,[Parameter(Mandatory)][string]$PackageDirectory,[switch]$DiagnosticsEnabled,[ValidateRange(10,86400)][int]$MaxSeconds=43200)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'Coop-SessionTools.ps1')
$record=Read-CoopJsonObject $SessionFile
if($record.Role -notin @('Host','Guest','Solo') -or $record.Nickname -notmatch '^[A-Za-z0-9_-]{1,16}$' -or !(Test-CoopSessionProcess $record.Client)){throw 'Session identity no longer matches / Sitzungsidentitaet stimmt nicht mehr.'}
$directory=[IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($SessionFile));$statusFile=Join-Path $directory 'session-status.json'
$compat=Get-CoopCompatibility $PackageDirectory
$peerState=New-CoopPeerState $compat $record.Nickname ([int]$record.MaxPlayers) ([int]$record.Difficulty)
$listener=$null;$lastSample=[datetime]::MinValue;$end=[datetime]::UtcNow.AddSeconds($MaxSeconds)
$diag=Join-Path ([IO.Path]::GetFullPath($record.GameDirectory)) ('TheRun-Coop-Logs\'+[IO.Path]::GetFileName($directory)+'-'+$record.Role+'-'+$record.Nickname)
$status=[ordered]@{Schema=1;Role=$record.Role;Nickname=$record.Nickname;Version=$compat.Version;Active=$true;Players=@();DiagnosticsEnabled=[bool]$DiagnosticsEnabled;DiagnosticDirectory=$(if($DiagnosticsEnabled){$diag}else{$null});PeerStatus='waiting';SessionDirectory=$directory}
try{
 if($record.Role -eq 'Host'){try{$listener=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Any,$script:CoopPeerPort);$listener.Start(8)}catch{$status.PeerStatus='port-unavailable'}}
 while([datetime]::UtcNow -lt $end -and (Test-CoopSessionProcess $record.Client)){
  if($listener){Receive-CoopPeerRequests $listener $peerState}
  if(([datetime]::UtcNow-$lastSample).TotalSeconds -ge 5){
   $lastSample=[datetime]::UtcNow;$status.UpdatedAt=$lastSample.ToString('o')
   if($record.Role -eq 'Guest'){
    try{$reply=Invoke-CoopPeerQuery ([string]$record.HostAddress) @{Protocol=1;Kind='hello';Nickname=$record.Nickname;Version=$compat.Version;Compatibility=$compat.Compatibility};$status.Players=@($reply.Players);$status.PeerStatus=$reply.Status;$status.HostDifficulty=$reply.Difficulty}
    catch{$status.PeerStatus='unavailable'}
   }elseif($record.Role -eq 'Host'){
    $reply=Invoke-CoopPeerRequest $peerState @{Protocol=1;Kind='probe';Nickname=$record.Nickname;Compatibility=$compat.Compatibility} '127.0.0.1'
    $status.Players=@($reply.Players);if($listener){$status.PeerStatus='compatible'}
   }
   Write-CoopJsonObjectAtomic $statusFile $status
   if($DiagnosticsEnabled){
    try{$p=Get-Process -Id ([int]$record.Client.Id) -ErrorAction Stop;Write-CoopDiagnosticEvent $diag @{At=$status.UpdatedAt;Type='sample';Role=$record.Role;Nickname=$record.Nickname;Version=$compat.Version;WorkingSetBytes=$p.WorkingSet64;CpuSeconds=$p.TotalProcessorTime.TotalSeconds;PeerStatus=$status.PeerStatus}}
    catch{$status.DiagnosticError=$_.Exception.Message}
   }
  }
  Start-Sleep -Milliseconds 200
 }
}finally{
 if($listener){$listener.Stop()};$status.Active=$false;$status.UpdatedAt=[datetime]::UtcNow.ToString('o')
 Write-CoopJsonObjectAtomic $statusFile $status
 if($DiagnosticsEnabled){try{Write-CoopDiagnosticEvent $diag @{At=$status.UpdatedAt;Type='session-ended';Role=$record.Role;Nickname=$record.Nickname;Version=$compat.Version}}catch{}}
}
