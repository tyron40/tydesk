"""Public browser companion page and credential-free Windows source download."""
import os
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from flask import render_template, send_file, abort
import download_catalog
ROOT=Path(__file__).resolve().parent
FILES=['desktop_runtime.py','desktop_shell.py','desktop_probe.py','camera_capture.py','remote_input.py','agent.py','native_shell.py','audio_capture.py','file_exchange.py','extensions.py','local_settings.py',
       'requirements.txt','start-agent.ps1','install-startup.ps1','uninstall-startup.ps1','LICENSE']

def windows_exe():
    current=ROOT/'downloads'/'ZDesk.exe'
    return current if current.is_file() else ROOT/'downloads'/'TyDesk.exe'

def install(app, durable_devices=None):
    from calculator_routes import install as install_calculator
    install_calculator(app)
    durable=bool(os.environ.get('TYDESK_REGISTRY_URL')) if durable_devices is None else durable_devices
    @app.get('/companion')
    def companion():return render_template('companion.html',windows_app_available=windows_exe().is_file(),android_app_available=(ROOT/'downloads'/'ZDesk-Android.apk').is_file(),durable_devices=durable)
    @app.get('/calculator')
    def system_calculator():return render_template('calculator.html')
    @app.get('/downloads')
    def all_downloads():return render_template('downloads.html',downloads=download_catalog.available(ROOT))
    @app.get('/download/<target>')
    def platform_download(target):
        entry=next((e for e in download_catalog.CATALOG if e['id']==target),None)
        if entry is None:abort(404)
        file=ROOT/'downloads'/entry['filename']
        if not file.is_file():abort(503,description='This platform build has not been published yet.')
        return send_file(file,mimetype=entry['mimetype'],as_attachment=True,download_name=entry['filename'])
    @app.get('/api/downloads')
    def download_info():
        exe=windows_exe()
        return {'windows_app_available':exe.is_file(),'filename':'ZDesk.exe' if exe.is_file() else 'ZDesk-Windows-Companion.zip','platforms':download_catalog.available(ROOT)}
    @app.get('/download/windows')
    def download():
        exe=windows_exe()
        if exe.is_file():return send_file(exe,mimetype='application/vnd.microsoft.portable-executable',as_attachment=True,download_name='ZDesk.exe')
        return download_source()
    @app.get('/download/android')
    def download_android():
        apk=ROOT/'downloads'/'ZDesk-Android.apk'
        if not apk.is_file():abort(503,description='The Android APK is still building. Try again shortly.')
        return send_file(apk,mimetype='application/vnd.android.package-archive',as_attachment=True,download_name='ZDesk-Android.apk')
    @app.get('/download/windows-source')
    def download_source():
        payload=BytesIO()
        with ZipFile(payload,'w',ZIP_DEFLATED) as archive:
            for name in FILES:
                content=(ROOT/name).read_bytes()
                if name=='agent.py':
                    content=content.replace(b'http://127.0.0.1:8787',b'https://zdesk-nnym.onrender.com')
                archive.writestr('ZDesk-Companion/'+name,content)
            archive.writestr('ZDesk-Companion/Start-ZDesk.cmd',
                '@echo off\r\ncd /d "%~dp0"\r\npowershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-agent.ps1"\r\npause\r\n')
            archive.writestr('ZDesk-Companion/READ-ME.txt',
                'ZDesk Windows companion (Python source package)\r\n\r\n'
                '1. Install Python 3.12 or 3.13 from https://www.python.org/downloads/windows/ including the launcher and Tcl/Tk.\r\n'
                '2. Extract ALL files into a permanent folder. Do not run from inside the ZIP.\r\n'
                '3. Double-click Start-ZDesk.cmd. First launch downloads Python dependencies.\r\n'
                '4. Create a pairing code at https://zdesk-nnym.onrender.com and paste it into the companion.\r\n'
                '5. Enable the permissions you want and press Start / reconnect.\r\n\r\n'
                'Terminal setup: from regular PowerShell in this folder, run .\\start-agent.ps1 -TerminalSetup.\r\n'
                'Choose sharing features, enter the masked ZDesk code, then type CONNECT to start a visible session.\r\n'
                'Add -RememberPairing to reuse the Windows-protected device token next time.\r\n\r\n'
                'Optional sign-in startup: enable Remember this device, then run install-startup.ps1.\r\n'
                'Remove startup with uninstall-startup.ps1. Disconnect or Quit ZDesk stops sharing. With tray mode enabled, closing the window keeps access available.\r\n'
                'This package is source code, not a standalone EXE or signed installer.\r\n')
        payload.seek(0)
        return send_file(payload,mimetype='application/zip',as_attachment=True,download_name='ZDesk-Windows-Companion.zip')

