#requires -Version 7.0
# Preference data only: no game, INI, process-memory or save-file writes.
function Get-CoopCarPreferencePath {
    if(!$env:LOCALAPPDATA){throw 'LOCALAPPDATA fehlt.'}
    return Join-Path $env:LOCALAPPDATA 'TheRunStoryCoop\car-preferences.json'
}
function Read-CoopCarPreferences([string]$Path=(Get-CoopCarPreferencePath)) {
    if(!(Test-Path -LiteralPath $Path)){return @()}
    if((Get-Item -LiteralPath $Path).Length -gt 65536){throw 'Autoauswahl-Datei ist zu gross.'}
    $data=Get-Content -LiteralPath $Path -Raw -Encoding utf8 | ConvertFrom-Json -ErrorAction Stop
    if($data.Schema -ne 1 -or @($data.Players).Count -gt 128){throw 'Autoauswahl-Dateiformat unbekannt.'}
    $seen=@{}
    foreach($entry in @($data.Players)){
        if($entry.Role -notin @('Host','Guest') -or $entry.Nickname -notmatch '^[A-Za-z0-9_-]{1,16}$'){throw 'Ungueltiges Autoauswahl-Profil.'}
        [void](Get-CoopStartCar $entry.CarId)
        $key=$entry.Role+'/'+$entry.Nickname
        if($seen.ContainsKey($key)){throw 'Doppeltes Autoauswahl-Profil.'}
        $seen[$key]=$true
    }
    return @($data.Players)
}
function Get-CoopSavedStartCar([ValidateSet('Host','Guest')][string]$Role,[string]$Nickname,[string]$Path=(Get-CoopCarPreferencePath)) {
    $match=@(Read-CoopCarPreferences $Path | Where-Object {$_.Role -ieq $Role -and $_.Nickname -ieq $Nickname})
    if(!$match.Count){return 'story'}
    return [string]$match[0].CarId
}
function Get-CoopLastCarProfile([string]$Role,[string]$Path=(Get-CoopCarPreferencePath)) {
    if($Role -and $Role -notin @('Host','Guest')){throw 'Ungueltige Rolle.'}
    $players=@(Read-CoopCarPreferences $Path | Where-Object {!$Role -or $_.Role -ieq $Role})
    if($players.Count){return $players[-1]}
    $defaultRole=if($Role){$Role}else{'Host'}
    return [pscustomobject]@{Role=$defaultRole;Nickname=$(if($defaultRole -eq 'Host'){'CoopHost'}else{'CoopGuest'});CarId='story'}
}
function Save-CoopCarPreference([ValidateSet('Host','Guest')][string]$Role,[string]$Nickname,[string]$CarId,[string]$Path=(Get-CoopCarPreferencePath)) {
    if($Nickname -notmatch '^[A-Za-z0-9_-]{1,16}$'){throw 'Ungueltiger Spielername.'}
    [void](Get-CoopStartCar $CarId)
    $players=@(Read-CoopCarPreferences $Path | Where-Object {!($_.Role -ieq $Role -and $_.Nickname -ieq $Nickname)})
    if($players.Count -ge 128){throw 'Zu viele Autoauswahl-Profile.'}
    $players+= [ordered]@{Role=$Role;Nickname=$Nickname;CarId=$CarId}
    $parent=Split-Path -Parent ([IO.Path]::GetFullPath($Path))
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    $temporary=Join-Path $parent ([IO.Path]::GetRandomFileName())
    try{
        $text=[ordered]@{Schema=1;Players=@($players)} | ConvertTo-Json -Depth 5
        [IO.File]::WriteAllText($temporary,$text,[Text.UTF8Encoding]::new($false))
        [IO.File]::Move($temporary,[IO.Path]::GetFullPath($Path),$true)
    }finally{if(Test-Path -LiteralPath $temporary){Remove-Item -LiteralPath $temporary}}
}
