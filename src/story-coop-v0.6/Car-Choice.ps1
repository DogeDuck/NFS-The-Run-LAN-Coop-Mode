function Get-CoopStartCars {
    $cars=@(Get-Content -LiteralPath (Join-Path $PSScriptRoot 'Start-Cars.json') -Raw|ConvertFrom-Json)
    if($cars.Count -lt 1 -or $cars.Count -gt 64){throw 'Ungueltige Startauto-Liste.'}
    $seen=@{}
    foreach($car in $cars){
        if($car.Id -notmatch '^[A-Za-z0-9_-]{1,24}$' -or $seen.ContainsKey($car.Id)){throw 'Ungueltige oder doppelte Auto-ID.'}
        $seen[$car.Id]=$true
        if($car.HelperHash -notmatch '^(0|[0-9A-F]{8})$'){throw 'Ungueltiger Fahrzeug-Hash.'}
        if(!$car.Name -or $car.Name.Length -gt 80){throw 'Ungueltiger Fahrzeugname.'}
    }
    return $cars
}
function Get-CoopStartCar([string]$Id='story'){
    $found=@(Get-CoopStartCars|Where-Object Id -eq $Id)
    if($found.Count -ne 1){throw 'Dieses Startauto steht nicht zur Auswahl.'}
    return $found[0]
}
function Set-CoopStartCarConfig([string]$Config,[string]$Id='story'){
    $car=Get-CoopStartCar $Id
    $pattern='(?m)^ForceGarageCarHash\s*=\s*[^\r\n]*'
    if([regex]::Matches($Config,$pattern).Count -ne 1){throw 'Startauto-Einstellung fehlt oder ist doppelt.'}
    return [regex]::Replace($Config,$pattern,('ForceGarageCarHash = '+$car.HelperHash))
}
