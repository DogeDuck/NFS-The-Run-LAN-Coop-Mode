' GUI launcher: no persistent CMD/PowerShell console next to the garage.
Option Explicit
Dim sh, fs, folder, command, fallback, launchError
Set sh = CreateObject("WScript.Shell")
Set fs = CreateObject("Scripting.FileSystemObject")
folder = fs.GetParentFolderName(WScript.ScriptFullName)
command = " -NoProfile -ExecutionPolicy Bypass -File " & Chr(34) & folder & "\Start-GarageWindow.ps1" & Chr(34)
sh.CurrentDirectory = folder
On Error Resume Next
sh.Run "pwsh.exe" & command, 0, False
launchError = Err.Number
If launchError <> 0 Then
    Err.Clear
    fallback = sh.ExpandEnvironmentStrings("%ProgramFiles%\PowerShell\7\pwsh.exe")
    If fs.FileExists(fallback) Then
        sh.Run Chr(34) & fallback & Chr(34) & command, 0, False
        launchError = Err.Number
    End If
End If
If launchError <> 0 Then MsgBox "PowerShell 7 is missing or the garage could not start." & vbCrLf & "PowerShell 7 fehlt oder die Garage konnte nicht gestartet werden.", 48, "The Run Co-op / Koop - Garage"
