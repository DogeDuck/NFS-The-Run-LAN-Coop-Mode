#requires -Version 7.0
# Small launcher control channel. No game memory, injection, input or remote commands.
. (Join-Path $PSScriptRoot 'Coop-UserData.ps1')
$script:CoopPeerPort=25212
function Get-CoopCompatibility {
 param([Parameter(Mandatory)][string]$PackageDirectory)
 $manifest=Read-CoopJsonObject (Join-Path $PackageDirectory 'package-manifest.json') 4MB
 foreach($key in 'client_sha256','server_sha256'){if([string]$manifest[$key] -notmatch '^[a-fA-F0-9]{64}$'){throw 'Invalid package hashes / Ungueltige Paketpruefsummen.'}}
 $version=[string]$manifest.version
 if(!$version -or $version.Length -gt 128){throw 'Invalid package version / Ungueltige Paketversion.'}
 $text='1|'+$version+'|'+([string]$manifest.client_sha256).ToLowerInvariant()+'|'+([string]$manifest.server_sha256).ToLowerInvariant()
 $sha=[Security.Cryptography.SHA256]::Create()
 try{$hash=([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($text)))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
 return [ordered]@{Protocol=1;Version=$version;Compatibility=$hash;ClientSha256=$manifest.client_sha256;ServerSha256=$manifest.server_sha256}
}
function Read-CoopPeerLine {
 param([Parameter(Mandatory)]$Stream,[int]$MaxBytes=4096)
 $bytes=[Collections.Generic.List[byte]]::new()
 while($bytes.Count -le $MaxBytes){$b=$Stream.ReadByte();if($b -lt 0){throw 'Incomplete launcher message / Unvollstaendige Launchernachricht.'};if($b -eq 10){return [Text.Encoding]::UTF8.GetString($bytes.ToArray()).TrimEnd("`r")};$bytes.Add([byte]$b)}
 throw 'Launcher message too large / Launchernachricht zu gross.'
}
function Invoke-CoopPeerQuery {
 param([Parameter(Mandatory)][string]$HostAddress,[Parameter(Mandatory)][System.Collections.IDictionary]$Request,[int]$Port=25212,[int]$TimeoutMs=1200)
 $ip=$null
 if(![Net.IPAddress]::TryParse($HostAddress,[ref]$ip) -or $ip.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork -or $ip.Equals([Net.IPAddress]::Any) -or $ip.Equals([Net.IPAddress]::Broadcast) -or $ip.GetAddressBytes()[0] -ge 224){throw 'Invalid host IPv4 / Ungueltige Host-IPv4.'}
 $client=[Net.Sockets.TcpClient]::new()
 try{
  $client.SendTimeout=$TimeoutMs;$client.ReceiveTimeout=$TimeoutMs
  if(!$client.ConnectAsync($ip,$Port).Wait($TimeoutMs)){throw 'Host version check unavailable (TCP 25212) / Host-Versionspruefung nicht erreichbar (TCP 25212).'}
  $stream=$client.GetStream();$bytes=[Text.Encoding]::UTF8.GetBytes(($Request|ConvertTo-Json -Compress -Depth 6)+"`n")
  if($bytes.Length -gt 4096){throw 'Request too large / Anfrage zu gross.'}
  $stream.Write($bytes,0,$bytes.Length)
  $reply=Read-CoopPeerLine $stream 16384
  return ConvertFrom-Json -InputObject $reply -AsHashtable -Depth 8
 }finally{$client.Dispose()}
}
function New-CoopPeerState {
 param([Parameter(Mandatory)][System.Collections.IDictionary]$Compatibility,[Parameter(Mandatory)][string]$Nickname,[ValidateRange(1,4)][int]$MaxPlayers=2,[ValidateRange(0,3)][int]$Difficulty=1)
 if($Nickname -notmatch '^[A-Za-z0-9_-]{1,16}$'){throw 'Invalid nickname / Ungueltiger Spielername.'}
 return [ordered]@{Protocol=1;Version=$Compatibility.Version;Compatibility=$Compatibility.Compatibility;Nickname=$Nickname;MaxPlayers=$MaxPlayers;Difficulty=$Difficulty;Peers=@{};Session=[Guid]::NewGuid().ToString('N')}
}
function Invoke-CoopPeerRequest {
 param([Parameter(Mandatory)][System.Collections.IDictionary]$State,[Parameter(Mandatory)]$Request,[Parameter(Mandatory)][string]$RemoteAddress,[datetime]$Now=[datetime]::UtcNow)
 foreach($key in @($State.Peers.Keys)){if(($Now-$State.Peers[$key].Seen).TotalSeconds -gt 20){$State.Peers.Remove($key)}}
 $valid=$Request -is [System.Collections.IDictionary] -and $Request.Protocol -eq 1 -and $Request.Kind -in @('probe','hello') -and [string]$Request.Nickname -match '^[A-Za-z0-9_-]{1,16}$' -and [string]$Request.Compatibility -match '^[a-f0-9]{64}$'
 if(!$valid){return [ordered]@{Protocol=1;Status='invalid'}}
 $matches=[string]$Request.Compatibility -ceq [string]$State.Compatibility
 $status=if($matches){'compatible'}else{'mismatch'}
 if($matches -and $Request.Kind -eq 'hello'){
  $key=$RemoteAddress+'/'+[string]$Request.Nickname
  if([string]$Request.Nickname -ieq $State.Nickname -or (!$State.Peers.ContainsKey($key) -and $State.Peers.Count -ge ($State.MaxPlayers-1))){$status='full'}
  elseif($State.Peers.Values|Where-Object {$_.Nickname -ieq $Request.Nickname -and $_.Address -ne $RemoteAddress}){$status='duplicate-name'}
  else{$State.Peers[$key]=@{Nickname=[string]$Request.Nickname;Address=$RemoteAddress;Seen=$Now;Version=[string]$Request.Version}}
 }
 $peers=@([ordered]@{Nickname=$State.Nickname;Role='Host';Version=$State.Version})
 foreach($peer in $State.Peers.Values){$peers+= [ordered]@{Nickname=$peer.Nickname;Role='Guest';Version=$peer.Version;Address=$peer.Address}}
 return [ordered]@{Protocol=1;Status=$status;Version=$State.Version;Compatibility=$State.Compatibility;Session=$State.Session;MaxPlayers=$State.MaxPlayers;Difficulty=$State.Difficulty;Players=$peers;Source='launcher-heartbeats-not-native-race-state'}
}
function Receive-CoopPeerRequests {
 param([Parameter(Mandatory)]$Listener,[Parameter(Mandatory)][System.Collections.IDictionary]$State)
 $count=0
 while($count -lt 4 -and $Listener.Pending()){
  $peer=$Listener.AcceptTcpClient();$count++
  try{
   $peer.ReceiveTimeout=400;$peer.SendTimeout=400;$stream=$peer.GetStream()
   $request=ConvertFrom-Json -InputObject (Read-CoopPeerLine $stream 4096) -AsHashtable -Depth 6
   $answer=Invoke-CoopPeerRequest $State $request ([Net.IPEndPoint]$peer.Client.RemoteEndPoint).Address.ToString()
   $data=[Text.Encoding]::UTF8.GetBytes(($answer|ConvertTo-Json -Compress -Depth 8)+"`n");$stream.Write($data,0,$data.Length)
  }catch{}finally{$peer.Dispose()}
 }
}
function Test-CoopPeerVersion {
 param([Parameter(Mandatory)][string]$PackageDirectory,[Parameter(Mandatory)][string]$HostAddress,[Parameter(Mandatory)][string]$Nickname,[int]$Port=25212)
 $compat=Get-CoopCompatibility $PackageDirectory
 $request=[ordered]@{Protocol=1;Kind='probe';Nickname=$Nickname;Version=$compat.Version;Compatibility=$compat.Compatibility}
 $reply=Invoke-CoopPeerQuery $HostAddress $request $Port
 if($reply.Protocol -ne 1 -or $reply.Compatibility -cne $compat.Compatibility -or $reply.Status -ne 'compatible'){
  throw ('Host and guest need the same mod package / Host und Gast brauchen dasselbe Modpaket. Host: '+[string]$reply.Version+'; local/lokal: '+$compat.Version)
 }
 return $reply
}
function Assert-CoopPeerPortAvailable {
 param([int]$Port=25212)
 $listener=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Any,$Port)
 try{$listener.Start(1)}catch{throw 'Launcher session port already in use (TCP 25212) / Launcher-Sitzungsport ist bereits belegt (TCP 25212).'}finally{$listener.Stop()}
}
function Test-CoopSessionProcess {
 param([Parameter(Mandatory)]$Record)
 try{$p=Get-Process -Id ([int]$Record.Id) -ErrorAction Stop;return $p.ProcessName -eq 'Need For Speed The Run' -and $p.StartTime.ToUniversalTime().Ticks -eq [long]$Record.StartTicks}catch{return $false}
}
function Write-CoopDiagnosticEvent {
 param([Parameter(Mandatory)][string]$Directory,[Parameter(Mandatory)][System.Collections.IDictionary]$Event,[int]$MaxBytes=2MB)
 [void][IO.Directory]::CreateDirectory($Directory)
 $path=Join-Path $Directory 'events.jsonl'
 if((Test-Path -LiteralPath $path) -and (Get-Item -LiteralPath $path).Length -ge $MaxBytes){
  $old=Join-Path $Directory 'events.2.jsonl';if(Test-Path -LiteralPath $old){Remove-Item -LiteralPath $old}
  $previous=Join-Path $Directory 'events.1.jsonl';if(Test-Path -LiteralPath $previous){Move-Item -LiteralPath $previous -Destination $old}
  Move-Item -LiteralPath $path -Destination $previous
 }
 [IO.File]::AppendAllText($path,($Event|ConvertTo-Json -Compress -Depth 6)+"`n",[Text.UTF8Encoding]::new($false))
}
