#requires -Version 7.0
# Keep personal helper options; change only the keys required by this session.
function Set-CoopSessionIniValue {
 param([string]$Text,[string]$Section,[string]$Key,[string]$Value)
 $newline=if($Text.Contains("`r`n")){"`r`n"}else{"`n"}
 $lines=[Collections.Generic.List[string]]::new();foreach($line in ($Text -split '\r?\n')){$lines.Add($line)}
 $current='';$sections=0;$keyCount=0;$insert=-1
 for($i=0;$i -lt $lines.Count;$i++){
  if($lines[$i] -match '^\s*\[([^\]]+)\]\s*(?:[;#].*)?$'){
   if($current -ieq $Section -and $insert -lt 0){$insert=$i}
   $current=$Matches[1]
   if($current -ieq $Section){$sections++}
  }elseif($current -ieq $Section -and $lines[$i] -match ('^\s*'+[regex]::Escape($Key)+'\s*=')){
   $keyCount++;$lines[$i]=$Key+' = '+$Value
  }
 }
 if($sections -gt 1 -or $keyCount -gt 1){throw 'Duplicate session INI key/section; original preserved / Doppelter INI-Schluessel oder Abschnitt; Original bleibt erhalten.'}
 if(!$keyCount){
  if(!$sections){$lines.Add('['+$Section+']');$lines.Add($Key+' = '+$Value)}
  else{if($insert -lt 0){$insert=$lines.Count};$lines.Insert($insert,$Key+' = '+$Value)}
 }
 return $lines -join $newline
}
function New-CoopSessionConfig {
 param([Parameter(Mandatory)][string]$Original,[Parameter(Mandatory)][string]$Nickname,[Parameter(Mandatory)][string]$CarHash,[bool]$CustomCar=$false)
 if($Nickname -notmatch '^[A-Za-z0-9_-]{1,16}$' -or $CarHash -notmatch '^(0|[0-9A-F]{8})$'){throw 'Invalid session values / Ungueltige Sitzungswerte.'}
 $changes=@(
  @('OnlineSettings','EnableLANOnlineTweaks','1'),@('OnlineSettings','DisableAutologConnectAttempts','1'),
  @('OnlineSettings','DisableUserComputerName','1'),@('OnlineSettings','ClientName',$Nickname),
  @('PlaylistSettings','ForceClientPlaylistPtrInMemory','0'),
  @('GameSettings','EnableDebugModeMenus','1'),@('GameSettings','ForceGarageCarHash',$CarHash),
  @('GameSettings','ForceInitFlow',$(if($CustomCar){'MainMenu'}else{'TheRun'})),
  @('ServerSettings','ForceCustomPlaylistSessionFirstID','0'),@('ServerSettings','DisablePlaylistSessionIDChanges','0'),
  @('ServerSettings','ForcePlaylistLoading','0'),@('ServerSettings','ForceServerPlayersCarHash','0'))
 $text=$Original
 foreach($row in $changes){$text=Set-CoopSessionIniValue $text $row[0] $row[1] $row[2]}
 return $text
}
