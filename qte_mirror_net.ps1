#requires -Version 7.0
<#
HOST-QTE-Spiegel uebers Netz (Claude 15.11.2026). Transport fuer qte_host_mirror_adapter zwischen zwei PCs.

Host-Modus:  liest im eigenen Spielclient SEND_MASK/SEND_SEQ (DataAddress + 0x40/0x44) und schickt jede neue Maske
             als UDP-Paket an alle Gast-IPs (Port Standard 25214).
Gast-Modus:  empfaengt die Pakete und schreibt RECV_MASK + RECV_TICK (DataAddress + 0x48/0x4C) in den eigenen
             Client; RECV_TICK = eigener GetTickCount, damit der Stub nur frische Masken (<300 ms) einmischt.
Paket: 'TRQM' (4 Byte) + Version 1 (1 Byte) + Sequenz (uint32) + Maske (uint32) = 13 Byte, little endian.
Nur lesen/schreiben dieser 8 Bytes im eigenen Prozess; keine Eingaben werden simuliert, nichts installiert.
Aufruf:
  pwsh -File qte_mirror_net.ps1 -Mode Host  -ProcessId <PID> -DataAddress 0x12340000 -Peers 26.1.2.3
  pwsh -File qte_mirror_net.ps1 -Mode Guest -ProcessId <PID> -DataAddress 0x56780000 -HostAddress 26.1.2.4
#>
param(
    [Parameter(Mandatory)][ValidateSet('Host','Guest')][string]$Mode,
    [Parameter(Mandatory)][int]$ProcessId,
    [Parameter(Mandatory)][string]$DataAddress,
    [string[]]$Peers=@(),
    [string]$HostAddress='',
    [int]$Port=25214,
    [int]$Seconds=43200,
    [string]$SessionFile,
    [string]$PackageDirectory=$PSScriptRoot
)
$ErrorActionPreference='Stop'
Add-Type -Namespace TRQ -Name Native -MemberDefinition @'
[DllImport("kernel32.dll", SetLastError=true)] public static extern System.IntPtr OpenProcess(uint access, bool inherit, int pid);
[DllImport("kernel32.dll", SetLastError=true)] public static extern bool ReadProcessMemory(System.IntPtr h, System.IntPtr addr, byte[] buf, int size, out int read);
[DllImport("kernel32.dll", SetLastError=true)] public static extern bool WriteProcessMemory(System.IntPtr h, System.IntPtr addr, byte[] buf, int size, out int written);
[DllImport("kernel32.dll")] public static extern uint GetTickCount();
[DllImport("kernel32.dll")] public static extern bool CloseHandle(System.IntPtr h);
'@
$proc=Get-Process -Id $ProcessId -ErrorAction Stop
if($proc.ProcessName -ne 'Need For Speed The Run'){throw "PID $ProcessId ist nicht der Spielclient."}
if($SessionFile){
 $record=Get-Content -LiteralPath $SessionFile -Raw|ConvertFrom-Json
 $manifest=Get-Content -LiteralPath (Join-Path $PackageDirectory 'package-manifest.json') -Raw|ConvertFrom-Json
 if($proc.StartTime.ToUniversalTime().Ticks -ne [long]$record.Client.StartTicks -or $proc.Path -ine (Join-Path $record.GameDirectory 'Need For Speed The Run.exe') -or (Get-FileHash -LiteralPath $proc.Path).Hash -ine $manifest.client_sha256){throw 'QTE session identity/version mismatch'}
}
[void]$proc.Handle
$data=[Convert]::ToInt64($DataAddress.Replace('0x',''),16)
if($data -le 0 -or $data -ge 0x80000000){throw 'Ungueltige DataAddress.'}
$handle=[TRQ.Native]::OpenProcess(0x38,$false,$ProcessId)   # VM_READ | VM_WRITE | VM_OPERATION
if($handle -eq [IntPtr]::Zero){throw 'Prozess konnte nicht geoeffnet werden.'}
function Read-Block([long]$offset,[int]$size){$b=New-Object byte[] $size;$n=0
    if(-not [TRQ.Native]::ReadProcessMemory($handle,[IntPtr]($data+$offset),$b,$size,[ref]$n) -or $n -ne $size){throw 'Lesen fehlgeschlagen (Spiel beendet?).'};return ,$b}
function Write-Block([long]$offset,[byte[]]$b){$n=0
    if(-not [TRQ.Native]::WriteProcessMemory($handle,[IntPtr]($data+$offset),$b,$b.Length,[ref]$n) -or $n -ne $b.Length){throw 'Schreiben fehlgeschlagen.'}}
# Plausibility: the stub's data block carries the env name at +0x20.
$name=[Text.Encoding]::ASCII.GetString((Read-Block 0x20 16))
if($name -ne 'THERUN_COOP_ROLE'){[TRQ.Native]::CloseHandle($handle)|Out-Null;throw 'DataAddress zeigt nicht auf den QTE-Spiegel-Block.'}
$udp=New-Object Net.Sockets.UdpClient
$end=(Get-Date).AddSeconds($Seconds);$count=0
try{
    if($Mode -eq 'Host'){
        $targets=@($Peers|ForEach-Object{New-Object Net.IPEndPoint([Net.IPAddress]::Parse($_),$Port)})
        $lastSeq=-1;$nextDiscovery=[datetime]::MinValue
        Write-Output "Host-Spiegel aktiv: $($Peers -join ', ') Port $Port"
        while((Get-Date) -lt $end -and !$proc.HasExited){
            if($SessionFile -and [datetime]::UtcNow -ge $nextDiscovery){
             $nextDiscovery=[datetime]::UtcNow.AddSeconds(1);$targets=@()
             try{$status=Get-Content -LiteralPath (Join-Path (Split-Path $SessionFile) 'session-status.json') -Raw|ConvertFrom-Json
              foreach($address in @($status.Players|Where-Object Role -eq 'Guest'|Select-Object -ExpandProperty Address -Unique)){
               $ip=$null;if([Net.IPAddress]::TryParse($address,[ref]$ip) -and $ip.AddressFamily -eq [Net.Sockets.AddressFamily]::InterNetwork -and $ip.GetAddressBytes()[0] -lt 224 -and !$ip.Equals([Net.IPAddress]::Any)){$targets+= [Net.IPEndPoint]::new($ip,$Port)}
              }
             }catch{}
            }
            $b=Read-Block 0x40 8;$mask=[BitConverter]::ToUInt32($b,0);$seq=[BitConverter]::ToUInt32($b,4)
            if($seq -ne $lastSeq){
                $pkt=[byte[]](0x54,0x52,0x51,0x4D,1)+[BitConverter]::GetBytes([uint32]$seq)+[BitConverter]::GetBytes([uint32]$mask)
                foreach($t in $targets){[void]$udp.Send($pkt,$pkt.Length,$t)};$lastSeq=$seq;$count++
            }
            Start-Sleep -Milliseconds 10
        }
    }else{
        $udp.Close();$udp=New-Object Net.Sockets.UdpClient($Port);$udp.Client.ReceiveTimeout=500
        if(!$HostAddress){throw 'Verified host address required'}
        $hostIp=[Net.IPAddress]::Parse($HostAddress)
        Write-Output "Gast-Spiegel aktiv: Port $Port$(if($hostIp){', nur von '+$hostIp})"
        $remote=New-Object Net.IPEndPoint([Net.IPAddress]::Any,0);$lastSeq=-1
        while((Get-Date) -lt $end -and !$proc.HasExited){
            try{$pkt=$udp.Receive([ref]$remote)}catch [Net.Sockets.SocketException]{continue}
            if($pkt.Length -ne 13 -or $pkt[0] -ne 0x54 -or $pkt[1] -ne 0x52 -or $pkt[2] -ne 0x51 -or $pkt[3] -ne 0x4D -or $pkt[4] -ne 1){continue}
            if($hostIp -and -not $remote.Address.Equals($hostIp)){continue}
            $seq=[BitConverter]::ToUInt32($pkt,5);$mask=[BitConverter]::ToUInt32($pkt,9)
            if($lastSeq -ge 0 -and $seq -le $lastSeq){continue}
            Write-Block 0x48 ([BitConverter]::GetBytes([uint32]$mask)+[BitConverter]::GetBytes([uint32][TRQ.Native]::GetTickCount()))
            $lastSeq=$seq;$count++
        }
    }
}finally{
    $udp.Close();[TRQ.Native]::CloseHandle($handle)|Out-Null
    Write-Output "Beendet, Masken: $count"
}
