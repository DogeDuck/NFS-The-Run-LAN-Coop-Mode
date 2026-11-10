#requires -Version 7.0
param([ValidateSet('Host','Guest')][string]$Role='Host',[string]$GameDirectory,[string]$HostAddress,[string]$Nickname,[string]$StartCarId,[ValidateRange(1,4)][int]$MaxPlayers=2,[ValidateRange(0,3)][int]$Difficulty=1,[switch]$ShowServerWindow,[switch]$CheckOnly,[ValidateSet('auto','de','en')][string]$Language='auto')
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'Coop-Language.ps1')
$script:CoopLanguage=Get-CoopLanguage $Language
trap { throw (ConvertTo-CoopUserError $_.Exception.Message) }
. (Join-Path $PSScriptRoot 'Coop-Core.ps1')
if(!$GameDirectory -and !(Test-Path -LiteralPath (Join-Path $script:CoopStateRoot 'settings.json'))){
    if($CheckOnly){throw (Get-CoopText MissingGame)}
    $GameDirectory=Read-Host (Get-CoopText FolderPrompt)
}
. (Join-Path $PSScriptRoot 'Car-Choice.ps1')
. (Join-Path $PSScriptRoot 'Car-Preferences.ps1')
$game=Get-CoopGameDirectory $GameDirectory
Test-CoopReady $game
if(!$Nickname){$Nickname=(Get-CoopLastCarProfile -Role $Role).Nickname}
if($Nickname -notmatch '^[A-Za-z0-9_-]{1,16}$'){throw (Get-CoopText BadNickname)}
if(!$StartCarId){$StartCarId=Get-CoopSavedStartCar $Role $Nickname}
$startCar=Get-CoopStartCar $StartCarId
if($Role -eq 'Host'){$HostAddress='127.0.0.1'}elseif(!$HostAddress){if($CheckOnly){throw (Get-CoopText BadIp)};$HostAddress=Read-Host (Get-CoopText VpnPrompt)}
$address=$null
if(![Net.IPAddress]::TryParse($HostAddress,[ref]$address) -or $address.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork){throw (Get-CoopText BadIp)}
$clientExe=Join-Path $game 'Need For Speed The Run.exe'
$serverExe=Join-Path $game 'NFSTR_Server.exe'
$clientArgs="-Client.ServerIp ${HostAddress}:25200 -Client.QuitGameOnServerDisconnect False -Client.UseGlobalGamePadInput False"
$serverArgs='-Server.ServerName StoryCoop -GamePort 25200 -Game.DefaultLayerInclusion StartupMode=Game;GameMode=StoryMode -NfsOnline.Backend Backend_Lan -NfsGame.CarSelectTimer 0.0'
# GameSettings.MaxPlayerCount (Server-Reflection); Wirkung auf die Spielerzahl ist noch nicht live geprueft.
if($MaxPlayers -ne 2){$serverArgs+=" -Game.MaxPlayerCount $MaxPlayers"}
if($CheckOnly){[ordered]@{Status='verified';Language=$script:CoopLanguage;ShowServerWindow=[bool]$ShowServerWindow;MaxPlayers=$MaxPlayers;DifficultyControlAvailable=$true;HostDifficulty=$(if($Role -eq 'Host'){$Difficulty}else{$null});StartCar=$startCar.Name;StartCarHash=$startCar.HelperHash;Role=$Role;GameDirectory=$game;Nickname=$Nickname;ClientArguments=$clientArgs;ServerArguments=$(if($Role -eq 'Host'){$serverArgs}else{$null})}|ConvertTo-Json;return}
Assert-CoopClosed
$stamp=(Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8)
$session=Join-Path $script:CoopStateRoot "Sessions\$stamp"
New-Item -Path $session -ItemType Directory -Force|Out-Null
$profile=Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'NFSTR'
if(Test-Path -LiteralPath $profile){
    $snapshot=Join-Path $session 'SaveBeforeStart'
    Copy-Item -LiteralPath $profile -Destination $snapshot -Recurse
    $files=@(Get-ChildItem -LiteralPath $profile -File -Recurse|ForEach-Object {
        $relative=$_.FullName.Substring($profile.Length+1)
        $hash=Get-CoopFileHash $_.FullName
        if((Get-CoopFileHash (Join-Path $snapshot $relative)) -ne $hash){throw (Get-CoopText BackupFailed)}
        [ordered]@{RelativePath=$relative;Sha256=$hash}
    })
    [ordered]@{ProfileDirectory=$profile;Snapshot=$snapshot;Files=$files}|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $session 'save-manifest.json') -Encoding utf8
}
$configPath=Join-Path $game 'Scripts\NFSTR_LANOnlineHelper.ini'
$originalConfig=[IO.File]::ReadAllBytes($configPath)
[IO.File]::WriteAllBytes((Join-Path $session 'LANOnlineHelper-before.ini'),$originalConfig)
$config=[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'config\NFSTR_LANOnlineHelper.ini'))
$config=$config -replace '(?m)^ClientName = .*',"ClientName = $Nickname"
$config=Set-CoopStartCarConfig $config $StartCarId
if($StartCarId -ne 'story'){$config=$config -replace '(?m)^ForceInitFlow = .*','ForceInitFlow = MainMenu'}
Save-CoopCarPreference $Role $Nickname $StartCarId
[IO.File]::WriteAllText($configPath,$config,[Text.Encoding]::ASCII)
$launchConfigHash=Get-CoopFileHash $configPath
$record=[ordered]@{Version='0.7.5-TEST';Role=$Role;GameDirectory=$game;SessionDirectory=$session;Status='starting';Client=$null;Server=$null;StartCarId=$StartCarId;StartCarHash=$startCar.HelperHash}
$active=Join-Path $script:CoopStateRoot 'active-session.json'
Save-CoopSettings $game
if($StartCarId -ne 'story'){Write-Host (Get-CoopText StartCar -Values @($startCar.Name));Write-Host (Get-CoopText ViewCars)}
$client=$null;$server=$null
$garageJob=$null
try {
    $info=New-Object Diagnostics.ProcessStartInfo
    $info.FileName=$clientExe;$info.WorkingDirectory=$game;$info.UseShellExecute=$false
    $info.EnvironmentVariables['__COMPAT_LAYER']='RunAsInvoker';$info.Arguments=$clientArgs
    $info.EnvironmentVariables['THERUN_COOP_ROLE']=$Role.ToUpperInvariant()
    $client=[Diagnostics.Process]::Start($info)
    try{
        & (Join-Path $PSScriptRoot 'Start-GarageWindow.ps1') -GamePid $client.Id -RelayOnly:($Role -eq 'Guest') -Language $script:CoopLanguage
    }catch{Write-Host (Get-CoopText GarageFailed -Values @((ConvertTo-CoopUserError $_.Exception.Message)))}
    $garageJob=Start-Job -ScriptBlock {
        param($worker,$gamePid,$directory,$log)
        & $worker -GameProcessId $gamePid -GameDirectory $directory -LogPath $log
    } -ArgumentList (Join-Path $PSScriptRoot 'Unlock-Coop-Garage.ps1'),$client.Id,$game,(Join-Path $session 'garage-unlock.log')
    $record.Client=Get-CoopProcessRecord $client $clientExe
    $record.Status='client-started'
    $record|ConvertTo-Json -Depth 5|Set-Content -LiteralPath $active -Encoding utf8
    if($Role -eq 'Host'){
        $vpn=@(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue|Where-Object InterfaceAlias -eq 'Radmin VPN'|Select-Object -ExpandProperty IPAddress)
        if($vpn.Count){Write-Host (Get-CoopText YourIp -Values @(($vpn -join ', ')))}
        Write-Host (Get-CoopText Invite)
        Read-Host (Get-CoopText ReadyPrompt)|Out-Null
        $client.Refresh();if($client.HasExited){throw (Get-CoopText HostClosed)}
        # The native story-player adapter matches the actual host nickname.
        # Keep this environment value scoped to the server start.
        $previousCoopHostName=[Environment]::GetEnvironmentVariable('THERUN_HOST_NAME','Process')
        $previousCoopDifficulty=[Environment]::GetEnvironmentVariable('THERUN_DIFFICULTY','Process')
        try {
            $env:THERUN_HOST_NAME=$Nickname
            $env:THERUN_DIFFICULTY=$Difficulty.ToString([Globalization.CultureInfo]::InvariantCulture)
            $server=Start-Process -FilePath $serverExe -WorkingDirectory $game -ArgumentList $serverArgs -WindowStyle $(if($ShowServerWindow){'Normal'}else{'Hidden'}) -PassThru
        } finally {
            [Environment]::SetEnvironmentVariable('THERUN_HOST_NAME',$previousCoopHostName,'Process')
            [Environment]::SetEnvironmentVariable('THERUN_DIFFICULTY',$previousCoopDifficulty,'Process')
        }
        $record.Server=Get-CoopProcessRecord $server $serverExe
        Write-Host (Get-CoopText ServerStarted)
    }else{Write-Host (Get-CoopText GuestWaiting)}
    $record.Status='running'
    $record|ConvertTo-Json -Depth 5|Set-Content -LiteralPath $active -Encoding utf8
    Write-Host (Get-CoopText Saved -Values @($session))
    Write-Host (Get-CoopText LeaveOpen)
    $client.WaitForExit()
} finally {
    if($record.Server){Stop-CoopOwnedProcess $record.Server}
    if($record.Client){Stop-CoopOwnedProcess $record.Client -Graceful}
    if($garageJob){Stop-Job -Job $garageJob -ErrorAction SilentlyContinue;Remove-Job -Job $garageJob -Force -ErrorAction SilentlyContinue}
    if((Test-Path -LiteralPath $configPath) -and (Get-CoopFileHash $configPath) -eq $launchConfigHash){[IO.File]::WriteAllBytes($configPath,$originalConfig)}
    $record.Status='stopped'
    $record|ConvertTo-Json -Depth 5|Set-Content -LiteralPath $active -Encoding utf8
}

