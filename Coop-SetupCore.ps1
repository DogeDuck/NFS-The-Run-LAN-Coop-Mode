# Setup helpers. PS7 for execution, Windows PowerShell5.1 for presentation/bootstrap.
function Test-CoopSetupFilesystemLink {
 param([Parameter(Mandatory)]$Item)
 # Cloud Files placeholders also have ReparsePoint. They are not directory
 # junctions/symlinks; normal Copy-Item/ReadAllBytes hydrates and verifies them.
 return ($Item.LinkType -in @('SymbolicLink','Junction') -or ![string]::IsNullOrEmpty([string]$Item.LinkTarget))
}
function Write-CoopSetupResult {
 param([string]$Path,$Value)
 $parent=[IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($Path))
 [void][IO.Directory]::CreateDirectory($parent)
 $temp=Join-Path $parent ([IO.Path]::GetRandomFileName())
 try{[IO.File]::WriteAllText($temp,($Value|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false));[IO.File]::Move($temp,$Path,$true)}
 finally{if(Test-Path -LiteralPath $temp){Remove-Item -LiteralPath $temp}}
}
function Get-CoopSetupBaseRequirements {
 param([string]$PackageDirectory)
 $required=@()
 foreach($name in 'client','server'){
  $patches=@(Get-ChildItem -LiteralPath (Join-Path $PackageDirectory 'patches') -Filter ($name+'*.json')|ForEach-Object{Get-Content -LiteralPath $_.FullName -Raw|ConvertFrom-Json})
  $required+= [pscustomobject]@{RelativePath=[string]$patches[0].FileName;Hashes=@($patches|ForEach-Object{$_.OriginalSha256;$_.PatchedSha256}|Select-Object -Unique)}
 }
 foreach($row in @(Get-Content -LiteralPath (Join-Path $PackageDirectory 'patches/support-files.json') -Raw|ConvertFrom-Json)){
  $required+= [pscustomobject]@{RelativePath=[string]$row.RelativePath;Hashes=@([string]$row.Sha256)}
 }
 return $required
}
function Get-CoopSetupMissingFiles {
 param([string]$GameDirectory,[string]$PackageDirectory)
 foreach($row in @(Get-CoopSetupBaseRequirements $PackageDirectory)){
  $path=Join-Path $GameDirectory $row.RelativePath
  if(!(Test-Path -LiteralPath $path -PathType Leaf) -or (Get-FileHash -LiteralPath $path).Hash -notin $row.Hashes){$row}
 }
}
function Expand-CoopSetupArchive {
 param([string]$Archive,[string]$Destination)
 Add-Type -AssemblyName System.IO.Compression.FileSystem
 if(Test-Path -LiteralPath $Destination){throw 'Import destination already exists / Importziel existiert bereits.'}
 $prefix=[IO.Path]::GetFullPath($Destination).TrimEnd('\')+'\'
 $zip=[IO.Compression.ZipFile]::OpenRead($Archive)
 try{
  if($zip.Entries.Count -gt 12000){throw 'Archive has too many entries / Zu viele Archiveintraege.'}
  $total=0L;$seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
  foreach($item in $zip.Entries){
   $name=$item.FullName.Replace('/','\')
   if(!$name -or [IO.Path]::IsPathRooted($name) -or $name.Contains(':') -or $name -match '(^|\\)\.\.([\\/]|$)'){throw 'Unsafe archive path / Unsicherer Archivpfad.'}
   $target=[IO.Path]::GetFullPath((Join-Path $Destination $name))
   if(!$target.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase) -or !$seen.Add($target)){throw 'Duplicate or escaping archive path / Doppelter oder unsicherer Archivpfad.'}
   if((($item.ExternalAttributes -shr 16) -band 0xF000) -eq 0xA000 -or ($item.ExternalAttributes -band 0x400)){throw 'Archive links unsupported / Archivverknuepfungen nicht erlaubt.'}
   $total+=$item.Length;if($total -gt 2147483648){throw 'Archive exceeds2GB / Archiv groesser als2GB.'}
  }
 }finally{$zip.Dispose()}
 [void][IO.Directory]::CreateDirectory($Destination)
 [IO.Compression.ZipFile]::ExtractToDirectory($Archive,$Destination)
}
function Find-CoopSetupBaseFolder {
 param([string]$Root,[object[]]$Requirements)
 $rootPath=[IO.Path]::GetFullPath($Root).TrimEnd('\')
 if(!(Test-Path -LiteralPath $rootPath -PathType Container)){throw 'Select an extracted LAN folder or ZIP / LAN-Ordner oder ZIP auswaehlen.'}
 $queue=[Collections.Generic.Queue[object]]::new();$queue.Enqueue(@($rootPath,0));$seen=0
 while($queue.Count){
  $entry=$queue.Dequeue();$directory=[string]$entry[0];$depth=[int]$entry[1]
  $info=Get-Item -LiteralPath $directory -Force
  if(Test-CoopSetupFilesystemLink $info){throw 'Import links unsupported / Importverknuepfungen nicht erlaubt.'}
  $ok=$true
  foreach($row in $Requirements){
   $path=[IO.Path]::GetFullPath((Join-Path $directory $row.RelativePath))
   if(!$path.StartsWith($directory+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid requirement path'}
   $cursor=$path
   while($cursor -and $cursor.Length -ge $directory.Length){if((Test-Path -LiteralPath $cursor) -and (Test-CoopSetupFilesystemLink (Get-Item -LiteralPath $cursor -Force))){throw 'Import links unsupported'};$cursor=[IO.Path]::GetDirectoryName($cursor)}
   if(!(Test-Path -LiteralPath $path -PathType Leaf) -or (Get-FileHash -LiteralPath $path).Hash -notin $row.Hashes){$ok=$false;break}
  }
  if($ok){return $directory}
  if($depth -lt 6){foreach($child in @(Get-ChildItem -LiteralPath $directory -Directory -Force)){$seen++;if($seen -gt 4000){throw 'Import folder too large / Importordner zu gross.'};$queue.Enqueue(@($child.FullName,$depth+1))}}
 }
 throw ('Matching LAN files not found / Passende LAN-Dateien nicht gefunden: '+(($Requirements|ForEach-Object RelativePath) -join ', '))
}
function Backup-CoopSetupSaves {
 param([string]$SaveDirectory=(Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'NFSTR'),[Parameter(Mandatory)][string]$BackupDirectory)
 $files=@();if(Test-Path -LiteralPath $SaveDirectory){
  $source=[IO.Path]::GetFullPath($SaveDirectory).TrimEnd('\')
  $target=[IO.Path]::GetFullPath($BackupDirectory).TrimEnd('\')
  if($target -ieq $source -or $target.StartsWith($source+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Save backup must be outside saves'}
  if(Test-Path -LiteralPath $target){throw 'Save backup destination exists'}
  $pending=[Collections.Generic.Queue[string]]::new();$pending.Enqueue($source);$entries=[Collections.Generic.List[object]]::new()
  $visited=0
  while($pending.Count){$directory=$pending.Dequeue();$visited++;if($visited -gt 10000){throw 'Save backup folder bound exceeded'};foreach($item in @(Get-ChildItem -LiteralPath $directory -Force)){
   if(Test-CoopSetupFilesystemLink $item){throw 'Save backup links unsupported'}
   if($item.PSIsContainer){$pending.Enqueue($item.FullName)}else{$entries.Add($item)}
   if($entries.Count+$pending.Count -gt 10000){throw 'Save backup exceeds bound'}
  }}
  foreach($file in $entries){$relative=$file.FullName.Substring($source.Length+1);$copy=Join-Path $target $relative;[void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($copy));Copy-Item -LiteralPath $file.FullName -Destination $copy -ErrorAction Stop
   $hash=(Get-FileHash -LiteralPath $file.FullName).Hash;if((Get-FileHash -LiteralPath $copy).Hash -ne $hash){throw 'Save backup verification failed'}
   $files+=@{Path=$file.FullName;Sha256=$hash}
  }
 }
 [pscustomobject]@{Directory=$BackupDirectory;Files=$files;Count=$files.Count;Restore=$false}
}
