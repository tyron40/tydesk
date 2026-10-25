"""Public browser companion page and credential-free Windows source download."""
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from flask import render_template, send_file
ROOT=Path(__file__).resolve().parent
FILES=['agent.py','audio_capture.py','file_exchange.py','extensions.py','local_settings.py',
       'requirements.txt','start-agent.ps1','install-startup.ps1','uninstall-startup.ps1','LICENSE']

def install(app):
    @app.get('/companion')
    def companion():return render_template('companion.html')
    @app.get('/download/windows')
    def download():
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
                'Remove startup with uninstall-startup.ps1. Close the visible app to stop sharing.\r\n'
                'This package is source code, not a standalone EXE or signed installer.\r\n')
        payload.seek(0)
        return send_file(payload,mimetype='application/zip',as_attachment=True,download_name='TyDesk-Windows-Companion.zip')
