"""Authenticated, ephemeral camera frames; local sharing permission is required."""
import time
from flask import request, abort, Response


def install(app, admin, device, devices, lock):
    @app.post('/api/devices/<identity>/camera')
    def upload_camera(identity):
        with lock:
            d = device(identity)
            if not d.get('camera') or time.time()-d['seen'] >= 8:
                abort(409)
            if request.mimetype != 'image/jpeg':
                abort(415)
            frame = request.get_data()
            if len(frame)>2*1024*1024:
                abort(413)
            if not frame.startswith(b'\xff\xd8') or not frame.endswith(b'\xff\xd9'):
                abort(400)
            d['camera_frame'] = frame
            d['camera_seen'] = time.time()
        return '', 204

    @app.get('/api/devices/<identity>/camera')
    @admin
    def download_camera(identity):
        with lock:
            d = devices.get(identity)
            if (not d or not d.get('camera') or time.time()-d['seen'] >= 8
                    or time.time()-d.get('camera_seen',0) >= 8 or not d.get('camera_frame')):
                abort(404)
            return Response(d['camera_frame'], mimetype='image/jpeg')
