# Stage and verify a complete package before replacing its directory. No deletion.
function Publish-CoopUpdatePackage {
 param([Parameter(Mandatory)][string]$GameDirectory,[Parameter(Mandatory)][string]$SourcePackage,[Parameter(Mandatory)][string]$Version,[Parameter(Mandatory)][string]$CurrentPackageDirectory,[Parameter(Mandatory)][scriptblock]$VerifyPackage)
 if($Version -notmatch '^\d+\.\d+(?:\.\d+)?-TEST$'){throw 'Invalid published version / Ungueltige Releaseversion.'}
 $game=[IO.Path]::GetFullPath($GameDirectory).TrimEnd('\')
 $source=[IO.Path]::GetFullPath($SourcePackage).TrimEnd('\')
 $current=[IO.Path]::GetFullPath($CurrentPackageDirectory).TrimEnd('\')
 $target=[IO.Path]::GetFullPath((Join-Path $game ('TheRun-Coop-v'+$Version)))
 if($target -ieq $current -or $game.StartsWith($source+'\',[StringComparison]::OrdinalIgnoreCase) -or $game -ieq $source){throw 'Unsafe update layout / Unsichere Updatepfade.'}
 if($game -match '(?i)(^|\\)THERUNBACKUP(\\|$)'){throw 'Protected backup / Geschuetzte Sicherung.'}
 & $VerifyPackage $source
 $reuse=$false
 if(Test-Path -LiteralPath $target){
  $item=Get-Item -LiteralPath $target -Force
  if(!$item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Target is a link/file / Ziel ist eine Verknuepfung oder Datei.'}
  try{& $VerifyPackage $target;$reuse=$true}catch{}
 }
 if($reuse){return [pscustomobject]@{PackageDirectory=$target;Reused=$true;QuarantinedDirectory=$null}}
 $id=[Guid]::NewGuid().ToString('N')
 $working=[IO.Path]::GetFullPath((Join-Path $game ('TheRun-UpdateWork-'+$id)))
 $quarantine=[IO.Path]::GetFullPath((Join-Path $game ('TheRun-Incomplete-'+$id)))
 # Verify the resolved absolute targets before any directory move.
 foreach($path in @($target,$working,$quarantine)){
  if([IO.Path]::GetDirectoryName($path) -ine $game){throw 'Update path escapes game folder / Updatepfad ausserhalb des Spielordners.'}
 }
 Copy-Item -LiteralPath $source -Destination $working -Recurse -ErrorAction Stop
 & $VerifyPackage $working
 if(@(Get-Process -Name 'Need For Speed The Run','NFSTR_Server' -ErrorAction SilentlyContinue).Count){throw 'Close game/server first / Spiel und Server zuerst schliessen.'}
 $moved=$false
 try{
  if(Test-Path -LiteralPath $target){Move-Item -LiteralPath $target -Destination $quarantine -ErrorAction Stop;$moved=$true}
  Move-Item -LiteralPath $working -Destination $target -ErrorAction Stop
  & $VerifyPackage $target
 }catch{
  # Existing private content was preserved, never recursively deleted.
  if($moved -and !(Test-Path -LiteralPath $target)){Move-Item -LiteralPath $quarantine -Destination $target -ErrorAction Stop}
  throw
 }
 [pscustomobject]@{PackageDirectory=$target;Reused=$false;QuarantinedDirectory=$(if($moved){$quarantine}else{$null})}
}
