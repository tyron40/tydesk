"""TyDesk v2: persistent single-owner remote desktop broker."""
import os, secrets, time, threading, math, sqlite3, hashlib
from pathlib import Path
from collections import deque
from functools import wraps
from flask import Flask, request, jsonify, abort, render_template, Response
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 21 * 1024 * 1024
ADMIN = os.environ.get('TYDESK_PASSWORD', '')
if len(ADMIN) < 16:
    raise RuntimeError('Set TYDESK_PASSWORD to a unique password of at least 16 characters.')
lock = threading.RLock()
DATA = Path(os.environ.get('TYDESK_DATA', './data')).resolve()
DATA.mkdir(parents=True, exist_ok=True)
db = sqlite3.connect(DATA / 'tydesk.db', check_same_thread=False)
db.execute('CREATE TABLE IF NOT EXISTS devices (id TEXT PRIMARY KEY, token TEXT, name TEXT)')
db.execute('CREATE TABLE IF NOT EXISTS audit (time REAL, device TEXT, event TEXT)')
db.commit()
def audit(identity, event):
    db.execute('INSERT INTO audit VALUES (?,?,?)', (time.time(), identity, event))
    db.commit()
def fresh(token, name):
    return dict(token=token, name=name, seen=0, frame=b'', commands=deque(maxlen=50), control=False,
        audio=False, files=False, audio_chunks=deque(maxlen=8), audio_seq=0, share=[])
devices = {identity: fresh(token,name) for identity,token,name in db.execute('SELECT * FROM devices')}

pairings = {}
failed_auth = {}

def admin(fn):
    @wraps(fn)
    def wrapped(*a, **kw):
        supplied = request.headers.get('Authorization', '').removeprefix('Bearer ')
        # Bound invalid password attempts without retaining supplied credentials.
        with lock:
            now = time.monotonic(); peer = request.remote_addr or 'unknown'
            if len(failed_auth)>1000: failed_auth.clear()
            failures = failed_auth.setdefault(peer, deque(maxlen=20))
            while failures and now-failures[0]>60: failures.popleft()
            if len(failures)>=20: abort(429)
            if not secrets.compare_digest(supplied, ADMIN):
                failures.append(now); abort(401)
        return fn(*a, **kw)
    return wrapped

def device(identity):
    d = devices.get(identity)
    supplied = request.headers.get('Authorization', '').removeprefix('Bearer ')
    if not d or not secrets.compare_digest(hashlib.sha256(supplied.encode()).hexdigest(), d['token']): abort(401)
    return d

@app.after_request
def headers(response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' blob:; frame-ancestors 'none'"
    return response

@app.get('/')
def index(): return render_template('index.html')

@app.post('/api/pairing')
@admin
def pairing():
    with lock:
        now = time.time()
        for key in list(pairings):
            if pairings[key] < now: del pairings[key]
        if len(pairings)>=100: abort(429)
        code = secrets.token_urlsafe(18)
        pairings[code] = now + 300
    return jsonify(code=code, expires_in=300)

@app.post('/api/enroll')
def enroll():
    data = request.get_json()
    if not isinstance(data,dict): abort(400)
    with lock:
        if len(devices)>=100: abort(429)
        expires = pairings.pop(str(data.get('code', '')), 0)
        if expires < time.time(): abort(403)
        identity, token = secrets.token_hex(12), secrets.token_urlsafe(32)
        name = str(data.get('name', 'Windows PC'))[:80]
        digest = hashlib.sha256(token.encode()).hexdigest()
        devices[identity] = fresh(digest, name)
        db.execute('INSERT INTO devices VALUES (?,?,?)', (identity,digest,name)); db.commit()
        audit(identity, 'enrolled')
    return jsonify(id=identity, token=token)

@app.get('/api/devices')
@admin
def listing():
    with lock:
        return jsonify([dict(id=k, name=d['name'], online=time.time()-d['seen'] < 8,
            control=d['control'], audio=d['audio'], files=d['files']) for k,d in devices.items()])

@app.post('/api/devices/<identity>/frame')
def frame_upload(identity):
    with lock:
        d = device(identity)
        if request.mimetype != 'image/jpeg': abort(415)
        payload = request.get_data()
        if len(payload)>3*1024*1024: abort(413)
        d['frame'] = payload
        d['seen'] = time.time()
        d['control'] = request.headers.get('X-Allow-Control') == 'yes'
        d['audio'] = request.headers.get('X-Allow-Audio') == 'yes'
        d['files'] = request.headers.get('X-Allow-Files') == 'yes'
        if not d['audio']: d['audio_chunks'].clear()
        if not d['control']: d['commands'].clear()
    return '', 204

@app.get('/api/devices/<identity>/frame')
@admin
def frame_download(identity):
    with lock:
        d = devices.get(identity)
        if not d or time.time()-d['seen'] >= 8 or not d['frame']: abort(404)
        return Response(d['frame'], mimetype='image/jpeg')

@app.get('/api/devices/<identity>/commands')
def commands(identity):
    with lock:
        d = device(identity)
        result = [c for stamp,c in d['commands'] if time.time()-stamp < 2]
        d['commands'].clear()
        return jsonify(result if d['control'] else [])

@app.post('/api/devices/<identity>/commands')
@admin
def command(identity):
    c = request.get_json()
    if not isinstance(c, dict): abort(400)
    kind = c.get('type')
    if kind == 'click':
        try:
            x,y = float(c['x']),float(c['y'])
            if not all(math.isfinite(v) and 0 <= v <= 1 for v in (x,y)): abort(400)
        except (KeyError, ValueError, TypeError): abort(400)
        c = dict(type='click', x=x, y=y, button='right' if c.get('button')=='right' else 'left')
    elif kind == 'text':
        text = c.get('text')
        if not isinstance(text,str) or len(text)>500 or not text.isascii(): abort(400)
        c = dict(type='text', text=text)
    elif kind == 'key':
        if c.get('key') not in ['enter','tab','backspace','esc','up','down','left','right','space']: abort(400)
        c = dict(type='key', key=c['key'])
    elif kind == 'scroll':
        amount = c.get('amount')
        if not isinstance(amount, (int,float)) or not math.isfinite(amount) or amount == 0: abort(400)
        c = dict(type='scroll', amount=1 if amount>0 else -1)
    else: abort(400)
    with lock:
        d = devices.get(identity)
        if not d or not d['control'] or time.time()-d['seen'] >= 8: abort(409)
        d['commands'].append((time.time(),c))
    return '',204

@app.delete('/api/devices/<identity>')
@admin
def revoke(identity):
    with lock:
        devices.pop(identity,None)
        db.execute('DELETE FROM devices WHERE id=?',(identity,)); db.commit()
        audit(identity, 'revoked')
        purge_transfers(identity)
    return '',204

from extensions import install
purge_transfers = install(app, admin, device, devices, lock, DATA, audit)

@app.get('/api/audit')
@admin
def audit_log():
    with lock:
        rows = db.execute('SELECT time,device,event FROM audit ORDER BY time DESC LIMIT 200').fetchall()
        return jsonify([dict(time=t,device=d,event=e) for t,d,e in rows])

if __name__ == '__main__':
    from waitress import serve
    host = os.environ.get('TYDESK_HOST','127.0.0.1')
    print('TyDesk dashboard: http://' + host + ':8787')
    serve(app, host=host, port=int(os.environ.get('PORT', '8787')), threads=16)
