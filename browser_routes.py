"""Public browser companion page and credential-free Windows source download."""
import os
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from flask import render_template, send_file
ROOT=Path(__file__).resolve().parent
FILES=['agent.py','native_shell.py','audio_capture.py','file_exchange.py','extensions.py','local_settings.py',
       'requirements.txt','start-agent.ps1','install-startup.ps1','uninstall-startup.ps1','LICENSE']

def install(app):
    @app.get('/companion')
    def companion():return render_template('companion.html',windows_app_available=(ROOT/'downloads'/'TyDesk.exe').is_file(),durable_devices=bool(os.environ.get('TYDESK_REGISTRY_URL')))
    @app.get('/api/downloads')
    def download_info():
        exe=ROOT/'downloads'/'TyDesk.exe'
        return {'windows_app_available':exe.is_file(),'filename':'TyDesk.exe' if exe.is_file() else 'TyDesk-Windows-Companion.zip'}
    @app.get('/download/windows')
    def download():
        exe=ROOT/'downloads'/'TyDesk.exe'
        if exe.is_file():return send_file(exe,mimetype='application/vnd.microsoft.portable-executable',as_attachment=True,download_name='TyDesk.exe')
        return download_source()
    @app.get('/download/windows-source')
    def download_source():
        payload=BytesIO()
        with ZipFile(payload,'w',ZIP_DEFLATED) as archive:
            for name in FILES:
                content=(ROOT/name).read_bytes()
                if name=='agent.py':
                    content=content.replace(b'http://127.0.0.1:8787',b'https://tydesk-broker.onrender.com')
                archive.writestr('TyDesk-Companion/'+name,content)
            archive.writestr('TyDesk-Companion/Start-TyDesk.cmd',
                '@echo off\r\ncd /d "%~dp0"\r\npowershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-agent.ps1"\r\npause\r\n')
            archive.writestr('TyDesk-Companion/READ-ME.txt',
                'TyDesk Windows companion (Python source package)\r\n\r\n'
                '1. Install Python 3.12 or 3.13 from https://www.python.org/downloads/windows/ including the launcher and Tcl/Tk.\r\n'
                '2. Extract ALL files into a permanent folder. Do not run from inside the ZIP.\r\n'
                '3. Double-click Start-TyDesk.cmd. First launch downloads Python dependencies.\r\n'
                '4. Create a pairing code at https://tydesk-broker.onrender.com and paste it into the companion.\r\n'
                '5. Enable the permissions you want and press Start / reconnect.\r\n\r\n'
                'Optional sign-in startup: enable Remember this device, then run install-startup.ps1.\r\n'
                'Remove startup with uninstall-startup.ps1. Disconnect or Quit TyDesk stops sharing. With tray mode enabled, closing the window keeps access available.\r\n'
                'This package is source code, not a standalone EXE or signed installer.\r\n')
        payload.seek(0)
        return send_file(payload,mimetype='application/zip',as_attachment=True,download_name='TyDesk-Windows-Companion.zip')
