# Download the user-provided original LAN archive. Never execute its scripts.
$script:CoopLanArchiveSha='785524270197f92cf2438b600f83a610dde7dbfe0c91372de343abd095bbc44d'
function Get-CoopOriginalLanArchive {
 param([Parameter(Mandatory)][string]$CacheDirectory)
 [void][IO.Directory]::CreateDirectory($CacheDirectory)
 $output=Join-Path $CacheDirectory 'NFSTR_LANScript_v1_May292024.7z'
 if((Test-Path -LiteralPath $output) -and (Get-FileHash -LiteralPath $output).Hash -ieq $script:CoopLanArchiveSha){return $output}
 $response=Invoke-RestMethod -Uri 'https://g.api.mega.co.nz/cs?id=2061115' -Method Post -Body '[{"a":"g","g":1,"ssl":1,"p":"C9xEUY4I"}]' -ContentType 'application/json' -TimeoutSec 30
 $meta=@($response)[0]
 if(!$meta.g -or [long]$meta.s -ne 16271509){throw 'LAN download unavailable / LAN-Download nicht verfuegbar.'}
 $url=[Uri]$meta.g
 if($url.Scheme -ne 'https' -or !$url.Host.EndsWith('.userstorage.mega.co.nz',[StringComparison]::OrdinalIgnoreCase)){throw 'Unexpected LAN download source / Unerwartete LAN-Downloadquelle.'}
 $encrypted=Join-Path $CacheDirectory ('encrypted-'+[Guid]::NewGuid().ToString('N'))
 $temporary=Join-Path $CacheDirectory ('archive-'+[Guid]::NewGuid().ToString('N'))
 try{
  Invoke-WebRequest -Uri $url.AbsoluteUri -OutFile $encrypted -TimeoutSec 180
  if((Get-Item -LiteralPath $encrypted).Length -ne 16271509){throw 'Incomplete LAN download / LAN-Download unvollstaendig.'}
  if(!('CoopLanCrypto' -as [type])){
   Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Security.Cryptography;
public static class CoopLanCrypto {
 public static void Decrypt(string source, string destination) {
  byte[] full=Convert.FromBase64String("-6Dnmu4kfHJr4D-E-5JiOEHa2vlVfj_eNjiMcxW6cC8".Replace('-','+').Replace('_','/')+"=");
  byte[] key=new byte[16],counter=new byte[16],stream=new byte[16],block=new byte[16];
  for(int i=0;i<16;i++)key[i]=(byte)(full[i]^full[i+16]);
  Array.Copy(full,16,counter,0,8);
  using(Aes aes=Aes.Create()) {
   aes.Key=key;aes.Mode=CipherMode.ECB;aes.Padding=PaddingMode.None;
   using(ICryptoTransform transform=aes.CreateEncryptor())
   using(FileStream input=File.OpenRead(source))
   using(FileStream output=new FileStream(destination,FileMode.CreateNew,FileAccess.Write)) {
    while(true) {
     int count=0,n;
     while(count<16 && (n=input.Read(block,count,16-count))>0)count+=n;
     if(count==0)break;
     transform.TransformBlock(counter,0,16,stream,0);
     for(int i=0;i<count;i++)block[i]^=stream[i];
     output.Write(block,0,count);
     for(int i=15;i>=0;i--){counter[i]++;if(counter[i]!=0)break;}
    }
   }
  }
 }
}
'@
  }
  [CoopLanCrypto]::Decrypt($encrypted,$temporary)
  if((Get-FileHash -LiteralPath $temporary).Hash -ine $script:CoopLanArchiveSha){throw 'LAN archive checksum mismatch / LAN-Archiv-Pruefsumme falsch.'}
  [IO.File]::Move($temporary,$output,$true)
  return $output
 }finally{foreach($path in @($encrypted,$temporary)){if(Test-Path -LiteralPath $path){Remove-Item -LiteralPath $path}}}
}
function Expand-CoopOriginalLanArchive {
 param([string]$Archive,[string]$Destination)
 if((Get-FileHash -LiteralPath $Archive).Hash -ine $script:CoopLanArchiveSha){throw 'Only the verified original7z archive is accepted. Extract other archives yourself / Nur das gepruefte Original7z ist erlaubt; andere Archive vorher entpacken.'}
 if(Test-Path -LiteralPath $Destination){throw 'Import destination already exists'}
 $tar=Join-Path $env:WINDIR 'System32\tar.exe'
 if(!(Test-Path -LiteralPath $tar)){throw 'Windows tar missing. Extract the LAN archive and select its folder / Windows tar fehlt; LAN-Archiv entpacken und Ordner auswaehlen.'}
 $names=@(& $tar -tf $Archive 2>&1)
 if($LASTEXITCODE -ne 0 -or $names.Count -gt 100){throw 'Original LAN archive listing failed'}
 foreach($name in $names){if([IO.Path]::IsPathRooted([string]$name) -or [string]$name -match '(^|[\\/])\.\.([\\/]|$)' -or [string]$name -match ':'){throw 'Unsafe LAN archive path'}}
 [void][IO.Directory]::CreateDirectory($Destination)
 & $tar -xf $Archive -C $Destination
 if($LASTEXITCODE -ne 0){throw 'LAN extraction failed / LAN-Entpacken fehlgeschlagen.'}
}
