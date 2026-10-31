param([ValidateSet('Host','Guest')][string]$Role='Host',[string]$GameDirectory,[string]$HostAddress,[string]$Nickname,[switch]$CheckOnly)
. (Join-Path $PSScriptRoot 'Coop-Core.ps1')
$game=Get-CoopGameDirectory $GameDirectory
Test-CoopReady $game
if(!$Nickname){$Nickname=if($Role -eq 'Host'){'CoopHost'}else{'CoopGuest'}}
if($Nickname -notmatch '^[A-Za-z0-9_-]{1,16}$'){throw 'Name: 1 bis 16 Buchstaben/Ziffern, _ oder -.'}
if($Role -eq 'Host'){$HostAddress='127.0.0.1'}elseif(!$HostAddress){if($CheckOnly){throw 'Fuer die Gast-Pruefung HostAddress angeben.'};$HostAddress=Read-Host 'Radmin-/VPN-IPv4 des Hosts'}
$address=$null
if(![Net.IPAddress]::TryParse($HostAddress,[ref]$address) -or $address.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork){throw 'Gueltige IPv4-Adresse des Hosts angeben.'}
$clientExe=Join-Path $game 'Need For Speed The Run.exe'
$serverExe=Join-Path $game 'NFSTR_Server.exe'
$clientArgs="-Client.ServerIp ${HostAddress}:25200 -Client.QuitGameOnServerDisconnect False -Client.UseGlobalGamePadInput False"
$serverArgs='-Server.ServerName StoryCoop -GamePort 25200 -Game.DefaultLayerInclusion StartupMode=Game;GameMode=StoryMode -NfsOnline.Backend Backend_Lan -NfsGame.CarSelectTimer 0.0'
if($CheckOnly){[ordered]@{Status='verified';Role=$Role;GameDirectory=$game;Nickname=$Nickname;ClientArguments=$clientArgs;ServerArguments=$(if($Role -eq 'Host'){$serverArgs}else{$null})}|ConvertTo-Json;return}
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
        if((Get-CoopFileHash (Join-Path $snapshot $relative)) -ne $hash){throw 'Spielstandssicherung fehlgeschlagen.'}
        [ordered]@{RelativePath=$relative;Sha256=$hash}
    })
    [ordered]@{ProfileDirectory=$profile;Snapshot=$snapshot;Files=$files}|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $session 'save-manifest.json') -Encoding utf8
}
$configPath=Join-Path $game 'Scripts\NFSTR_LANOnlineHelper.ini'
$originalConfig=[IO.File]::ReadAllBytes($configPath)
[IO.File]::WriteAllBytes((Join-Path $session 'LANOnlineHelper-before.ini'),$originalConfig)
$config=[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'config\NFSTR_LANOnlineHelper.ini'))
$config=$config -replace '(?m)^ClientName = .*',"ClientName = $Nickname"
[IO.File]::WriteAllText($configPath,$config,[Text.Encoding]::ASCII)
$launchConfigHash=Get-CoopFileHash $configPath
$record=[ordered]@{Version='0.3-TEST';Role=$Role;GameDirectory=$game;SessionDirectory=$session;Status='starting';Client=$null;Server=$null}
$active=Join-Path $script:CoopStateRoot 'active-session.json'
Save-CoopSettings $game
$client=$null;$server=$null
$garageJob=$null
try {
    $info=New-Object Diagnostics.ProcessStartInfo
    $info.FileName=$clientExe;$info.WorkingDirectory=$game;$info.UseShellExecute=$false
    $info.EnvironmentVariables['__COMPAT_LAYER']='RunAsInvoker';$info.Arguments=$clientArgs
    $client=[Diagnostics.Process]::Start($info)
    $garageJob=Start-Job -ScriptBlock {
        param($worker,$gamePid,$directory,$log)
        & $worker -GameProcessId $gamePid -GameDirectory $directory -LogPath $log
    } -ArgumentList (Join-Path $PSScriptRoot 'Unlock-Coop-Garage.ps1'),$client.Id,$game,(Join-Path $session 'garage-unlock.log')
    $record.Client=Get-CoopProcessRecord $client $clientExe
    $record.Status='client-started'
    $record|ConvertTo-Json -Depth 5|Set-Content -LiteralPath $active -Encoding utf8
    if($Role -eq 'Host'){
        $vpn=@(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue|Where-Object InterfaceAlias -eq 'Radmin VPN'|Select-Object -ExpandProperty IPAddress)
        if($vpn.Count){Write-Host ('Deine Radmin-IP: '+($vpn -join ', '))}
        Write-Host 'Der Kumpel startet jetzt Start-Guest.cmd auf seinem PC.'
        Read-Host 'Enter druecken, sobald sein Spielfenster offen ist'|Out-Null
        $client.Refresh();if($client.HasExited){throw 'Das Host-Spielfenster wurde geschlossen.'}
        $server=Start-Process -FilePath $serverExe -WorkingDirectory $game -ArgumentList $serverArgs -WindowStyle Hidden -PassThru
        $record.Server=Get-CoopProcessRecord $server $serverExe
        Write-Host 'Server gestartet. Sobald beide verbunden sind: nur der Host waehlt THE RUN -> Fortsetzen.'
    }else{Write-Host 'Warte im Spielfenster auf die Verbindung. Der Host startet danach den Server und waehlt Fortsetzen.'}
    $record.Status='running'
    $record|ConvertTo-Json -Depth 5|Set-Content -LiteralPath $active -Encoding utf8
    Write-Host "Spielstand vor dem Start gesichert in: $session"
    Write-Host 'Dieses Starterfenster offen lassen, bis das Spiel beendet ist.'
    $client.WaitForExit()
} finally {
    if($record.Server){Stop-CoopOwnedProcess $record.Server}
    if($record.Client){Stop-CoopOwnedProcess $record.Client -Graceful}
    if($garageJob){Stop-Job -Job $garageJob -ErrorAction SilentlyContinue;Remove-Job -Job $garageJob -Force -ErrorAction SilentlyContinue}
    if((Test-Path -LiteralPath $configPath) -and (Get-CoopFileHash $configPath) -eq $launchConfigHash){[IO.File]::WriteAllBytes($configPath,$originalConfig)}
    $record.Status='stopped'
    $record|ConvertTo-Json -Depth 5|Set-Content -LiteralPath $active -Encoding utf8
}

