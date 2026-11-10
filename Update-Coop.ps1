#requires -Version 7.0
param([switch]$CheckOnly,[switch]$Install,[string]$GameDirectory,[string]$CurrentPackageDirectory=$PSScriptRoot,[string]$ResultPath)
$ErrorActionPreference='Stop'

function Save-UpdateResult($Value){
    $json=$Value|ConvertTo-Json -Depth 8
    if($ResultPath){
        $parent=Split-Path -Parent ([IO.Path]::GetFullPath($ResultPath));[void][IO.Directory]::CreateDirectory($parent)
        $temp=Join-Path $parent ([IO.Path]::GetRandomFileName())
        [IO.File]::WriteAllText($temp,$json,[Text.UTF8Encoding]::new($false))
        [IO.File]::Move($temp,[IO.Path]::GetFullPath($ResultPath),$true)
    }
    Write-Output $json
}
function Get-ReleaseNumber([string]$Text){
    if($Text -notmatch '^v?(\d+)\.(\d+)(?:\.(\d+))?(?:-[A-Za-z0-9.-]+)?$'){throw 'Unrecognized release version.'}
    $patch=if($Matches[3]){[int]$Matches[3]}else{0}
    return [Version]::new([int]$Matches[1],[int]$Matches[2],$patch)
}
function Assert-UpdateGameClosed{
    if(@(Get-Process -Name 'Need For Speed The Run','NFSTR_Server' -ErrorAction SilentlyContinue).Count){throw 'UPDATE_GAME_RUNNING'}
}
function Resolve-UpdateChild([string]$Root,[string]$Relative){
    if(!$Relative -or [IO.Path]::IsPathRooted($Relative) -or $Relative.Contains(':') -or $Relative -match '(^|[\\/])\.\.([\\/]|$)'){throw 'Unsafe package path.'}
    $prefix=[IO.Path]::GetFullPath($Root).TrimEnd('\','/')+[IO.Path]::DirectorySeparatorChar
    $target=[IO.Path]::GetFullPath((Join-Path $Root $Relative))
    if(!$target.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)){throw 'Package path leaves its directory.'}
    return $target
}
function Assert-UpdatePackage([string]$Directory,[string]$Version){
    $manifestPath=Join-Path $Directory 'package-manifest.json'
    $manifest=Get-Content -LiteralPath $manifestPath -Raw -Encoding utf8|ConvertFrom-Json
    if([string]$manifest.version -ne $Version){throw 'Release and package versions differ.'}
    $seen=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    [void]$seen.Add('package-manifest.json')
    foreach($item in $manifest.files){
        $relative=([string]$item.path).Replace('/','\')
        if(!$seen.Add($relative)){throw 'Duplicate package entry.'}
        $path=Resolve-UpdateChild $Directory $relative
        if(!(Test-Path -LiteralPath $path -PathType Leaf) -or (Get-Item -LiteralPath $path).Length -ne [long]$item.bytes -or (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne [string]$item.sha256){throw ('Package checksum mismatch: '+$relative)}
    }
    foreach($path in Get-ChildItem -LiteralPath $Directory -Recurse -File){
        $relative=[IO.Path]::GetRelativePath($Directory,$path.FullName)
        if(!$seen.Contains($relative)){throw ('Unlisted package file: '+$relative)}
        if($path.Extension -in @('.exe','.dll','.ebx','.sb','.toc','.dmp')){throw 'Package contains a full game/runtime binary.'}
    }
    foreach($name in 'Install-Coop.ps1','Connect-Coop.ps1','Coop-Core.ps1'){
        if(!(Test-Path -LiteralPath (Join-Path $Directory $name) -PathType Leaf)){throw ('Missing update entrypoint: '+$name)}
    }
}

if($MyInvocation.InvocationName -eq '.'){return}

try{
    $currentManifest=Get-Content -LiteralPath (Join-Path $CurrentPackageDirectory 'package-manifest.json') -Raw -Encoding utf8|ConvertFrom-Json
    $current=[string]$currentManifest.version;$number=Get-ReleaseNumber $current
    # This project publishes TEST prereleases. /latest would omit all of them.
    # Accept published TEST releases, never drafts, DEV/GAS/ALL/CANDIDATE builds.
    $headers=@{'User-Agent'='TheRunStoryCoop-Updater';Accept='application/vnd.github+json';'X-GitHub-Api-Version'='2026-03-10'}
    # Invoke-RestMethod emits the JSON array as one pipeline object. Wrapping
    # the call in @() creates a nested array, so .draft becomes an array too.
    $releases=Invoke-RestMethod -Uri 'https://api.github.com/repos/DogeDuck/NFS-The-Run-LAN-Coop-Mode/releases?per_page=30' -Headers $headers -TimeoutSec 12
    $choices=@(foreach($release in $releases){
        if($release.draft -or [string]$release.tag_name -notmatch '^v\d+\.\d+(?:\.\d+)?-TEST$'){continue}
        $version=([string]$release.tag_name).Substring(1)
        $assetName='TheRun-Coop-v'+$version+'.zip'
        $assets=@($release.assets|Where-Object {$_.name -eq $assetName -and $_.state -eq 'uploaded'})
        if($assets.Count -ne 1){continue}
        $asset=$assets[0];$uri=[Uri]$asset.browser_download_url
        $expected='/DogeDuck/NFS-The-Run-LAN-Coop-Mode/releases/download/'+[string]$release.tag_name+'/'+$assetName
        if($uri.Scheme -ne 'https' -or $uri.Host -ne 'github.com' -or [Uri]::UnescapeDataString($uri.AbsolutePath) -cne $expected){continue}
        if([string]$asset.digest -notmatch '^sha256:[0-9a-fA-F]{64}$' -or [long]$asset.size -gt 209715200){continue}
        [pscustomobject]@{Version=$version;Number=(Get-ReleaseNumber $version);Url=$uri.AbsoluteUri;Sha256=([string]$asset.digest).Substring(7);Bytes=[long]$asset.size;ReleaseUrl=[string]$release.html_url}
    })
    $latest=$choices|Sort-Object Number -Descending|Select-Object -First 1
    if(!$latest -or $latest.Number -le $number){Save-UpdateResult @{Status='current';CurrentVersion=$current};return}
    if(!$Install -or $CheckOnly){Save-UpdateResult @{Status='available';CurrentVersion=$current;Version=$latest.Version;ReleaseUrl=$latest.ReleaseUrl};return}
    Assert-UpdateGameClosed
    if(!$GameDirectory){throw 'UPDATE_MISSING_GAME'}
    $game=[IO.Path]::GetFullPath($GameDirectory.Trim('"')).TrimEnd('\')
    if($game.Split('\') -contains 'THERUNBACKUP' -or !(Test-Path -LiteralPath (Join-Path $game 'Need For Speed The Run.exe') -PathType Leaf)){throw 'UPDATE_MISSING_GAME'}
    $updates=Join-Path $env:LOCALAPPDATA 'TheRunStoryCoop\Updates'
    $stage=Join-Path $updates ([Guid]::NewGuid().ToString('N'));[void][IO.Directory]::CreateDirectory($stage)
    $zip=Join-Path $stage 'package.zip'
    Invoke-WebRequest -Uri $latest.Url -OutFile $zip -Headers @{'User-Agent'='TheRunStoryCoop-Updater'} -TimeoutSec 120
    if((Get-Item -LiteralPath $zip).Length -ne $latest.Bytes -or (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash -ne $latest.Sha256){throw 'Release download checksum mismatch.'}
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $extract=Join-Path $stage 'unpacked';[void][IO.Directory]::CreateDirectory($extract)
    $archive=[IO.Compression.ZipFile]::OpenRead($zip)
    try{
        if($archive.Entries.Count -gt 5000){throw 'Too many package files.'}
        $total=0L;$entries=[Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        foreach($entry in $archive.Entries){
            $relative=$entry.FullName.Replace('/','\');$target=Resolve-UpdateChild $extract $relative
            if(!$entries.Add($target)){throw 'Duplicate archive path.'}
            $total+=$entry.Length;if($total -gt 419430400){throw 'Unpacked package is too large.'}
            if((($entry.ExternalAttributes -shr 16) -band 0xF000) -eq 0xA000){throw 'Archive symlinks are unsupported.'}
        }
    }finally{$archive.Dispose()}
    [IO.Compression.ZipFile]::ExtractToDirectory($zip,$extract)
    $folder='TheRun-Coop-v'+$latest.Version
    $package=Resolve-UpdateChild $extract $folder
    Assert-UpdatePackage $package $latest.Version
    $target=Resolve-UpdateChild $game $folder
    if(Test-Path -LiteralPath $target){Assert-UpdatePackage $target $latest.Version}else{Copy-Item -LiteralPath $package -Destination $target -Recurse}
    Assert-UpdateGameClosed
    # The existing installer validates native deltas/support files before writing
    # and backs up every changed mod file. Never call a save restore here.
    $pwsh=Join-Path $PSHOME 'pwsh.exe'
    $preflight=& $pwsh -NoProfile -File (Join-Path $target 'Install-Coop.ps1') -GameDirectory $game -CheckOnly 2>&1
    if($LASTEXITCODE -ne 0){throw ('Installer preflight failed: '+($preflight -join ' '))}
    $backup=Join-Path $stage 'personal-settings-before';[void][IO.Directory]::CreateDirectory($backup)
    $state=Join-Path $env:LOCALAPPDATA 'TheRunStoryCoop'
    foreach($name in 'launcher.json','language.json','car-preferences.json','settings.json'){
        $path=Join-Path $state $name;if(Test-Path -LiteralPath $path -PathType Leaf){Copy-Item -LiteralPath $path -Destination (Join-Path $backup $name)}
    }
    Assert-UpdateGameClosed
    $log=& $pwsh -NoProfile -File (Join-Path $target 'Install-Coop.ps1') -GameDirectory $game 2>&1
    $log|Set-Content -LiteralPath (Join-Path $stage 'installer.log') -Encoding utf8
    if($LASTEXITCODE -ne 0){throw ('Installer failed; backups retained: '+$stage)}
    Save-UpdateResult @{Status='installed';Version=$latest.Version;PackageDirectory=$target;BackupDirectory=$stage;SaveRestore=$false}
}catch{
    $message=$_.Exception.Message
    $status=if($message -eq 'UPDATE_GAME_RUNNING'){'game-running'}elseif($message -eq 'UPDATE_MISSING_GAME'){'missing-game'}elseif($Install){'failed'}else{'offline'}
    Save-UpdateResult @{Status=$status;Error=$message}
    if($Install){exit 1}
}
