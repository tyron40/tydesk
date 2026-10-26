"""Saved enrollment: Windows DPAPI, macOS Keychain, or Linux secure desktop keyring."""
import json, os,sys
from pathlib import Path
ROOT=Path(os.environ.get('LOCALAPPDATA',str(Path.home()))) / 'ZDesk'

def save(config):
    if os.name!='nt':
        import desktop_runtime
        return desktop_runtime.secure_save(json.dumps(config))
    import win32crypt
    ROOT.mkdir(parents=True,exist_ok=True)
    blob=win32crypt.CryptProtectData(json.dumps(config).encode(),'ZDesk enrollment',None,None,None,0)
    temp=ROOT/'enrollment.tmp';temp.write_bytes(blob);temp.replace(ROOT/'enrollment.dat')

LEGACY_ROOT=ROOT.with_name('TyDesk')

def load():
    if os.name!='nt':
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
        import desktop_runtime
        return desktop_runtime.secure_forget()
    (ROOT/'enrollment.dat').unlink(missing_ok=True)
    (LEGACY_ROOT/'enrollment.dat').unlink(missing_ok=True)
