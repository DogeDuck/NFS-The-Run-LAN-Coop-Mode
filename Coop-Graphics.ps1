#requires -Version 7.0
# Persoenliche Grafik-Einstellungen (nur dieser PC, nie vom Host synchronisiert) fuer die Definitive Edition:
# Scripts\NFSTR_DefinitiveEdition.ini. Standard = ausgeliefertes Koop-Profil (240 FPS, Schatten 4096/600, AF 16,
# Sichtfeld wie im Spiel). Der Launcher schreibt vor jedem Start nur diese Zeilen; alle anderen Bytes, Kommentare,
# Kodierung und Zeilenenden der INI bleiben gleich. Ein Update spielt die INI neu ein; der naechste Start setzt die
# gewaehlten Werte wieder. Ein eigenes Sichtfeld braucht den DE-Hauptschalter EnableRenderTweaks (aktiviert dann auch
# den DE-Minimap-Fix); beim Spiel-Sichtfeld bleibt er wie ausgeliefert aus.
$script:CoopGraphicsKeys=@('FPSLimit','ShadowmapResolution','ShadowmapViewDistance','AnisotropicFiltering','ForceFov')
$script:CoopGraphicsDefaults=[ordered]@{FPSLimit=240;ShadowmapResolution=4096;ShadowmapViewDistance=600;AnisotropicFiltering=16;ForceFov=0}
$script:CoopGraphicsChoices=[ordered]@{
    FPSLimit=@(30,60,120,144,165,240,-1)
    ShadowmapResolution=@(-1,2048,4096)
    ShadowmapViewDistance=@(200,400,600,800)
    AnisotropicFiltering=@(1,2,4,8,16)
    ForceFov=@(0,55,60,65,70)
}

# Liest Werte aus Launcher-Zustand/Objekt; ungueltige oder fehlende Werte werden zum Standard.
function ConvertTo-CoopGraphicsSettings($Source){
    $result=[ordered]@{}
    foreach($key in $script:CoopGraphicsKeys){
        $value=$script:CoopGraphicsDefaults[$key]
        if($null -ne $Source){
            $raw=if($Source -is [Collections.IDictionary]){$Source[$key]}else{$Source.$key}
            $number=0
            if(($raw -is [int] -or $raw -is [long] -or $raw -is [string]) -and [int]::TryParse([string]$raw,[ref]$number) -and $number -in $script:CoopGraphicsChoices[$key]){$value=$number}
        }
        $result[$key]=$value
    }
    return $result
}

# Rueckgabe: missing (keine DE-INI) | unchanged | updated. Unbekannte INI-Struktur: Fehler, Datei unveraendert.
function Set-CoopGraphicsIni([string]$GameDirectory,$Settings){
    $ini=Join-Path $GameDirectory 'Scripts\NFSTR_DefinitiveEdition.ini'
    if(!(Test-Path -LiteralPath $ini -PathType Leaf)){return 'missing'}
    $values=ConvertTo-CoopGraphicsSettings $Settings
    $lines=[ordered]@{}
    foreach($key in $script:CoopGraphicsKeys){$lines[$key]=[string]$values[$key]}
    $lines['EnableRenderTweaks']=if($values.ForceFov -gt 0){'1'}else{'0'}
    $bytes=[IO.File]::ReadAllBytes($ini)
    $bom=$bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF
    $skip=if($bom){3}else{0}
    $text=([Text.UTF8Encoding]::new($false,$true)).GetString($bytes,$skip,$bytes.Length-$skip)
    $new=$text
    foreach($key in $lines.Keys){
        $pattern='(?m)^('+[regex]::Escape($key)+'[ \t]*=[ \t]*)[^\r\n;]*'
        if([regex]::Matches($new,$pattern).Count -ne 1){throw ('Definitive-Edition-INI hat eine unbekannte Struktur: '+$key)}
        $new=[regex]::Replace($new,$pattern,'${1}'+$lines[$key])
    }
    if($new -ceq $text){return 'unchanged'}
    $body=[Text.UTF8Encoding]::new($false).GetBytes($new)
    $output=if($bom){[byte[]](0xEF,0xBB,0xBF)+$body}else{$body}
    $tmp=$ini+'.coop-write'
    try{
        [IO.File]::WriteAllBytes($tmp,[byte[]]$output)
        [IO.File]::Replace($tmp,$ini,[NullString]::Value)
    }finally{if(Test-Path -LiteralPath $tmp){Remove-Item -LiteralPath $tmp -Force}}
    if(-not [Linq.Enumerable]::SequenceEqual([byte[]][IO.File]::ReadAllBytes($ini),[byte[]]$output)){throw 'Definitive-Edition-INI konnte nicht verifiziert werden.'}
    return 'updated'
}

# Hoechste aktuelle Bildwiederholrate (Hz) als Hinweis im Grafik-Fenster; 0 wenn unbekannt.
function Get-CoopMonitorRefreshRate{
    try{
        $rates=@(Get-CimInstance -ClassName Win32_VideoController -ErrorAction Stop|ForEach-Object{[int]$_.CurrentRefreshRate}|Where-Object{$_ -gt 1})
        if($rates.Count){return ($rates|Measure-Object -Maximum).Maximum}
    }catch{}
    return 0
}
