"""Explicit local terminal-to-tray handoff; no startup task or hidden capture."""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ENV_KEY = 'ZDESK_BACKGROUND_HANDOFF'
FEATURES = {'control', 'audio', 'microphone', 'camera', 'files'}
SERVER = 'https://zdesk-nnym.onrender.com'


def _validate(value):
    if not isinstance(value, dict) or value.get('version') != 1:
        raise ValueError('Invalid ZDesk background request.')
    stamp = value.get('created')
    if type(stamp) not in (int, float) or not 0 <= time.time()-stamp <= 45:
        raise ValueError('Expired ZDesk background request.')
    selected = value.get('selected')
    if not isinstance(selected, list) or not all(isinstance(x,str) and x in FEATURES for x in selected):
        raise ValueError('Invalid ZDesk sharing selection.')
    saved, code = value.get('saved'), value.get('code')
    if saved is not None and (not isinstance(saved,dict) or saved.get('url')!=SERVER or
        not all(isinstance(saved.get(k),str) and 0<len(saved[k])<=512 for k in ('id','token'))):
        raise ValueError('Invalid ZDesk saved pairing.')
    if not isinstance(code,str) or len(code)>200 or (saved is None and not code):
        raise ValueError('Missing ZDesk pairing code.')
    if type(value.get('remember')) is not bool or not isinstance(value.get('ready'),str):
        raise ValueError('Invalid ZDesk background options.')
    return value


def encode_handoff(value):
    import win32crypt
    data = json.dumps(_validate(value)).encode('utf-8')
    return base64.b64encode(win32crypt.CryptProtectData(data,'ZDesk local background handoff',None,None,None,0)).decode('ascii')


def consume_handoff():
    import win32crypt
    encoded = os.environ.pop(ENV_KEY, '')
    if not encoded or len(encoded)>32768:
        raise ValueError('Missing ZDesk local background authorization.')
    blob = base64.b64decode(encoded,validate=True)
    return _validate(json.loads(win32crypt.CryptUnprotectData(blob,None,None,None,0)[1]))


def acknowledge(path, ok):
    target=Path(path)
    pending=target.with_suffix('.tmp')
    pending.write_text(json.dumps({'ok':bool(ok)}),encoding='utf-8')
    pending.replace(target)


def launch(setup, *, saved=None, remember=False, write=print):
    """Start a separate GUI process only after the local Yes/No consent."""
    if sys.platform!='win32' or getattr(sys,'frozen',False):
        raise RuntimeError('Background handoff requires the Windows source launcher.')
    pythonw=Path(sys.executable).with_name('pythonw.exe')
    if not pythonw.is_file():
        raise RuntimeError('The Python installation is missing pythonw.exe.')
    code,selected=setup
    with tempfile.TemporaryDirectory(prefix='zdesk-background-') as folder:
        ready=Path(folder)/'ready.json'
        env=dict(os.environ)
        env[ENV_KEY]=encode_handoff(dict(version=1,created=time.time(),code=code,
            selected=sorted(selected),saved=saved,remember=remember,ready=str(ready)))
        worker=None;accepted=False
        try:
            worker=subprocess.Popen([str(pythonw),str(Path(__file__).with_name('agent.py')),'--background-session'],
                env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                close_fds=True,creationflags=0x00000008 | 0x00000200)
            deadline=time.monotonic()+16
            while time.monotonic()<deadline:
                if ready.exists():
                    result=json.loads(ready.read_text(encoding='utf-8'))
                    if result.get('ok') is True and worker.poll() is None:
                        accepted=True
                        write('ZDesk background companion started. You may close PowerShell.')
                        write('Use the visible ZDesk tray icon to Open, Disconnect or Quit.')
                        return True
                    break
                if worker.poll() is not None:break
                time.sleep(.1)
            raise RuntimeError('ZDesk background companion could not confirm its tray controls. No background session was left running.')
        finally:
            env.pop(ENV_KEY,None)
            if worker is not None and not accepted:
                if worker.poll() is None:worker.terminate();worker.wait(timeout=5)
