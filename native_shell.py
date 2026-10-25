"""Explicit user actions for Windows shortcuts and sign-in startup."""
import os,sys,subprocess
from pathlib import Path

def remove_companion():
    """Recycle this portable executable after it exits; never delete user folders."""
    if os.name!='nt' or not getattr(sys,'frozen',False):
        raise RuntimeError('Automatic removal is available only in the packaged Windows app.')
    startup(False)
    import win32com.client
    shell=win32com.client.Dispatch('WScript.Shell')
    for name in ('ZDesk.lnk','TyDesk.lnk'):
        (Path(shell.SpecialFolders('Desktop'))/name).unlink(missing_ok=True)
    script="""$ErrorActionPreference='Stop'
Wait-Process -Id ([int]$env:ZDESK_REMOVE_PID) -Timeout 45 -ErrorAction SilentlyContinue
if (Get-Process -Id ([int]$env:ZDESK_REMOVE_PID) -ErrorAction SilentlyContinue) { exit 1 }
Add-Type -AssemblyName Microsoft.VisualBasic
[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($env:ZDESK_REMOVE_EXE, [Microsoft.VisualBasic.FileIO.UIOption]::AllDialogs, [Microsoft.VisualBasic.FileIO.RecycleOption]::SendToRecycleBin)
"""
    env={**os.environ,'ZDESK_REMOVE_PID':str(os.getpid()),'ZDESK_REMOVE_EXE':str(Path(sys.executable).resolve())}
    subprocess.Popen(['powershell.exe','-NoProfile','-Command',script],env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.DETACHED_PROCESS,close_fds=True)

def target():
    if getattr(sys,'frozen',False):return Path(sys.executable),'--autostart'
    return Path(sys.executable).with_name('pythonw.exe'),'"'+str(Path(__file__).with_name('agent.py'))+'" --autostart'

def desktop_shortcut():
    if os.name!='nt':raise RuntimeError('Windows only')
    import win32com.client
    shell=win32com.client.Dispatch('WScript.Shell')
    shortcut=shell.CreateShortcut(str(Path(shell.SpecialFolders('Desktop'))/'ZDesk.lnk'))
    exe,args=target();shortcut.TargetPath=str(exe);shortcut.Arguments=args.replace(' --autostart','').replace('--autostart','')
    shortcut.WorkingDirectory=str(exe.parent);shortcut.Description='ZDesk remote desktop companion'
    shortcut.IconLocation=str(exe)+',0';shortcut.Save()

def startup(enabled):
    if os.name!='nt':raise RuntimeError('Windows only')
    exe,args=target();env={**os.environ,'TYDESK_APP_EXE':str(exe),'TYDESK_APP_ARGS':args}
    if enabled:
        script='''$ErrorActionPreference='Stop'
$user=[System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$action=New-ScheduledTaskAction -Execute $env:TYDESK_APP_EXE -Argument $env:TYDESK_APP_ARGS -WorkingDirectory (Split-Path $env:TYDESK_APP_EXE)
$trigger=New-ScheduledTaskTrigger -AtLogOn -User $user
$principal=New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero)
Unregister-ScheduledTask -TaskName 'TyDesk Remote Access Companion' -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName 'ZDesk Remote Access Companion' -Description 'Visible ZDesk companion; enabled by the local user.' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
'''
    else:script="Unregister-ScheduledTask -TaskName 'TyDesk Remote Access Companion' -Confirm:$false -ErrorAction SilentlyContinue; Unregister-ScheduledTask -TaskName 'ZDesk Remote Access Companion' -Confirm:$false -ErrorAction SilentlyContinue"
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],env=env,capture_output=True,text=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:raise RuntimeError(result.stderr.strip()[:300] or 'Windows startup setup failed')
