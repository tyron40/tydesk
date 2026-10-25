"""ZDesk v2: persistent single-owner remote desktop broker."""
import os, secrets, time, threading, math, sqlite3, hashlib
import device_registry
import connection_access
import remote_input
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
        audio=False, files=False, audio_chunks=deque(maxlen=8), audio_seq=0, share=[], protocol=1, cursor='default', audio_status={'state':'waiting','message':'Waiting for system audio'})
if device_registry.ENABLED:
    # Durable registry is authoritative. Never resurrect locally cached revocations.
    rows=device_registry.list_devices()
    db.execute('DELETE FROM devices')
    db.executemany('INSERT INTO devices VALUES (?,?,?)',[(d['id'],d['token'],d['name']) for d in rows]);db.commit()
devices = {identity: fresh(token,name) for identity,token,name in db.execute('SELECT * FROM devices')}

db.execute('CREATE TABLE IF NOT EXISTS connection_settings (id TEXT PRIMARY KEY, passcode_hash TEXT)')
if device_registry.ENABLED:
    passcode_hash=device_registry.get_passcode()
    db.execute("INSERT OR REPLACE INTO connection_settings VALUES ('primary',?)",(passcode_hash,));db.commit()
else:
    row=db.execute("SELECT passcode_hash FROM connection_settings WHERE id='primary'").fetchone()
    passcode_hash=row[0] if row else None
enrollment_gate=connection_access.EnrollmentGate()
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
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' blob:; media-src 'self' blob:; frame-ancestors 'none'"
    return response

@app.get('/')
def index(): return render_template('index.html',durable_devices=device_registry.ENABLED)

from browser_routes import install as install_browser
install_browser(app)

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

@app.route('/api/access-passcode',methods=['GET','PUT','DELETE'])
@admin
def access_passcode():
    global passcode_hash
    with lock:
        if request.method=='GET':return jsonify(enabled=bool(passcode_hash),minimum_length=16)
        encoded=None
        if request.method=='PUT':
            data=request.get_json(silent=True)
            try:encoded=connection_access.encode(data.get('passcode') if isinstance(data,dict) else None)
            except ValueError as e:abort(400,description=str(e))
        try:device_registry.set_passcode(encoded)
        except Exception:abort(503,description='Could not save connection settings. Try again shortly.')
        db.execute("INSERT OR REPLACE INTO connection_settings VALUES ('primary',?)",(encoded,));db.commit()
        passcode_hash=encoded
        audit('dashboard','connection passcode changed' if encoded else 'connection passcode disabled')
        return jsonify(enabled=bool(encoded),minimum_length=16)

@app.post('/api/enroll')
def enroll():
    data = request.get_json()
    if not isinstance(data,dict): abort(400)
    if not enrollment_gate.permit(request.remote_addr or 'unknown'):abort(429)
    with lock:
        if len(devices)>=100: abort(429)
        code=data.get('code','')
        if not isinstance(code,str) or not 1<=len(code)<=200:abort(403)
        expires = pairings.pop(code, 0)
        if expires < time.time() and not connection_access.verify(code,passcode_hash): abort(403)
        identity, token = secrets.token_hex(12), secrets.token_urlsafe(32)
        name = str(data.get('name', 'Windows PC'))[:80] or 'Computer'
        digest = hashlib.sha256(token.encode()).hexdigest()
        try:device_registry.register(identity,digest,name)
        except Exception:abort(503,description='Saved-device registry is temporarily unavailable. Try pairing again shortly.')
        devices[identity] = fresh(digest, name)
        db.execute('INSERT INTO devices VALUES (?,?,?)', (identity,digest,name)); db.commit()
        audit(identity, 'enrolled')
    return jsonify(id=identity, token=token)

@app.get('/api/devices')
@admin
def listing():
    with lock:
        return jsonify([dict(id=k, name=d['name'], online=time.time()-d['seen'] < 8,
            control=d['control'], audio=d['audio'], files=d['files'], protocol=d['protocol']) for k,d in devices.items()])

@app.post('/api/devices/<identity>/frame')
def frame_upload(identity):
    with lock:
        d = device(identity)
        if request.mimetype != 'image/jpeg': abort(415)
        payload = request.get_data()
        if len(payload)>3*1024*1024: abort(413)
        d['frame'] = payload
        d['seen'] = time.time()
        d['protocol']=2 if request.headers.get('X-TyDesk-Protocol')=='2' else 1
        cursor=request.headers.get('X-Remote-Cursor','default');d['cursor']=cursor if cursor in remote_input.CURSORS else 'default'
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
        return Response(d['frame'], mimetype='image/jpeg',headers={'X-Remote-Cursor':d['cursor']})

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
    payload=request.get_json()
    batch=payload.get('commands') if isinstance(payload,dict) and 'commands' in payload else [payload]
    if not isinstance(batch,list) or not 1<=len(batch)<=24:abort(400)
    try:batch=[remote_input.validate(c) for c in batch]
    except ValueError:abort(400)
    with lock:
        d=devices.get(identity)
        if not d or not d['control'] or time.time()-d['seen']>=8:abort(409)
        for c in batch:
            if c['type']=='release':d['commands'].clear()
            if c['type']=='move' and d['commands'] and d['commands'][-1][1]['type']=='move':d['commands'].pop()
            if len(d['commands'])>=49:
                d['commands'].clear();d['commands'].append((time.time(),{'type':'release'}))
            d['commands'].append((time.time(),c))
    return '',204

@app.delete('/api/devices/<identity>')
@admin
def revoke(identity):
    with lock:
        try:device_registry.revoke(identity)
        except Exception:abort(503,description='Cannot persist revocation while the registry is unavailable. Retry shortly.')
        devices.pop(identity,None)
        db.execute('DELETE FROM devices WHERE id=?',(identity,)); db.commit()
        audit(identity, 'revoked')
        purge_transfers(identity)
    return '',204

from extensions import install
purge_transfers = install(app, admin, device, devices, lock, DATA, audit)

@app.get('/api/registry-status')
@admin
def registry_status():return jsonify(durable_devices=device_registry.ENABLED)

@app.get('/api/audit')
@admin
def audit_log():
    with lock:
        rows = db.execute('SELECT time,device,event FROM audit ORDER BY time DESC LIMIT 200').fetchall()
        return jsonify([dict(time=t,device=d,event=e) for t,d,e in rows])

if __name__ == '__main__':
    from waitress import serve
    host = os.environ.get('TYDESK_HOST','127.0.0.1')
    print('ZDesk dashboard: http://' + host + ':8787')
    serve(app, host=host, port=int(os.environ.get('PORT', '8787')), threads=16)
