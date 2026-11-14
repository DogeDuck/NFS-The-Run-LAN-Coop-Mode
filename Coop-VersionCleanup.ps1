# Verified retired packages only. No recursive delete, no game/save file deletion.
function Get-CoopCleanupVersion {
 param([string]$Text)
 if($Text -notmatch '^(\d+)\.(\d+)(?:\.(\d+))?(?:-[A-Za-z0-9._-]+)?$'){throw 'unknown package version'}
 $patch=if($Matches[3]){[int]$Matches[3]}else{0}
 return [Version]::new([int]$Matches[1],[int]$Matches[2],$patch)
}
function Get-CoopRetiredPackagePlan {
 param([Parameter(Mandatory)][string]$GameDirectory,[Parameter(Mandatory)][string]$ActivePackage)
 $game=[IO.Path]::GetFullPath($GameDirectory).TrimEnd('\')
 $active=[IO.Path]::GetFullPath($ActivePackage).TrimEnd('\')
 if([IO.Path]::GetDirectoryName($active) -ine $game){throw 'Active package must be a direct game-folder child / Aktives Paket muss direkt im Spielordner liegen.'}
 if(!(Test-Path -LiteralPath (Join-Path $active 'package-manifest.json') -PathType Leaf)){throw 'Active package missing / Aktives Paket fehlt.'}
 $activeManifest=Get-Content -LiteralPath (Join-Path $active 'package-manifest.json') -Raw|ConvertFrom-Json
 if([IO.Path]::GetFileName($active) -cne ('TheRun-Coop-v'+[string]$activeManifest.version)){throw 'Active package identity differs / Identitaet des aktiven Pakets weicht ab.'}
 $activeVersion=Get-CoopCleanupVersion ([string]$activeManifest.version)
 if($game -match '(?i)(^|\\)THERUNBACKUP(\\|$)'){throw 'Protected backup / Geschuetzte Sicherung.'}
 foreach($folder in @(Get-ChildItem -LiteralPath $game -Directory -Force)){
  if($folder.FullName -ieq $active -or $folder.Name -notmatch '^TheRun-Coop-v[A-Za-z0-9][A-Za-z0-9._-]*$'){continue}
  $row=[ordered]@{Path=$folder.FullName;Status='preserved';Reason='unverified';Files=@();Directories=@()}
  try{
   if($folder.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'link'}
   $manifestPath=Join-Path $folder.FullName 'package-manifest.json'
   $manifest=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
   if($folder.Name -cne ('TheRun-Coop-v'+[string]$manifest.version)){throw 'version/name mismatch'}
   if((Get-CoopCleanupVersion ([string]$manifest.version)) -gt $activeVersion){throw 'newer package version'}
   $allowed=New-Object 'System.Collections.Generic.Dictionary[string,string]' ([StringComparer]::OrdinalIgnoreCase)
   foreach($entry in @($manifest.files)){
    $name=[string]$entry.path;$hash=[string]$entry.sha256
    if(!$name -or $hash -notmatch '^[0-9a-fA-F]{64}$' -or [IO.Path]::IsPathRooted($name)){throw 'invalid manifest entry'}
    $target=[IO.Path]::GetFullPath((Join-Path $folder.FullName $name))
    if(!$target.StartsWith($folder.FullName+'\',[StringComparison]::OrdinalIgnoreCase) -or $target -ieq $manifestPath){throw 'path escape'}
    $allowed.Add($target,$hash)
   }
   if(!$allowed.Count){throw 'empty manifest'}
   $allowed.Add($manifestPath,(Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash)
   $queue=New-Object 'System.Collections.Generic.Queue[string]';$queue.Enqueue($folder.FullName)
   $files=New-Object 'System.Collections.Generic.List[object]';$dirs=New-Object 'System.Collections.Generic.List[string]'
   while($queue.Count){
    $directory=$queue.Dequeue();$dirs.Add($directory)
    foreach($item in @(Get-ChildItem -LiteralPath $directory -Force)){
     if($item.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'link inside package'}
     if($item.PSIsContainer){$queue.Enqueue($item.FullName);continue}
     if(!$allowed.ContainsKey($item.FullName)){throw 'personal/unlisted file'}
     $hash=(Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash
     if($hash -ine $allowed[$item.FullName]){throw 'modified file'}
     $files.Add([pscustomobject]@{Path=$item.FullName;Sha256=$hash})
    }
    if($files.Count+$dirs.Count -gt 10000){throw 'package exceeds bound'}
   }
   if($files.Count -ne $allowed.Count){throw 'missing package files'}
   $row.Status='eligible';$row.Reason='exact manifest';$row.Files=@($files.ToArray());$row.Directories=@($dirs.ToArray())
  }catch{$row.Reason=$_.Exception.Message}
  [pscustomobject]$row
 }
}

function Invoke-CoopRetiredPackageCleanup {
 param([Parameter(Mandatory)][string]$GameDirectory,[Parameter(Mandatory)][string]$ActivePackage,[switch]$Commit,[switch]$NewInstallationVerified)
 $plan=@(Get-CoopRetiredPackagePlan -GameDirectory $GameDirectory -ActivePackage $ActivePackage)
 if(!$Commit){return $plan}
 if(!$NewInstallationVerified){throw 'Verify the new installation first / Neue Installation zuerst pruefen.'}
 if(@(Get-Process -Name 'Need For Speed The Run','NFSTR_Server' -ErrorAction SilentlyContinue).Count){throw 'Close game/server first / Spiel und Server zuerst schliessen.'}
 foreach($row in $plan){
  if($row.Status -ne 'eligible'){$row;continue}
  # No recursive operations: only exact manifest files, then empty directories.
  foreach($file in $row.Files){
   if((Get-FileHash -LiteralPath $file.Path -Algorithm SHA256).Hash -ine $file.Sha256){throw 'Package changed during cleanup / Paket wurde zwischenzeitlich geaendert.'}
   Remove-Item -LiteralPath $file.Path -Force -ErrorAction Stop
  }
  foreach($directory in @($row.Directories|Sort-Object Length -Descending)){
   $item=Get-Item -LiteralPath $directory -Force
   if($item.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Directory changed into link / Ordner wurde zu Verknuepfung.'}
   if(@(Get-ChildItem -LiteralPath $directory -Force).Count){throw 'Directory no longer empty / Ordner nicht mehr leer.'}
   Remove-Item -LiteralPath $directory -Force -ErrorAction Stop
  }
  $row.Status='removed';$row
 }
}
