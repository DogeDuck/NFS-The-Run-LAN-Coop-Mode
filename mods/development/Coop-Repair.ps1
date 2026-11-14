#requires -Version 7.0
# Reconstruct known mod targets from verified package data / own install backups.
# Personal INIs, launcher data and game saves are never repair targets.
. (Join-Path $PSScriptRoot 'Coop-UserData.ps1')
. (Join-Path $PSScriptRoot 'Coop-Core.ps1')
function Resolve-CoopRepairChild {
 param([string]$Root,[string]$Relative)
 if(!$Relative -or [IO.Path]::IsPathRooted($Relative) -or $Relative.Contains(':') -or $Relative -match '(^|[\\/])\.\.([\\/]|$)'){throw 'Unsafe repair path / Unsicherer Reparaturpfad.'}
 $rootPath=[IO.Path]::GetFullPath($Root).TrimEnd('\');$path=[IO.Path]::GetFullPath((Join-Path $rootPath $Relative))
 if(!$path.StartsWith($rootPath+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Repair path outside folder / Reparaturpfad ausserhalb des Ordners.'}
 $cursor=$path
 while($cursor -and $cursor.Length -ge $rootPath.Length){if((Test-Path -LiteralPath $cursor) -and ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Repair links are unsupported / Reparatur ueber Verknuepfung nicht erlaubt.'};$cursor=[IO.Path]::GetDirectoryName($cursor)}
 return $path
}
function Assert-CoopRepairPackage {
 param([string]$PackageDirectory)
 $manifest=Read-CoopJsonObject (Join-Path $PackageDirectory 'package-manifest.json') 4MB
 if(@($manifest.files).Count -lt 3 -or @($manifest.files).Count -gt 10000){throw 'Incomplete package manifest / Unvollstaendiges Paketmanifest.'}
 $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
 foreach($row in $manifest.files){
  if(!$seen.Add([string]$row.path)){throw 'Duplicate package path / Doppelter Paketpfad.'}
  $path=Resolve-CoopRepairChild $PackageDirectory $row.path
  if(!(Test-Path -LiteralPath $path -PathType Leaf) -or (Get-Item -LiteralPath $path).Length -ne [long]$row.bytes -or (Get-CoopFileHash $path) -ine $row.sha256){throw ('Package damaged; download it again / Paket beschaedigt; erneut herunterladen: '+$row.path)}
 }
 return $manifest
}
function Find-CoopRepairBytes {
 param([string]$Relative,[string[]]$Hashes,[string]$GameDirectory,[string]$BackupRoot)
 $paths=@((Resolve-CoopRepairChild $GameDirectory $Relative))
 if(Test-Path -LiteralPath $BackupRoot -PathType Container){
  $parent=Get-Item -LiteralPath $BackupRoot -Force
  if($parent.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Backup links unsupported / Sicherungsverknuepfungen nicht erlaubt.'}
  foreach($folder in @(Get-ChildItem -LiteralPath $BackupRoot -Directory|Sort-Object LastWriteTime -Descending|Select-Object -First 24)){
   $paths+=Resolve-CoopRepairChild $folder.FullName $Relative
  }
 }
 foreach($path in $paths){if((Test-Path -LiteralPath $path -PathType Leaf) -and (Get-CoopFileHash $path) -in $Hashes){return ,([IO.File]::ReadAllBytes($path))}}
 return $null
}
function Get-CoopRepairPlan {
 param([Parameter(Mandatory)][string]$GameDirectory,[Parameter(Mandatory)][string]$PackageDirectory,[string]$BackupRoot=(Join-Path $env:LOCALAPPDATA 'TheRunStoryCoop\InstallBackups'))
 $game=[IO.Path]::GetFullPath($GameDirectory.Trim('"')).TrimEnd('\')
 if($game.Split('\') -contains 'THERUNBACKUP'){throw 'Protected backup / Geschuetzte Sicherung.'}
 $manifest=Assert-CoopRepairPackage $PackageDirectory
 $changes=[Collections.Generic.List[object]]::new();$blocked=[Collections.Generic.List[string]]::new()
 foreach($stem in 'client','server'){
  $default=Read-CoopJsonObject (Join-Path $PackageDirectory ('patches\'+$stem+'.json')) 16MB
  $relative=[string]$default.FileName
  if($relative -notin @('Need For Speed The Run.exe','NFSTR_Server.exe')){throw 'Unexpected native target / Unerwartete Spiel-Zieldatei.'}
  $target=Resolve-CoopRepairChild $game $relative;$expected=[string]$default.PatchedSha256
  if($expected -notmatch '^[a-f0-9A-F]{64}$' -or $expected -ine $manifest[($stem+'_sha256')]){throw 'Manifest/native patch disagree / Manifest und Spielpatch widersprechen sich.'}
  if((Test-Path -LiteralPath $target) -and (Get-CoopFileHash $target) -ieq $expected){continue}
  $bytes=$null
  foreach($path in @(Get-ChildItem -LiteralPath (Join-Path $PackageDirectory 'patches') -Filter ($stem+'*.json') -File)){
   $delta=Read-CoopJsonObject $path.FullName 16MB
   if($delta.FileName -cne $relative -or $delta.PatchedSha256 -ine $expected){continue}
   $source=Find-CoopRepairBytes $relative @([string]$delta.OriginalSha256,[string]$delta.PatchedSha256) $game $BackupRoot
   if($null -ne $source){$bytes=New-CoopPatchedBytes $source $delta;break}
  }
  if($null -eq $bytes){$blocked.Add($relative);continue}
  $changes.Add([pscustomobject]@{RelativePath=$relative;Path=$target;Bytes=$bytes;AfterSha256=$expected;BeforeSha256=$(if(Test-Path -LiteralPath $target){Get-CoopFileHash $target}else{$null})})
 }
 $support=Get-Content -LiteralPath (Join-Path $PackageDirectory 'patches\support-files.json') -Raw|ConvertFrom-Json
 foreach($row in $support){
  if([IO.Path]::GetExtension([string]$row.RelativePath) -ieq '.ini'){continue}
  $target=Resolve-CoopRepairChild $game $row.RelativePath
  if((Test-Path -LiteralPath $target) -and (Get-CoopFileHash $target) -ieq $row.Sha256){continue}
  $bytes=Find-CoopRepairBytes $row.RelativePath @([string]$row.Sha256) $game $BackupRoot
  if($null -eq $bytes){$blocked.Add([string]$row.RelativePath);continue}
  $changes.Add([pscustomobject]@{RelativePath=$row.RelativePath;Path=$target;Bytes=$bytes;AfterSha256=$row.Sha256;BeforeSha256=$(if(Test-Path -LiteralPath $target){Get-CoopFileHash $target}else{$null})})
 }
 # The bundled Definitive Edition ASI has a verified package source. Its personal
 # INI and asset archives remain outside repair scope.
 $de=@($manifest.files|Where-Object {$_.path -ieq 'addons/NFSTR_DefinitiveEdition.asi'})
 if($de.Count -eq 1){
  $relative='Scripts\NFSTR_DefinitiveEdition.asi';$target=Resolve-CoopRepairChild $game $relative
  if(!(Test-Path -LiteralPath $target) -or (Get-CoopFileHash $target) -ine $de[0].sha256){
   $source=Resolve-CoopRepairChild $PackageDirectory $de[0].path
   $changes.Add([pscustomobject]@{RelativePath=$relative;Path=$target;Bytes=[IO.File]::ReadAllBytes($source);AfterSha256=$de[0].sha256;BeforeSha256=$(if(Test-Path -LiteralPath $target){Get-CoopFileHash $target}else{$null})})
  }
 }
 return [pscustomobject]@{Version=$manifest.version;GameDirectory=$game;Changes=$changes;Blocked=@($blocked);Ready=($blocked.Count -eq 0);SaveRestore=$false;PersonalIniPreserved=$true}
}
function Invoke-CoopRepairPlan {
 param([Parameter(Mandatory)]$Plan,[string]$BackupDirectory=(Join-Path $env:LOCALAPPDATA ('TheRunStoryCoop\RepairBackups\'+[Guid]::NewGuid().ToString('N'))),[scriptblock]$BeforeReplace)
 Assert-CoopClosed
 if(!$Plan.Ready){throw ('Verified repair source missing; reinstall from your base package / Gepruefte Reparaturquelle fehlt; eigenes Grundpaket benoetigt: '+($Plan.Blocked -join ', '))}
 $done=[Collections.Generic.List[object]]::new()
 try{
  foreach($row in $Plan.Changes){
   Assert-CoopClosed
   if((Resolve-CoopRepairChild $Plan.GameDirectory $row.RelativePath) -ine $row.Path){throw 'Repair target changed / Reparaturziel veraendert.'}
   $current=if(Test-Path -LiteralPath $row.Path){Get-CoopFileHash $row.Path}else{$null}
   if($current -cne $row.BeforeSha256){throw 'File changed during repair / Datei waehrend Reparatur veraendert.'}
   if((Get-CoopHash $row.Bytes) -ine $row.AfterSha256){throw 'Repair checksum mismatch / Reparaturpruefsumme stimmt nicht.'}
   $backup=Resolve-CoopRepairChild $BackupDirectory $row.RelativePath;[void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($backup))
   if($null -ne $current){Copy-Item -LiteralPath $row.Path -Destination $backup -ErrorAction Stop}
   if($BeforeReplace){& $BeforeReplace $row}
   $temporary=$row.Path+'.repair-'+[Guid]::NewGuid().ToString('N')
   try{[void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($row.Path));[IO.File]::WriteAllBytes($temporary,$row.Bytes);[IO.File]::Move($temporary,$row.Path,$true)}finally{if(Test-Path -LiteralPath $temporary){Remove-Item -LiteralPath $temporary}}
   $done.Add([pscustomobject]@{Row=$row;Backup=$backup})
  }
 }catch{
  $failure=$_
  for($i=$done.Count-1;$i -ge 0;$i--){$item=$done[$i];if((Test-Path -LiteralPath $item.Row.Path) -and (Get-CoopFileHash $item.Row.Path) -ieq $item.Row.AfterSha256){if(Test-Path -LiteralPath $item.Backup){Copy-Item -LiteralPath $item.Backup -Destination $item.Row.Path -Force}else{Remove-Item -LiteralPath $item.Row.Path}}}
  throw $failure
 }
 return [ordered]@{Status='repaired';Files=@($done|ForEach-Object {$_.Row.RelativePath});BackupDirectory=$(if($done.Count){$BackupDirectory}else{$null});SaveRestore=$false;PersonalIniPreserved=$true}
}
