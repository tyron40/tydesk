"""Short-lived, authenticated requests to remove only the connected companion."""
import secrets
import time
from flask import request, jsonify, abort


def install(app, admin, device, devices, lock, audit):
    def current(d):
        job = d.get('removal')
        if job and ((job['state'] == 'pending' and time.time() > job['expires']) or (job['state'] == 'confirmation_required' and time.time() > job['expires']+120)):
            job['state'] = 'expired'
        return job

    @app.post('/api/devices/<identity>/uninstall')
    @admin
    def request_uninstall(identity):
        with lock:
            d = devices.get(identity)
            if not d or time.time() - d['seen'] >= 8 or not d['control'] or not d.get('removal_supported'):
                abort(409, description='Update the companion and enable local control while connected.')
            job = current(d)
            if job and job['state'] in ('pending', 'confirmation_required'):
                return jsonify(job)
            d['removal'] = dict(id=secrets.token_hex(16), state='pending', expires=time.time()+30)
            audit(identity, 'companion uninstall requested')
            return jsonify(d['removal']), 202

    @app.route('/api/devices/<identity>/removal', methods=['GET', 'POST'])
    def removal(identity):
        with lock:
            d = device(identity)
            job = current(d)
            if request.method == 'GET':
                if not job or job['state'] != 'pending' or not d['control'] or time.time()-d['seen'] >= 8:
                    return jsonify(None)
                job['state'] = 'confirmation_required'
                return jsonify(job)
            body = request.get_json(silent=True)
            if not isinstance(body, dict) or not job or body.get('id') != job['id']:
                abort(400)
            if job['state'] != 'confirmation_required' or body.get('state') not in ('cancelled', 'removal_started', 'failed'):
                abort(400)
            job['state'] = body['state']
            audit(identity, 'companion uninstall ' + job['state'])
            return '', 204
