#requires -Version 7.0
# Personal JSON only. Invalid existing data is never silently overwritten.
function Read-CoopJsonObject {
 param([Parameter(Mandatory)][string]$Path,[int]$MaxBytes=262144)
 if(!(Test-Path -LiteralPath $Path -PathType Leaf)){return [ordered]@{}}
 if((Get-Item -LiteralPath $Path).Length -gt $MaxBytes){throw 'Personal settings file is too large / Persoenliche Einstellungsdatei ist zu gross.'}
 try{$value=ConvertFrom-Json -InputObject ([IO.File]::ReadAllText($Path)) -AsHashtable -Depth 32 -ErrorAction Stop}catch{throw 'Personal settings are damaged; original file preserved / Persoenliche Einstellungen sind beschaedigt; Originaldatei bleibt erhalten.'}
 if($value -isnot [System.Collections.IDictionary]){throw 'Personal settings must be a JSON object / Persoenliche Einstellungen muessen ein JSON-Objekt sein.'}
 return $value
}
function Write-CoopJsonObjectAtomic {
 param([Parameter(Mandatory)][string]$Path,[Parameter(Mandatory)][System.Collections.IDictionary]$Value)
 $full=[IO.Path]::GetFullPath($Path);$parent=[IO.Path]::GetDirectoryName($full)
 [void][IO.Directory]::CreateDirectory($parent)
 $tmp=Join-Path $parent ([IO.Path]::GetRandomFileName())
 try{[IO.File]::WriteAllText($tmp,($Value|ConvertTo-Json -Depth 24),[Text.UTF8Encoding]::new($false));[IO.File]::Move($tmp,$full,$true)}
 finally{if(Test-Path -LiteralPath $tmp){Remove-Item -LiteralPath $tmp}}
}
function Merge-CoopJsonObject {
 param([Parameter(Mandatory)][string]$Path,[Parameter(Mandatory)][System.Collections.IDictionary]$Changes)
 $data=Read-CoopJsonObject $Path
 foreach($key in $Changes.Keys){$data[$key]=$Changes[$key]}
 Write-CoopJsonObjectAtomic $Path $data
}
