param(
    [ValidateSet('Apply','Restore')][string]$Mode='Apply',
    [string]$GamePath='',
    [switch]$CheckOnly
)
$ErrorActionPreference='Stop'
# Eigenstaendiger lokaler Audio-Patch: Musik +25 dB, Effekte -2 dB, Sprache original.
# Die komprimierten Daten enthalten Zielwerte UND saemtliche Originalbytes.
$encoded='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'
$memory=New-Object IO.MemoryStream(,[Convert]::FromBase64String($encoded))
$gzip=New-Object IO.Compression.GZipStream($memory,[IO.Compression.CompressionMode]::Decompress)
$reader=New-Object IO.StreamReader($gzip,[Text.Encoding]::UTF8)
try { $plan=$reader.ReadToEnd() | ConvertFrom-Json } finally { $reader.Dispose(); $gzip.Dispose(); $memory.Dispose() }
if([string]::IsNullOrWhiteSpace($GamePath)) {
    if(Test-Path -LiteralPath (Join-Path $PSScriptRoot 'Need For Speed The Run.exe')) { $GamePath=$PSScriptRoot }
    else { $GamePath=$plan.game_directory }
}
$gameRoot=[IO.Path]::GetFullPath($GamePath).TrimEnd('\')+'\'
if(-not (Test-Path -LiteralPath (Join-Path $gameRoot 'Need For Speed The Run.exe'))) {
    throw "Die Spiel-EXE fehlt in $gameRoot. Den richtigen Ordner mit -GamePath angeben."
}
if(!$CheckOnly -and (Get-Process -Name 'Need For Speed The Run','dlss5-feed-host64' -ErrorAction SilentlyContinue)) {
    throw 'The Run und den DLSS-Host vor dem Patchen vollstaendig schliessen.'
}
function Resolve-GameFile([string]$Relative) {
    $path=[IO.Path]::GetFullPath([IO.Path]::Combine($gameRoot,$Relative))
    if(-not $path.StartsWith($gameRoot,[StringComparison]::OrdinalIgnoreCase)) { throw 'Ungueltiger Dateipfad im Patch.' }
    return $path
}
function Convert-HexBytes([string]$Hex) {
    $bytes=New-Object byte[] ($Hex.Length/2)
    for($i=0;$i -lt $bytes.Length;$i++) { $bytes[$i]=[Convert]::ToByte($Hex.Substring($i*2,2),16) }
    return ,$bytes
}
function Read-Bytes($Stream,[long]$Offset,[int]$Count) {
    if($Offset -lt 0 -or $Offset+$Count -gt $Stream.Length) { throw 'Ungueltige Dateiposition.' }
    [void]$Stream.Seek($Offset,[IO.SeekOrigin]::Begin)
    $bytes=New-Object byte[] $Count
    if($Stream.Read($bytes,0,$Count) -ne $Count) { throw 'Datei konnte nicht vollstaendig gelesen werden.' }
    return ,$bytes
}
function To-Hex([byte[]]$Bytes) {
    return [BitConverter]::ToString($Bytes).Replace('-','').ToLowerInvariant()
}
function Read-Ranges($Ranges) {
    $buffer=New-Object IO.MemoryStream
    try {
        foreach($range in $Ranges) {
            $path=Resolve-GameFile $range.path
            if($streams.ContainsKey($path)) { $stream=$streams[$path] }
            else {
                if(-not $readers.ContainsKey($path)) { $readers[$path]=[IO.File]::OpenRead($path) }
                $stream=$readers[$path]
            }
            $bytes=Read-Bytes $stream ([long]$range.offset) ([int]$range.length)
            $buffer.Write($bytes,0,$bytes.Length)
        }
        return ,$buffer.ToArray()
    } finally { $buffer.Dispose() }
}
function Assert-Assets([string]$State) {
    $sha=[Security.Cryptography.SHA1]::Create()
    try {
        foreach($asset in $plan.assets) {
            $bytes=Read-Ranges $asset.data_ranges
            $digest=To-Hex ($sha.ComputeHash($bytes))
            $expected=if($State -eq 'Target'){$asset.new_sha1}else{$asset.original_sha1}
            if($digest -ne $expected) { throw "Audio-Asset stimmt nicht mit dem Patch ueberein: $($asset.asset)" }
            $stored=To-Hex (Read-Ranges $asset.checksum_ranges)
            if($stored -ne $digest) { throw "Pruefsumme stimmt nicht: $($asset.asset)" }
        }
    } finally { $sha.Dispose() }
}
$streams=@{}
$readers=@{}
$operations=New-Object 'System.Collections.Generic.List[object]'
$completed=New-Object 'System.Collections.Generic.List[object]'
$desired=if($Mode -eq 'Apply'){'Target'}else{'Original'}
try {
    foreach($entry in $plan.files) {
        $path=Resolve-GameFile $entry.path
        $stream=[IO.File]::Open($path,[IO.FileMode]::Open,$(if($CheckOnly){[IO.FileAccess]::Read}else{[IO.FileAccess]::ReadWrite}),[IO.FileShare]::Read)
        $streams[$path]=$stream
        if($stream.Length -ne [long]$entry.size) { throw "Andere Spieldateiversion: $path" }
        $candidates=@($plan.states)
        foreach($block in $entry.blocks) {
            $current=To-Hex (Read-Bytes $stream ([long]$block.offset) ($block.states.Original.Length/2))
            $candidates=@($candidates | Where-Object { $current -eq $block.states.$_ })
            $target=$block.states.$desired
            if($current -ne $target) {
                $operations.Add([pscustomobject]@{Path=$path;Offset=[long]$block.offset;Source=$current;Target=$target})
            }
        }
        if($candidates.Count -eq 0) { throw "Unbekannter oder anderweitig veraenderter Dateistand: $path. Vor dem Schreiben abgebrochen." }
    }
    if($CheckOnly){Write-Output 'Audio-Patch: Dateiversion und alle Patchstellen kompatibel.';return}
    foreach($op in $operations) {
        $stream=$streams[$op.Path]
        $bytes=Convert-HexBytes $op.Target
        [void]$stream.Seek($op.Offset,[IO.SeekOrigin]::Begin)
        $completed.Add($op)
        $stream.Write($bytes,0,$bytes.Length)
    }
    foreach($stream in $streams.Values) { $stream.Flush($true) }
    foreach($entry in $plan.files) {
        $path=Resolve-GameFile $entry.path
        foreach($block in $entry.blocks) {
            $actual=To-Hex (Read-Bytes $streams[$path] ([long]$block.offset) ($block.states.Original.Length/2))
            if($actual -ne $block.states.$desired) { throw 'Bytepruefung nach dem Schreiben fehlgeschlagen.' }
        }
    }
    Assert-Assets $desired
    if($Mode -eq 'Apply') { Write-Output 'Angewendet: Musik +25 dB, Effekte/Umgebung/UI -2 dB, Sprache Original.' }
    else { Write-Output 'Originaler Audiomix vollstaendig wiederhergestellt.' }
    Write-Output "Gepruefte Audio-Assets: $($plan.assets.Count). Dateien: $($plan.files.Count). Geschriebene Bloecke: $($operations.Count)."
} catch {
    $failure=$_
    for($i=$completed.Count-1;$i -ge 0;$i--) {
        $op=$completed[$i]
        $bytes=Convert-HexBytes $op.Source
        $stream=$streams[$op.Path]
        [void]$stream.Seek($op.Offset,[IO.SeekOrigin]::Begin)
        $stream.Write($bytes,0,$bytes.Length)
    }
    foreach($stream in $streams.Values) { $stream.Flush($true) }
    throw $failure
} finally {
    foreach($stream in $readers.Values) { $stream.Dispose() }
    foreach($stream in $streams.Values) { $stream.Dispose() }
}
