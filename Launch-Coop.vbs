' Optional GUI entry point, without a persistent command window.
Option Explicit
Dim sh, fs, folder, arguments, fallback, launchError
Set sh = CreateObject("WScript.Shell")
Set fs = CreateObject("Scripting.FileSystemObject")
folder = fs.GetParentFolderName(WScript.ScriptFullName)
arguments = " -STA -NoProfile -ExecutionPolicy Bypass -File " & Chr(34) & folder & "\Start-CoopWindow.ps1" & Chr(34)
sh.CurrentDirectory = folder
On Error Resume Next
sh.Run "pwsh.exe" & arguments, 0, False
launchError = Err.Number
If launchError <> 0 Then
    Err.Clear
    fallback = sh.ExpandEnvironmentStrings("%ProgramFiles%\PowerShell\7\pwsh.exe")
    If fs.FileExists(fallback) Then
        sh.Run Chr(34) & fallback & Chr(34) & arguments, 0, False
        launchError = Err.Number
    End If
End If
If launchError <> 0 Then MsgBox "PowerShell 7 is missing or the launcher could not start." & vbCrLf & "PowerShell 7 fehlt oder der Launcher konnte nicht starten.", 48, "The Run Co-op / Koop"
