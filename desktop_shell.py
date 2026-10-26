"""User-requested desktop shortcuts and login startup, without privileged services."""
import os,sys,plistlib,subprocess,shlex
from pathlib import Path

def app_bundle():
    if sys.platform=='darwin' and getattr(sys,'frozen',False):
        return next((p for p in Path(sys.executable).resolve().parents if p.suffix=='.app'),None)
    return None

def launch_args(autostart=False):
    bundle=app_bundle()
    if bundle:args=['/usr/bin/open',str(bundle),'--args']
    elif getattr(sys,'frozen',False):args=[str(Path(sys.executable).resolve())]
    else:args=[sys.executable,str(Path(__file__).with_name('agent.py').resolve())]
    return args+(['--autostart'] if autostart else [])

def desktop_entry(autostart=False):
    # Desktop Entry quoting differs from shell quoting; escape field-code percent.
    def quote(v):return '"'+v.replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$').replace('%','%%')+'"'
    return '[Desktop Entry]\nType=Application\nName=ZDesk\nComment=Visible remote access companion\nTerminal=false\nExec='+' '.join(quote(v) for v in launch_args(autostart))+'\nCategories=Network;RemoteAccess;\n'

def startup(enabled):
    if sys.platform=='darwin':
        path=Path.home()/'Library/LaunchAgents/com.zdesk.companion.plist'
        if not enabled:path.unlink(missing_ok=True);return
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(plistlib.dumps({'Label':'com.zdesk.companion','ProgramArguments':launch_args(True),'RunAtLoad':True,'ProcessType':'Interactive'}));path.chmod(0o600)
    elif sys.platform.startswith('linux'):
        path=Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'autostart/zdesk.desktop'
        if not enabled:path.unlink(missing_ok=True);return
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(desktop_entry(True));path.chmod(0o700)
    else:raise RuntimeError('This platform does not support login startup.')

def desktop_shortcut():
    if sys.platform=='darwin':
        bundle=app_bundle()
        if not bundle:raise RuntimeError('Move the packaged ZDesk.app into Applications first.')
        path=Path.home()/'Desktop/ZDesk.app'
        if path.exists() or path.is_symlink():raise RuntimeError('A ZDesk desktop entry already exists.')
        path.symlink_to(bundle,target_is_directory=True)
    elif sys.platform.startswith('linux'):
        result=subprocess.run(['xdg-user-dir','DESKTOP'],capture_output=True,text=True,timeout=5,check=True)
        path=Path(result.stdout.strip())/'ZDesk.desktop';path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(desktop_entry());path.chmod(0o700)
    else:raise RuntimeError('No desktop shortcut available.')
