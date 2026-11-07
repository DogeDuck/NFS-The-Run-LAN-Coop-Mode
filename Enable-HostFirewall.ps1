param([string]$GameDirectory,[Parameter(Mandatory=$true)][string]$FriendVpnAddress)
. (Join-Path $PSScriptRoot 'Coop-Core.ps1')
$game=Get-CoopGameDirectory $GameDirectory
Test-CoopReady $game
$address=$null
if(![Net.IPAddress]::TryParse($FriendVpnAddress,[ref]$address) -or $address.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork){throw 'Eine einzelne VPN-IPv4 des Kumpels angeben.'}
if($FriendVpnAddress -eq '0.0.0.0' -or $FriendVpnAddress -eq '255.255.255.255'){throw 'Eine einzelne Peer-Adresse angeben.'}
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
if(!(New-Object Security.Principal.WindowsPrincipal($identity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'Diesen gezielten Firewall-Schritt bei Bedarf in einer PowerShell als Administrator starten.'}
$rule='TheRunStoryCoop-UDP25200-'+$FriendVpnAddress.Replace('.','-')
if(!(Get-NetFirewallRule -Name $rule -ErrorAction SilentlyContinue)){
 New-NetFirewallRule -Name $rule -DisplayName "The Run Story-Coop: $FriendVpnAddress" -Direction Inbound -Action Allow -Protocol UDP -LocalPort 25200 -Program (Join-Path $game 'NFSTR_Server.exe') -RemoteAddress $FriendVpnAddress -Profile Any|Out-Null
}
$garageRule='TheRunStoryCoop-Garage-TCP25211-'+$FriendVpnAddress.Replace('.','-')
if(!(Get-NetFirewallRule -Name $garageRule -ErrorAction SilentlyContinue)){
 New-NetFirewallRule -Name $garageRule -DisplayName "The Run Story-Coop Garage: $FriendVpnAddress" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 25211 -Program (Join-Path $PSHOME 'pwsh.exe') -RemoteAddress $FriendVpnAddress -Profile Any|Out-Null
 Write-Output "Garage-Regel angelegt: $garageRule (nur TCP 25211, nur von $FriendVpnAddress)"
}
Write-Output "Spiel-Regel vorhanden: $rule"
Write-Output "Zum Entfernen: Remove-NetFirewallRule -Name '$rule'; Remove-NetFirewallRule -Name '$garageRule'"
