#requires -Version 7.0
param([Parameter(Mandatory)][string]$GameDirectory,[string]$PackageDirectory=$PSScriptRoot,[switch]$Apply,[ValidateSet('auto','de','en')][string]$Language='auto')
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'Coop-Repair.ps1')
$plan=Get-CoopRepairPlan $GameDirectory $PackageDirectory
if($Apply){Invoke-CoopRepairPlan $plan;return}
[ordered]@{Status='repair-check-only';Ready=$plan.Ready;Files=@($plan.Changes|ForEach-Object RelativePath);Blocked=$plan.Blocked;WritesGame=$false;SaveRestore=$false;PersonalIniPreserved=$true}
