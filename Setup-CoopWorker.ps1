param([Parameter(Mandatory)][string]$RequestPath)
$ErrorActionPreference='Stop'
$request=Get-Content -LiteralPath $RequestPath -Raw -Encoding UTF8|ConvertFrom-Json
$result=[string]$request.ResultPath
try{
 if($PSVersionTable.PSVersion.Major -lt 7){
  . (Join-Path $PSScriptRoot 'Coop-PowerShellRuntime.ps1')
  $runtime=Resolve-CoopPowerShell7
  & $runtime -NoProfile -ExecutionPolicy Bypass -File $PSCommandPath -RequestPath $RequestPath
  exit $LASTEXITCODE
 }
 $PSStyle.OutputRendering='PlainText'
 . (Join-Path $PSScriptRoot 'Coop-SetupCore.ps1')
 . (Join-Path $PSScriptRoot 'Coop-LanDownload.ps1')
 . (Join-Path $PSScriptRoot 'Coop-UpdateStage.ps1')
 . (Join-Path $PSScriptRoot 'Coop-Repair.ps1')
 Write-CoopSetupResult $result @{Status='working';Phase='checking'}
 if(@(Get-Process -Name 'Need For Speed The Run','NFSTR_Server' -ErrorAction SilentlyContinue).Count){throw 'Close the game and server first / Spiel und Server zuerst schliessen.'}
 $game=[IO.Path]::GetFullPath([string]$request.GameDirectory).TrimEnd('\')
 if($game -match '(?i)(^|\\)THERUNBACKUP(\\|$)' -or !(Test-Path -LiteralPath (Join-Path $game 'Need For Speed The Run.exe') -PathType Leaf)){throw 'Select the game folder containing Need For Speed The Run.exe / Spielordner mit der Spiel-EXE auswaehlen.'}
 $manifest=Assert-CoopRepairPackage $PSScriptRoot
 # Always reconstruct managed files from the verified original LAN base.
 $missing=@(Get-CoopSetupBaseRequirements $PSScriptRoot)
 $base=''
 if($missing.Count){
  foreach($row in $missing){
   if($row.RelativePath -in @('Need For Speed The Run.exe','NFSTR_Server.exe')){
    $stem=if($row.RelativePath -eq 'NFSTR_Server.exe'){'server'}else{'client'}
    $delta=Get-Content -LiteralPath (Join-Path $PSScriptRoot ('patches/'+$stem+'.json')) -Raw|ConvertFrom-Json
    $row.Hashes=@($delta.OriginalSha256)
   }
  }
  if(!$request.LanSource -and $request.DownloadLan){
   Write-CoopSetupResult $result @{Status='working';Phase='downloading'}
   $request.LanSource=Get-CoopOriginalLanArchive (Join-Path $env:LOCALAPPDATA 'TheRunStoryCoop\LANBase')
  }
  if(!$request.LanSource){Write-CoopSetupResult $result @{Status='needs-lan';Files=@($missing|ForEach-Object RelativePath)};exit 2}
  Write-CoopSetupResult $result @{Status='working';Phase='importing'}
  $base=[IO.Path]::GetFullPath([string]$request.LanSource)
  if(Test-Path -LiteralPath $base -PathType Leaf){
   $extension=[IO.Path]::GetExtension($base)
   if($extension -notin @('.zip','.7z')){throw 'Select a LAN ZIP/7z archive or extracted folder / LAN-ZIP/7z oder entpackten Ordner auswaehlen.'}
   $unpacked=Join-Path ([IO.Path]::GetDirectoryName($result)) ('lan-import-'+[Guid]::NewGuid().ToString('N'))
   if($extension -ieq '.7z'){Expand-CoopOriginalLanArchive $base $unpacked}else{Expand-CoopSetupArchive $base $unpacked};$base=$unpacked
  }
  $base=Find-CoopSetupBaseFolder $base $missing
 }
 $published=Publish-CoopUpdatePackage -GameDirectory $game -SourcePackage $PSScriptRoot -Version $manifest.version -CurrentPackageDirectory (Join-Path ([IO.Path]::GetDirectoryName($result)) 'not-active') -VerifyPackage {param($directory) [void](Assert-CoopRepairPackage $directory)}
 $package=$published.PackageDirectory
 $argsList=@('-NoProfile','-File',(Join-Path $package 'Install-Coop.ps1'),'-GameDirectory',$game,'-NonInteractive','-FreshBase')
 if($base){$argsList+=@('-LanPackageDirectory',$base)}
 $output=& (Join-Path $PSHOME 'pwsh.exe') @argsList -CheckOnly 2>&1
 $plain=($output -join [Environment]::NewLine) -replace '\x1b\[[0-9;]*[A-Za-z]',''
 [IO.File]::WriteAllText((Join-Path ([IO.Path]::GetDirectoryName($result)) 'preflight.txt'),$plain)
 if($LASTEXITCODE -ne 0){throw $plain}
 Write-CoopSetupResult $result @{Status='working';Phase='backup'}
 $saveBackup=Backup-CoopSetupSaves -BackupDirectory (Join-Path ([IO.Path]::GetDirectoryName($result)) 'SaveBeforeSetup')
 Write-CoopSetupResult $result @{Status='working';Phase='installing'}
 $output=& (Join-Path $PSHOME 'pwsh.exe') @argsList 2>&1
 $code=$LASTEXITCODE;$plain=($output -join [Environment]::NewLine) -replace '\x1b\[[0-9;]*[A-Za-z]',''
 [IO.File]::WriteAllText((Join-Path ([IO.Path]::GetDirectoryName($result)) 'install.txt'),$plain)
 if($code -ne 0){throw $plain}
 foreach($file in $saveBackup.Files){if(!(Test-Path -LiteralPath $file.Path) -or (Get-FileHash -LiteralPath $file.Path).Hash -ne $file.Sha256){throw 'Save changed; backup retained. No save restored / Spielstand geaendert; Sicherung erhalten, nichts zurueckgespielt.'}}
 if($request.Language -in @('de','en')){. (Join-Path $PSScriptRoot 'Coop-Language.ps1');Save-CoopLanguage ([string]$request.Language)}
 if($request.DesktopShortcut){
  $shell=New-Object -ComObject WScript.Shell
  $link=$shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'The Run Co-op.lnk'))
  $link.TargetPath=Join-Path $env:WINDIR 'System32\wscript.exe';$link.Arguments='"'+(Join-Path $package 'Launch-Coop.vbs')+'"';$link.WorkingDirectory=$package;$link.Description='The Run Co-op';$link.Save()
 }
 Write-CoopSetupResult $result @{Status='installed';Version=$manifest.version;PackageDirectory=$package;SavedFiles=$saveBackup.Count;BackupDirectory=[IO.Path]::GetDirectoryName($result);SaveRestore=$false}
}catch{
 $message=$_.Exception.Message -replace '\x1b\[[0-9;]*[A-Za-z]',''
 $data=@{Status='failed';Error=$message}
 $parent=[IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($result));[void][IO.Directory]::CreateDirectory($parent)
 [IO.File]::WriteAllText($result,($data|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
 exit 1
}
