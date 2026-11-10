"""Saved enrollment: Windows DPAPI, macOS Keychain, or Linux secure desktop keyring."""
import json, os,sys
from pathlib import Path
ROOT=Path(os.environ.get('LOCALAPPDATA',str(Path.home()))) / 'ZDesk'

def save(config):
    if os.name!='nt':
        import desktop_runtime
        desktop_runtime.secure_save(json.dumps(config))
        (ROOT/'enrollment-forgotten').unlink(missing_ok=True)
        return
    import win32crypt
    ROOT.mkdir(parents=True,exist_ok=True)
    blob=win32crypt.CryptProtectData(json.dumps(config).encode(),'ZDesk enrollment',None,None,None,0)
    temp=ROOT/'enrollment.tmp';temp.write_bytes(blob);temp.replace(ROOT/'enrollment.dat')

LEGACY_ROOT=ROOT.with_name('TyDesk')

def load():
    if os.name!='nt':
        if (ROOT/'enrollment-forgotten').exists():return None
        import desktop_runtime
        value=desktop_runtime.secure_load()
        return json.loads(value) if value else None
    path=ROOT/'enrollment.dat'
    if not path.exists():
        legacy=LEGACY_ROOT/'enrollment.dat'
        if not legacy.exists():return None
        path=legacy
    if os.name!='nt': raise RuntimeError('Saved enrollment requires Windows DPAPI.')
    import win32crypt
    return json.loads(win32crypt.CryptUnprotectData(path.read_bytes(),None,None,None,0)[1])

def forget():
    if os.name!='nt':
        # Non-secret tombstone prevents restoring stale enrollment even if the
        # encrypted OS keyring is locked. A successful new opt-in save clears it.
        ROOT.mkdir(parents=True,exist_ok=True)
        (ROOT/'enrollment-forgotten').touch(mode=0o600)
        import desktop_runtime
        try:desktop_runtime.secure_forget()
        except Exception:pass
        return
    (ROOT/'enrollment.dat').unlink(missing_ok=True)
    (LEGACY_ROOT/'enrollment.dat').unlink(missing_ok=True)


def save_terminal(config):
    """Remember only the device credential for explicit terminal launches."""
    if os.name != 'nt':
        raise RuntimeError('Remembering terminal pairing requires Windows DPAPI.')
    import win32crypt
    values = {key: config[key] for key in ('id', 'token', 'url')}
    ROOT.mkdir(parents=True, exist_ok=True)
    blob = win32crypt.CryptProtectData(json.dumps(values).encode(), 'ZDesk terminal enrollment', None, None, None, 0)
    temp = ROOT / 'enrollment-terminal.tmp'
    temp.write_bytes(blob)
    temp.replace(ROOT / 'enrollment-terminal.dat')


def load_terminal():
    if os.name != 'nt':
        raise RuntimeError('Remembering terminal pairing requires Windows DPAPI.')
    path = ROOT / 'enrollment-terminal.dat'
    if not path.exists():
        return None
    import win32crypt
    values = json.loads(win32crypt.CryptUnprotectData(path.read_bytes(), None, None, None, 0)[1])
    if not isinstance(values, dict) or not all(isinstance(values.get(k), str) and values[k] for k in ('id', 'token', 'url')):
        raise ValueError('Invalid saved terminal enrollment.')
    return values


def forget_terminal():
    (ROOT / 'enrollment-terminal.dat').unlink(missing_ok=True)
