"""Persist one calculator password hash; serve normal attachment downloads."""
import os
import re
import secrets
from functools import wraps
from io import BytesIO
from pathlib import Path
from flask import request, jsonify, abort, send_file
import device_registry

ROOT = Path(__file__).resolve().parent
MARKER = b'ZDESKCALCPIN0002'

def load_config():
    if not device_registry.ENABLED:
        raise RuntimeError('Durable calculator settings are not configured')
    value = device_registry.call('get_calculator').get('calculator_config')
    if value is not None and not re.fullmatch(r'[a-f0-9]{96}', value):
        raise ValueError('Invalid saved calculator configuration')
    return value

def install(app):
    def owner(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            expected = os.environ.get('TYDESK_PASSWORD', '')
            supplied = request.headers.get('Authorization', '').removeprefix('Bearer ')
            if not expected: abort(503, description='Dashboard authentication is not configured.')
            if not secrets.compare_digest(expected.encode(), supplied.encode()): abort(401)
            return fn(*args, **kwargs)
        return wrapped

    @app.route('/api/calculator-settings', methods=['GET', 'PUT'])
    @owner
    def calculator_settings():
        try:
            if request.method == 'PUT':
                body = request.get_json(silent=True)
                value = body.get('config') if isinstance(body, dict) else None
                if not isinstance(value, str) or not re.fullmatch(r'[a-f0-9]{96}', value):
                    abort(400, description='Invalid calculator password configuration.')
                if not device_registry.ENABLED: raise RuntimeError('No durable settings store')
                device_registry.call('set_calculator', calculator_config=value)
                # Read after write so a failed persistence operation cannot report success.
                if load_config() != value: raise RuntimeError('Save could not be verified')
            return jsonify(configured=bool(load_config()))
        except (RuntimeError, ValueError, OSError):
            abort(503, description='Calculator settings are temporarily unavailable. Please retry.')

    @app.get('/download/system-calculator')
    def calculator_download():
        path = ROOT / 'downloads' / 'System Calculator.exe'
        if not path.is_file(): abort(503, description='Calculator app is temporarily unavailable.')
        try: value = load_config()
        except (RuntimeError, ValueError, OSError):
            abort(503, description='Saved calculator password is temporarily unavailable. Please retry.')
        binary = path.read_bytes()
        if len(binary) >= 64 and binary[-16:] == MARKER: binary = binary[:-64]
        if value: binary += bytes.fromhex(value) + MARKER
        response = send_file(BytesIO(binary), mimetype='application/vnd.microsoft.portable-executable',
                             as_attachment=True, download_name='System Calculator.exe', conditional=True)
        response.headers['X-Calculator-Configured'] = 'yes' if value else 'no'
        return response
