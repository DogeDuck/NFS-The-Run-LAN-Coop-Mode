#requires -Version 7.0
param([Parameter(Mandatory)][string]$SessionFile,[Parameter(Mandatory)][string]$PackageDirectory,[switch]$DiagnosticsEnabled,[ValidateRange(10,86400)][int]$MaxSeconds=43200)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'Coop-SessionTools.ps1')
$record=Read-CoopJsonObject $SessionFile
if($record.Role -notin @('Host','Guest','Solo') -or $record.Nickname -notmatch '^[A-Za-z0-9_-]{1,16}$' -or !(Test-CoopSessionProcess $record.Client)){throw 'Session identity no longer matches / Sitzungsidentitaet stimmt nicht mehr.'}
# Retain this verified process handle. This avoids a process-list query on every
# broker tick and cannot silently follow a later process that reuses the PID.
$observed=Get-Process -Id ([int]$record.Client.Id) -ErrorAction Stop
[void]$observed.Handle
if($observed.ProcessName -ne 'Need For Speed The Run' -or $observed.StartTime.ToUniversalTime().Ticks -ne [long]$record.Client.StartTicks){$observed.Dispose();throw 'Session process changed / Sitzungsprozess hat gewechselt.'}
$directory=[IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($SessionFile));$statusFile=Join-Path $directory 'session-status.json'
$compat=Get-CoopCompatibility $PackageDirectory
$peerState=New-CoopPeerState $compat $record.Nickname ([int]$record.MaxPlayers) ([int]$record.Difficulty)
$listener=$null;$lastSample=[datetime]::MinValue;$end=[datetime]::UtcNow.AddSeconds($MaxSeconds)
$diag=Join-Path ([IO.Path]::GetFullPath($record.GameDirectory)) ('TheRun-Coop-Logs\'+[IO.Path]::GetFileName($directory)+'-'+$record.Role+'-'+$record.Nickname)
$status=[ordered]@{Schema=1;Role=$record.Role;Nickname=$record.Nickname;Version=$compat.Version;Active=$true;Players=@();DiagnosticsEnabled=[bool]$DiagnosticsEnabled;DiagnosticDirectory=$(if($DiagnosticsEnabled){$diag}else{$null});PeerStatus='waiting';SessionDirectory=$directory}
try{
 $qteWorker=$null
 if($record.Role -in @('Host','Guest')){
  $manifest=Read-CoopJsonObject (Join-Path $PackageDirectory 'package-manifest.json') 4MB
  if($manifest.qte_mirror_data){
   $info=[Diagnostics.ProcessStartInfo]::new((Join-Path $PSHOME 'pwsh.exe'));$info.UseShellExecute=$false;$info.CreateNoWindow=$true
   foreach($arg in @('-NoProfile','-File',(Join-Path $PackageDirectory 'qte_mirror_net.ps1'),'-Mode',$record.Role,'-ProcessId',[string]$record.Client.Id,'-DataAddress',('0x{0:X}' -f [long]$manifest.qte_mirror_data),'-SessionFile',$SessionFile,'-PackageDirectory',$PackageDirectory)){$info.ArgumentList.Add($arg)}
   if($record.Role -eq 'Guest'){$info.ArgumentList.Add('-HostAddress');$info.ArgumentList.Add([string]$record.HostAddress)}
   $qteWorker=[Diagnostics.Process]::Start($info)
  }
 }
 if($record.Role -eq 'Host'){try{$listener=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Any,$script:CoopPeerPort);$listener.Start(8)}catch{$status.PeerStatus='port-unavailable'}}
 while([datetime]::UtcNow -lt $end -and !$observed.HasExited){
  if($listener){Receive-CoopPeerRequests $listener $peerState}
  if(([datetime]::UtcNow-$lastSample).TotalSeconds -ge 5){
   $lastSample=[datetime]::UtcNow;$status.UpdatedAt=$lastSample.ToString('o')
   if($record.Role -eq 'Guest'){
    try{$reply=Invoke-CoopPeerQuery ([string]$record.HostAddress) @{Protocol=1;Kind='hello';Nickname=$record.Nickname;Version=$compat.Version;Compatibility=$compat.Compatibility};$status.Players=@($reply.Players);$status.PeerStatus=$reply.Status;$status.HostDifficulty=$reply.Difficulty}
    catch{$status.PeerStatus='unavailable'}
   }elseif($record.Role -eq 'Host'){
    $reply=Invoke-CoopPeerRequest $peerState @{Protocol=1;Kind='probe';Nickname=$record.Nickname;Compatibility=$compat.Compatibility} '127.0.0.1'
    $status.Players=@($reply.Players);if($listener){$status.PeerStatus='compatible'}
   }else{
    $status.Players=@([ordered]@{Nickname=$record.Nickname;Role='Solo';Version=$compat.Version});$status.PeerStatus='solo'
   }
   Write-CoopJsonObjectAtomic $statusFile $status
   if($DiagnosticsEnabled){
    try{$observed.Refresh();Write-CoopDiagnosticEvent $diag @{At=$status.UpdatedAt;Type='sample';Role=$record.Role;Nickname=$record.Nickname;Version=$compat.Version;WorkingSetBytes=$observed.WorkingSet64;CpuSeconds=$observed.TotalProcessorTime.TotalSeconds;PeerStatus=$status.PeerStatus}}
    catch{$status.DiagnosticError=$_.Exception.Message}
   }
  }
  Start-Sleep -Milliseconds 200
 }
}finally{
 if($qteWorker){if(!$qteWorker.HasExited){[void]$qteWorker.WaitForExit(1500)};$qteWorker.Dispose()}
 if($listener){$listener.Stop()};$status.Active=$false;$status.UpdatedAt=[datetime]::UtcNow.ToString('o')
 $status.EndReason='helper-stopped';$status.ExitCode=$null
 try{if($observed.HasExited){$status.EndReason='game-exited';$status.ExitCode=$observed.ExitCode}}catch{}
 Write-CoopJsonObjectAtomic $statusFile $status
 if($DiagnosticsEnabled){try{Write-CoopDiagnosticEvent $diag @{At=$status.UpdatedAt;Type='session-ended';Role=$record.Role;Nickname=$record.Nickname;Version=$compat.Version;EndReason=$status.EndReason;ExitCode=$status.ExitCode}}catch{}}
 $observed.Dispose()
}
