"""Bundle pinned, user-requested addons into every new installer."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent


def bundle(destination):
    source = ROOT / 'third_party/coop-addons'
    manifest = json.loads((source / 'manifest.json').read_text())
    for relative, digest in manifest['files'].items():
        path = source / relative
        if path.resolve().is_relative_to(source.resolve()) is False:
            raise ValueError('Invalid addon path')
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Addon changed: ' + relative)
    shutil.copytree(source, destination / 'addons')
    installer = destination / 'Install-Coop.ps1'
    text = installer.read_text(encoding='utf-8-sig')
    preflight = '''$addonRoot=Join-Path $PSScriptRoot 'addons'
$addonManifest=Get-Content -LiteralPath (Join-Path $addonRoot 'manifest.json') -Raw|ConvertFrom-Json
foreach($item in $addonManifest.files.PSObject.Properties){
 $file=Join-Path $addonRoot $item.Name
 if((Get-CoopFileHash $file) -ne $item.Value){throw ('Addon-Pruefsumme stimmt nicht: '+$item.Name)}
}
$music=Join-Path $addonRoot 'music25\\NFS-Audio-Patch.ps1'
& $music -GamePath $game -CheckOnly
'''
    marker = '$staged=@{}'
    if text.count(marker) != 1:
        raise ValueError('Installer preflight insertion differs')
    text = text.replace(marker, preflight + marker, 1)
    marker = "$specialK=Join-Path"
    stage = '''foreach($name in @('NFSTR_DefinitiveEdition.asi','NFSTR_DefinitiveEdition.ini')){
 $staged[('Scripts\\'+$name)]=[IO.File]::ReadAllBytes((Join-Path $addonRoot $name))
}
'''
    if text.count(marker) != 1:
        raise ValueError('Installer staging insertion differs')
    text = text.replace(marker, stage + marker, 1)
    text = text.replace('if(!$changes.Count){', 'if(!$changes.Count){& $music -GamePath $game -Mode Apply;', 1)
    marker = "$manifest.Status='installed'"
    if text.count(marker) != 1:
        raise ValueError('Installer completion insertion differs')
    text = text.replace(marker, '& $music -GamePath $game -Mode Apply\n' + marker, 1)
    installer.write_text(text, encoding='utf-8-sig')
    restore = destination / 'Restore-Installation.ps1'
    content = restore.read_text(encoding='utf-8-sig')
    content = content.replace("$allowed=@(", "$allowed=@('Scripts\\NFSTR_DefinitiveEdition.asi','Scripts\\NFSTR_DefinitiveEdition.ini',", 1)
    restore.write_text(content, encoding='utf-8-sig')

    (destination / 'ADDONS.md').write_text('''# Feste Bestandteile dieses Testpakets

Definitive Edition wird automatisch unter Scripts installiert: FPS-/Motor-Audio-
und Partikelfixes aktiv, Fahrziel240FPS, Cutscene-/QTE-Clamp aktiv. Schnelleres
Laden (VSync-Bypass) und Schatten4096/Sichtweite600 sind aktiviert. Zusaetzliche
Schwierigkeitsmodi, Tageszeit-, Fahrzeug-, Kamera- und Verkehrsveraenderungen sind
im Coop-Profil ausgeschaltet. Diese Grafikwerte sind Nutzerstandard, kein Koopfix. Quelle/Commit und Datei-SHA256: addons/manifest.json.
MIT-Lizenz liegt bei. Diese Kombination ist noch nicht im Spiel bestaetigt.

Musikpatch: Musik+25dB, Effekte-2dB, Sprache original. Vor Installation werden
alle Patchstellen geprueft; der Audiopatch setzt bei Fehlern seine eigenen
Schreibvorgaenge zurueck. Wiederholte Installation addiert keine weitere Lautstaerke.
Originalmix: addons/music25/NFS-Audio-Patch.ps1 -GamePath "SPIELORDNER" -Mode Restore.
Die Wiederherstellung der Coop-Dateien stellt den Audiomix nicht automatisch um.

Offen: Brueckenabsturz/fehlende Zwischenszenen, KI-Racer und Missionsuebergaenge.
Keine weiteren gefundenen EXE-/Spielarchiv-Mods sind pauschal enthalten.
''', encoding='utf-8')
    return manifest
