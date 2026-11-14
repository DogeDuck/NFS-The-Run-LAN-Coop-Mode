param(
    [ValidateSet('Apply','Restore')][string]$Mode='Apply',
    [ValidateSet('Dim','Clear')][string]$Variant='Dim',
    [string]$GamePath='',
    [switch]$CheckOnly
)
$ErrorActionPreference='Stop'
# Persoenlicher HUD-Patch (Claude 14.11.2026): Tacho-Hintergrund (Scheibe + Ziffernplatte) Dim = 15 %, Clear = aus.
# Aendert nur zwei Textur-Chunks in Data\Win32\UI.sb, byte-genau gleich gross, Bundle/TOC unveraendert.
# Plan (hud-alpha-plan.json) enthaelt pro Stelle Original- UND Zielbytes; vor dem Schreiben wird alles geprueft,
# bei Fehlern wird zurueckgeschrieben. Restore stellt die Originalbytes exakt wieder her.
$planPath=Join-Path $PSScriptRoot 'hud-alpha-plan.json'
if(!(Test-Path -LiteralPath $planPath -PathType Leaf)){throw 'HUD-Plan fehlt: hud-alpha-plan.json'}
$plan=Get-Content -LiteralPath $planPath -Raw -Encoding UTF8 | ConvertFrom-Json
if([string]::IsNullOrWhiteSpace($GamePath)){throw 'Spielordner fehlt (-GamePath).'}
$gameRoot=[IO.Path]::GetFullPath($GamePath).TrimEnd('\')+'\'
if(-not (Test-Path -LiteralPath (Join-Path $gameRoot 'Need For Speed The Run.exe'))){
    throw "Die Spiel-EXE fehlt in $gameRoot. Den richtigen Ordner mit -GamePath angeben."
}
if(!$CheckOnly -and (Get-Process -Name 'Need For Speed The Run','NFSTR_Server','dlss5-feed-host64' -ErrorAction SilentlyContinue)){
    throw 'The Run, Server und DLSS-Host vor dem HUD-Patch vollstaendig schliessen.'
}
function Resolve-GameFile([string]$Relative){
    $path=[IO.Path]::GetFullPath([IO.Path]::Combine($gameRoot,$Relative))
    if(-not $path.StartsWith($gameRoot,[StringComparison]::OrdinalIgnoreCase)){throw 'Ungueltiger Dateipfad im Patch.'}
    return $path
}
function Convert-HexBytes([string]$Hex){
    $bytes=New-Object byte[] ($Hex.Length/2)
    for($i=0;$i -lt $bytes.Length;$i++){$bytes[$i]=[Convert]::ToByte($Hex.Substring($i*2,2),16)}
    return ,$bytes
}
function Read-Bytes($Stream,[long]$Offset,[int]$Count){
    if($Offset -lt 0 -or $Offset+$Count -gt $Stream.Length){throw 'Ungueltige Dateiposition.'}
    [void]$Stream.Seek($Offset,[IO.SeekOrigin]::Begin)
    $bytes=New-Object byte[] $Count
    $read=0
    while($read -lt $Count){$n=$Stream.Read($bytes,$read,$Count-$read);if($n -le 0){throw 'Datei konnte nicht vollstaendig gelesen werden.'};$read+=$n}
    return ,$bytes
}
function To-Hex([byte[]]$Bytes){return [BitConverter]::ToString($Bytes).Replace('-','').ToLowerInvariant()}
function Assert-Chunks($Stream,[string]$State){
    $sha=[Security.Cryptography.SHA1]::Create()
    try{
        foreach($chunk in $plan.chunks){
            $digest=To-Hex ($sha.ComputeHash((Read-Bytes $Stream ([long]$chunk.offset) ([int]$chunk.length))))
            $expected=$chunk.sha1.$State
            if($digest -ne $expected){throw "HUD-Textur stimmt nicht mit dem Patch ueberein: $($chunk.texture)"}
        }
    }finally{$sha.Dispose()}
}
$entry=@($plan.files)[0]
$path=Resolve-GameFile $entry.path
$desired=if($Mode -eq 'Apply'){$Variant}else{'Original'}
$operations=New-Object 'System.Collections.Generic.List[object]'
$completed=New-Object 'System.Collections.Generic.List[object]'
$stream=[IO.File]::Open($path,[IO.FileMode]::Open,$(if($CheckOnly){[IO.FileAccess]::Read}else{[IO.FileAccess]::ReadWrite}),[IO.FileShare]::Read)
try{
    if($stream.Length -ne [long]$entry.size){throw "Andere Spieldateiversion: $path"}
    $candidates=@($plan.states)
    foreach($block in $entry.blocks){
        $current=To-Hex (Read-Bytes $stream ([long]$block.offset) ($block.states.Original.Length/2))
        $candidates=@($candidates | Where-Object {$current -eq $block.states.$_})
        if($current -ne $block.states.$desired){
            $operations.Add([pscustomobject]@{Offset=[long]$block.offset;Source=$current;Target=$block.states.$desired})
        }
    }
    if($candidates.Count -eq 0){throw "Unbekannter oder anderweitig veraenderter Stand von UI.sb. Vor dem Schreiben abgebrochen."}
    Assert-Chunks $stream $candidates[0]
    if($CheckOnly){Write-Output "HUD-Patch: UI.sb kompatibel, aktueller Stand $($candidates[0])."; return}
    foreach($op in $operations){
        $bytes=Convert-HexBytes $op.Target
        [void]$stream.Seek($op.Offset,[IO.SeekOrigin]::Begin)
        $completed.Add($op)
        $stream.Write($bytes,0,$bytes.Length)
    }
    $stream.Flush($true)
    foreach($block in $entry.blocks){
        $actual=To-Hex (Read-Bytes $stream ([long]$block.offset) ($block.states.Original.Length/2))
        if($actual -ne $block.states.$desired){throw 'Bytepruefung nach dem Schreiben fehlgeschlagen.'}
    }
    Assert-Chunks $stream $desired
    if($Mode -eq 'Restore'){Write-Output 'HUD: Original-Tacho wiederhergestellt.'}elseif($Variant -eq 'Clear'){Write-Output 'HUD: Tacho-Hintergrund ausgeblendet.'}else{Write-Output 'HUD: Tacho-Hintergrund auf 15 % gesetzt.'}
}catch{
    $failure=$_
    for($i=$completed.Count-1;$i -ge 0;$i--){
        $op=$completed[$i];$bytes=Convert-HexBytes $op.Source
        [void]$stream.Seek($op.Offset,[IO.SeekOrigin]::Begin);$stream.Write($bytes,0,$bytes.Length)
    }
    $stream.Flush($true)
    throw $failure
}finally{$stream.Dispose()}
