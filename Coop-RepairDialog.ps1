#requires -Version 7.0
# Presentation only: does not inspect or modify the game, backups or saves.
function Get-CoopRepairPresentation {
 param([Parameter(Mandatory)]$Result)
 if($Result.Status -ne 'repaired'){throw 'Unexpected repair result / Unerwartetes Reparaturergebnis.'}
 $files=@($Result.Files|Where-Object {$_})
 $changed=$files.Count -gt 0
 [pscustomobject]@{
  Title=(Get-CoopText RepairFiles)
  Heading=$(if($changed){Get-CoopText RepairDone}else{Get-CoopText RepairHealthy})
  Summary=$(if($files.Count -eq 1){Get-CoopText RepairOneFile}elseif($changed){Get-CoopText RepairCount -Values @($files.Count)}else{Get-CoopText RepairNoChanges})
  Preservation=(Get-CoopText RepairPreserved)
  Files=$files
  BackupDirectory=[string]$Result.BackupDirectory
  Changed=$changed
 }
}

function New-CoopRepairResultDialog {
 param([Parameter(Mandatory)]$Result)
 Add-Type -AssemblyName System.Windows.Forms,System.Drawing
 $model=Get-CoopRepairPresentation $Result
 $dialog=[Windows.Forms.Form]::new()
 $dialog.Text=$model.Title;$dialog.ClientSize=[Drawing.Size]::new(580,294)
 $dialog.FormBorderStyle='FixedDialog';$dialog.StartPosition='CenterParent'
 $dialog.MaximizeBox=$false;$dialog.MinimizeBox=$false;$dialog.ShowInTaskbar=$false
 $dialog.BackColor=[Drawing.Color]::FromArgb(22,22,26)
 $dialog.ForeColor=[Drawing.Color]::FromArgb(242,242,244)
 $dialog.Font=[Drawing.Font]::new('Segoe UI',10)
 $icon=[Windows.Forms.Label]::new();$icon.Text=[char]0x2713
 $icon.Location='24,22';$icon.Size='40,40';$icon.Font=[Drawing.Font]::new('Segoe UI',22)
 $icon.ForeColor=[Drawing.Color]::FromArgb(103,211,151);$dialog.Controls.Add($icon)
 $heading=[Windows.Forms.Label]::new();$heading.Text=$model.Heading
 $heading.Location='76,27';$heading.Size='480,36';$heading.Font=[Drawing.Font]::new('Segoe UI Semibold',16)
 $dialog.Controls.Add($heading)
 $summary=[Windows.Forms.Label]::new();$summary.Text=$model.Summary
 $summary.Location='28,83';$summary.Size='524,48';$dialog.Controls.Add($summary)
 $preserved=[Windows.Forms.Label]::new();$preserved.Text=$model.Preservation
 $preserved.Location='28,144';$preserved.Size='524,46'
 $preserved.ForeColor=[Drawing.Color]::FromArgb(181,184,191);$dialog.Controls.Add($preserved)
 $details=[Windows.Forms.TextBox]::new();$details.Location='28,286';$details.Size='524,174'
 $details.Multiline=$true;$details.ReadOnly=$true;$details.ScrollBars='Both';$details.WordWrap=$false
 $details.BackColor=[Drawing.Color]::FromArgb(31,31,36);$details.ForeColor=$dialog.ForeColor
 $details.BorderStyle='FixedSingle';$details.Visible=$false;$details.AccessibleName=Get-CoopText RepairDetails
 $lines=@((Get-CoopText RepairFiles)+':')
 if($model.Files.Count){$lines+=@($model.Files|ForEach-Object {'  '+$_})}else{$lines+=(Get-CoopText RepairNoChanges)}
 $lines+='';$lines+=$(if($model.BackupDirectory){(Get-CoopText RepairBackup)+': '+$model.BackupDirectory}else{Get-CoopText RepairNoBackup})
 $details.Text=$lines -join [Environment]::NewLine;$dialog.Controls.Add($details)
 $toggle=[Windows.Forms.Button]::new();$toggle.Text=Get-CoopText RepairShowDetails
 $toggle.Location='28,225';$toggle.Size='148,34';$toggle.FlatStyle='Flat'
 $toggle.BackColor=[Drawing.Color]::FromArgb(32,32,37);$dialog.Controls.Add($toggle)
 $toggle.Tag=@{Form=$dialog;Details=$details}
 $toggle.Add_Click({
  $expanded=!$this.Tag.Details.Visible
  $this.Tag.Details.Visible=$expanded
  $this.Tag.Form.ClientSize=[Drawing.Size]::new(580,$(if($expanded){486}else{294}))
  $this.Text=Get-CoopText $(if($expanded){'RepairHideDetails'}else{'RepairShowDetails'})
 })
 if($model.BackupDirectory){
  $open=[Windows.Forms.Button]::new();$open.Text=Get-CoopText RepairOpenBackup
  $open.Location='186,225';$open.Size='198,34';$open.FlatStyle='Flat'
  $open.BackColor=$toggle.BackColor;$open.Tag=$model.BackupDirectory
  $open.Add_Click({
   if(Test-Path -LiteralPath ([string]$this.Tag) -PathType Container){
    $info=[Diagnostics.ProcessStartInfo]::new();$info.FileName=[string]$this.Tag;$info.UseShellExecute=$true
    [void][Diagnostics.Process]::Start($info)
   }
  });$dialog.Controls.Add($open)
 }
 $close=[Windows.Forms.Button]::new();$close.Text=Get-CoopText RepairClose
 $close.Location='410,225';$close.Size='142,34';$close.FlatStyle='Flat'
 $close.BackColor=[Drawing.Color]::FromArgb(235,125,30);$close.ForeColor=[Drawing.Color]::Black
 $close.DialogResult='OK';$dialog.Controls.Add($close);$dialog.AcceptButton=$close;$dialog.CancelButton=$close
 [pscustomobject]@{Form=$dialog;Model=$model;Details=$details;Toggle=$toggle}
}

function Show-CoopRepairResultDialog {
 param([Parameter(Mandatory)]$Result,$Owner)
 $view=New-CoopRepairResultDialog $Result
 try{
  if($Owner){[void]$view.Form.ShowDialog($Owner)}else{[void]$view.Form.ShowDialog()}
 }finally{
  foreach($control in $view.Form.Controls){if($control -is [Windows.Forms.Label] -and $control.Font -ne $view.Form.Font){$control.Font.Dispose()}}
  $view.Form.Font.Dispose();$view.Form.Dispose()
 }
}
