# Windows PowerShell5.1 compatible. Portable per-user runtime, no admin/registry changes.
# Official ZIP method: https://learn.microsoft.com/powershell/scripting/install/install-powershell-on-windows
function Get-CoopPowerShellAsset {
 param([Parameter(Mandatory)]$Release)
 if($Release.draft -or $Release.prerelease -or [string]$Release.tag_name -notmatch '^v(7\.\d+\.\d+)$'){throw 'Invalid PowerShell release / Ungueltige PowerShell-Version.'}
 $version=$Matches[1];$name='PowerShell-'+$version+'-win-x64.zip'
 $assets=@($Release.assets|Where-Object {$_.name -ceq $name -and $_.state -eq 'uploaded'})
 if($assets.Count -ne 1){throw 'PowerShell asset missing / PowerShell-Paket fehlt.'}
 $asset=$assets[0];$url=[Uri]$asset.browser_download_url
 $expected='/PowerShell/PowerShell/releases/download/v'+$version+'/'+$name
 if($url.Scheme -cne 'https' -or $url.Host -ine 'github.com' -or [Uri]::UnescapeDataString($url.AbsolutePath) -cne $expected -or $url.Query -or $url.Fragment){throw 'Invalid PowerShell source / Ungueltige PowerShell-Quelle.'}
 if([string]$asset.digest -notmatch '^sha256:([0-9a-fA-F]{64})$' -or [long]$asset.size -le 0 -or [long]$asset.size -gt 262144000){throw 'PowerShell checksum/size missing / PowerShell-Pruefsumme oder Groesse ungueltig.'}
 [pscustomobject]@{Version=$version;Url=$url.AbsoluteUri;Sha256=([string]$asset.digest).Substring(7);Bytes=[long]$asset.size}
}

function Assert-CoopRuntimeArchive {
 param([Parameter(Mandatory)][string]$Zip,[Parameter(Mandatory)][string]$Destination)
 Add-Type -AssemblyName System.IO.Compression.FileSystem
 $prefix=[IO.Path]::GetFullPath($Destination).TrimEnd('\')+'\'
 $archive=[IO.Compression.ZipFile]::OpenRead($Zip)
 try{
  if($archive.Entries.Count -gt 10000){throw 'Runtime archive exceeds file bound'}
  $seen=New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
  $total=0L
  foreach($entry in $archive.Entries){
   $relative=$entry.FullName.Replace('/','\')
   if(!$relative -or [IO.Path]::IsPathRooted($relative) -or $relative.Contains(':') -or $relative -match '(^|\\)\.\.(\\|$)'){throw 'Runtime archive path escape'}
   $target=[IO.Path]::GetFullPath((Join-Path $Destination $relative))
   if(!$target.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase) -or !$seen.Add($target)){throw 'Runtime archive path collision'}
   if((($entry.ExternalAttributes -shr 16) -band 0xF000) -eq 0xA000 -or ($entry.ExternalAttributes -band 0x400)){throw 'Runtime archive link'}
   $total+=$entry.Length;if($total -gt 1073741824){throw 'Runtime archive exceeds size bound'}
  }
 }finally{$archive.Dispose()}
}

function Resolve-CoopPowerShell7 {
 param([string]$RuntimeRoot,[switch]$SkipInstalled)
 $candidates=New-Object 'System.Collections.Generic.List[string]'
 if(!$SkipInstalled -and $PSVersionTable.PSVersion.Major -ge 7){$candidates.Add((Join-Path $PSHOME 'pwsh.exe'))}
 $command=Get-Command pwsh.exe -ErrorAction SilentlyContinue
 if(!$SkipInstalled -and $command){$candidates.Add($command.Source)}
 if(!$SkipInstalled -and $env:ProgramFiles){$candidates.Add((Join-Path $env:ProgramFiles 'PowerShell\7\pwsh.exe'))}
 foreach($candidate in $candidates){
  if(Test-Path -LiteralPath $candidate -PathType Leaf){
   try{
    $version=& $candidate -NoProfile -Command '$PSVersionTable.PSVersion.Major' 2>$null
    if($LASTEXITCODE -eq 0 -and [string]$version -match '^\s*7\s*$'){return $candidate}
   }catch{}
  }
 }
 $root=if($RuntimeRoot){[IO.Path]::GetFullPath($RuntimeRoot)}else{Join-Path $env:LOCALAPPDATA 'TheRunStoryCoop\Runtime'}
 $pointer=Join-Path $root 'powershell-runtime.json'
 if(Test-Path -LiteralPath $pointer){
  try{
   $saved=Get-Content -LiteralPath $pointer -Raw|ConvertFrom-Json
   $candidate=[IO.Path]::GetFullPath([string]$saved.Path)
   if($candidate.StartsWith([IO.Path]::GetFullPath($root).TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase) -and (Test-Path -LiteralPath $candidate -PathType Leaf) -and (Get-FileHash -LiteralPath $candidate -Algorithm SHA256).Hash -ieq [string]$saved.Sha256){
    $version=& $candidate -NoProfile -Command '$PSVersionTable.PSVersion.Major' 2>$null
    if($LASTEXITCODE -eq 0 -and [string]$version -match '^\s*7\s*$'){return $candidate}
   }
  }catch{} # Rebuild a damaged private runtime instead of returning a broken pointer.
 }
 [Net.ServicePointManager]::SecurityProtocol=[Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
 $headers=@{'User-Agent'='TheRunStoryCoop-PowerShell';Accept='application/vnd.github+json'}
 $release=Invoke-RestMethod -Uri 'https://api.github.com/repos/PowerShell/PowerShell/releases/latest' -Headers $headers -TimeoutSec 20
 $asset=Get-CoopPowerShellAsset $release
 $directory=Join-Path $root ('PowerShell-'+$asset.Version+'-'+[Guid]::NewGuid().ToString('N'))
 [void][IO.Directory]::CreateDirectory($directory)
 $zip=Join-Path $directory 'runtime.zip';$unpacked=Join-Path $directory 'files'
 Write-Host 'Preparing PowerShell 7 / PowerShell 7 wird vorbereitet ...'
 Invoke-WebRequest -UseBasicParsing -Uri $asset.Url -OutFile $zip -Headers @{'User-Agent'='TheRunStoryCoop-PowerShell'} -TimeoutSec 180
 if((Get-Item -LiteralPath $zip).Length -ne $asset.Bytes -or (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash -ine $asset.Sha256){throw 'PowerShell checksum mismatch / PowerShell-Pruefsumme falsch.'}
 Assert-CoopRuntimeArchive -Zip $zip -Destination $unpacked
 [IO.Compression.ZipFile]::ExtractToDirectory($zip,$unpacked)
 $candidate=Join-Path $unpacked 'pwsh.exe'
 $signature=Get-AuthenticodeSignature -LiteralPath $candidate
 if($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch '(^|,\s*)O=Microsoft Corporation(,|$)'){throw 'Invalid Microsoft signature / Microsoft-Signatur ungueltig.'}
 $version=& $candidate -NoProfile -Command '$PSVersionTable.PSVersion.Major' 2>$null
 if($LASTEXITCODE -ne 0 -or [string]$version -notmatch '^\s*7\s*$'){throw 'PowerShell could not start / PowerShell konnte nicht starten.'}
 $saved=[ordered]@{Path=$candidate;Sha256=(Get-FileHash -LiteralPath $candidate -Algorithm SHA256).Hash;Version=$asset.Version;Source=$asset.Url}
 $temporary=Join-Path $root ([IO.Path]::GetRandomFileName())
 foreach($path in @($temporary,$pointer)){
  if([IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($path)) -ine [IO.Path]::GetFullPath($root).TrimEnd('\')){throw 'Runtime pointer path escape'}
 }
 $saved|ConvertTo-Json|Set-Content -LiteralPath $temporary -Encoding utf8
 Move-Item -LiteralPath $temporary -Destination $pointer -Force
 return $candidate
}
