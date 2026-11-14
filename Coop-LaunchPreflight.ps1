# Read-only launcher checks. No network packets, game launch, or settings writes.
function Test-CoopHostPortFree {
 param([int]$Port=25200)
 try{
  if(Get-Command Get-NetUDPEndpoint -ErrorAction SilentlyContinue){return (@(Get-NetUDPEndpoint -LocalPort $Port -ErrorAction SilentlyContinue).Count -eq 0)}
 }catch{}
 $socket=New-Object Net.Sockets.Socket ([Net.Sockets.AddressFamily]::InterNetwork),([Net.Sockets.SocketType]::Dgram),([Net.Sockets.ProtocolType]::Udp)
 try{
  $socket.ExclusiveAddressUse=$true
  $socket.Bind((New-Object Net.IPEndPoint ([Net.IPAddress]::Any),$Port))
  return $true
 }catch{return $false}finally{$socket.Dispose()}
}

function Test-CoopLaunchReadiness {
 param([Parameter(Mandatory)][string]$GameDirectory,[Parameter(Mandatory)][string]$PackageDirectory,[ValidateSet('Host','Guest','Solo')][string]$Role='Host',[string]$HostAddress='127.0.0.1',[string]$Language='en')
 $messages=@{
  game=@('Spielordner oder Spiel-EXE fehlt.','Game folder or game executable is missing.')
  running=@('Bitte das laufende Spiel und den Server zuerst schliessen.','Close the running game and server first.')
  ip=@('Bitte eine gueltige IPv4-Adresse des Hosts eingeben.','Enter a valid host IPv4 address.')
  package=@('Das Modpaket ist unvollstaendig. Bitte das vollstaendige Paket verwenden.','The mod package is incomplete. Use the complete package.')
  version=@('Andere Modversion erkannt. Bitte den aktuellen Launcher oder das passende Paket verwenden.','Different mod version detected. Use the current launcher or matching package.')
  port=@('UDP-Port 25200 ist bereits belegt oder nicht verfuegbar.','UDP port 25200 is already in use or unavailable.')
 }
 $index=if($Language -like 'de*'){0}else{1}
 $resolved=$null;$code='ready';$detail=$null
 try{
  $resolved=[IO.Path]::GetFullPath($GameDirectory.Trim('"')).TrimEnd('\')
  if(Test-Path -LiteralPath $resolved -PathType Leaf){
   if([IO.Path]::GetFileName($resolved) -ine 'Need For Speed The Run.exe'){throw 'game'}
   $resolved=[IO.Path]::GetDirectoryName($resolved)
  }
  if($resolved.Split('\') -contains 'THERUNBACKUP' -or !(Test-Path -LiteralPath (Join-Path $resolved 'Need For Speed The Run.exe') -PathType Leaf)){throw 'game'}
 }catch{$code='game'}
 if($code -eq 'ready' -and @(Get-Process -Name 'Need For Speed The Run','NFSTR_Server' -ErrorAction SilentlyContinue).Count){$code='running'}
 if($code -eq 'ready' -and $Role -eq 'Guest'){
  $parsed=$null
  if(![Net.IPAddress]::TryParse($HostAddress,[ref]$parsed) -or $parsed.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork){$code='ip'}
  elseif($parsed.Equals([Net.IPAddress]::Any) -or $parsed.Equals([Net.IPAddress]::Broadcast) -or $parsed.GetAddressBytes()[0] -ge 224){$code='ip'}
 }
 if($code -eq 'ready' -and $Role -ne 'Solo'){
  try{
   $manifest=Get-Content -LiteralPath (Join-Path $PackageDirectory 'package-manifest.json') -Raw|ConvertFrom-Json
   $expected=@{'Need For Speed The Run.exe'=[string]$manifest.client_sha256;'NFSTR_Server.exe'=[string]$manifest.server_sha256}
   $support=Get-Content -LiteralPath (Join-Path $PackageDirectory 'patches\support-files.json') -Raw|ConvertFrom-Json
   foreach($item in $support){$expected.Add([string]$item.RelativePath,[string]$item.Sha256)}
   foreach($relative in $expected.Keys){
    if($expected[$relative] -notmatch '^[0-9a-fA-F]{64}$'){throw 'package'}
    $path=[IO.Path]::GetFullPath((Join-Path $resolved $relative))
    if(!$path.StartsWith($resolved+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'package'}
    if(!(Test-Path -LiteralPath $path -PathType Leaf) -or (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ine $expected[$relative]){$code='version';$detail=$relative;break}
   }
  }catch{$code='package'}
 }
 if($code -eq 'ready' -and $Role -eq 'Host' -and !(Test-CoopHostPortFree)){$code='port'}
 $message=if($code -eq 'ready'){$null}else{$messages[$code][$index]}
 if($detail){$message+=' ('+$detail+')'}
 [pscustomobject]@{Ready=($code -eq 'ready');Code=$code;Message=$message;GameDirectory=$resolved}
}
