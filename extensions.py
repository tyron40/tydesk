"""Bounded audio buffer and explicit shared-folder file exchange."""
import base64, io, re, secrets, shutil, time, wave
from flask import request, jsonify, abort, Response
MAX_FILE = 20 * 1024 * 1024
MAX_TOTAL = 200 * 1024 * 1024

def safe_name(name):
    if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._ -]{0,119}',name):
        raise ValueError('Use a simple filename, up to 120 characters.')
    if name.endswith(('.', ' ')) or name.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}:
        raise ValueError('Reserved Windows filename.')
    return name

def install(app, admin, device, devices, lock, data_dir, audit):
    folder=data_dir/'transfers'; folder.mkdir(exist_ok=True)
    # Pending transfers are not resumed after a broker restart.
    for p in folder.glob('*.bin'): p.unlink()
    transfers={}
    def purge(identity=None):
        now=time.time()
        for key,t in list(transfers.items()):
            if (identity is not None and t['device']==identity) or now-t['created']>3600:
                (folder/(key+'.bin')).unlink(missing_ok=True); del transfers[key]
    def require(identity):
        d=devices.get(identity)
        if not d or time.time()-d['seen']>=8 or not d['files']: abort(409)
        return d
    def create(identity,direction,name,status):
        purge()
        if len(transfers)>=100 or sum(p.stat().st_size for p in folder.glob('*.bin'))>=MAX_TOTAL: abort(507)
        try: name=safe_name(name)
        except ValueError: abort(400)
        key=secrets.token_hex(16)
        t=dict(id=key,device=identity,direction=direction,name=name,status=status,created=time.time(),size=0)
        transfers[key]=t; audit(identity,'file '+direction+' requested')
        return key,t
    def transfer(identity,key):
        t=transfers.get(key)
        if not t or t['device']!=identity: abort(404)
        return t
    def store(key):
        # Stream to disk with explicit per-file and total quotas, even for chunked HTTP.
        path=folder/(key+'.bin'); size=0
        try:
            with path.open('wb') as f:
                while True:
                    chunk=request.stream.read(65536)
                    if not chunk: break
                    size+=len(chunk)
                    if size>MAX_FILE: abort(413)
                    if size+sum(p.stat().st_size for p in folder.glob('*.bin') if p!=path)>MAX_TOTAL: abort(507)
                    f.write(chunk)
        except BaseException:
            path.unlink(missing_ok=True); raise
        return size
    @app.get('/health')
    def health(): return jsonify(status='ok',service='tydesk',version=2)
    @app.post('/api/devices/<identity>/audio')
    def upload_audio(identity):
        with lock:
            d=device(identity)
            if not d['audio']: abort(409)
            payload=request.get_data()
            if len(payload)>100000: abort(413)
            try:
                with wave.open(io.BytesIO(payload),'rb') as w:
                    if w.getnchannels()!=2 or w.getsampwidth()!=2 or w.getframerate()!=24000 or w.getnframes()>12000: abort(400)
            except (wave.Error,EOFError): abort(400)
            d['audio_seq']+=1
            d['audio_chunks'].append((d['audio_seq'],time.time(),payload))
        return '',204
    @app.get('/api/devices/<identity>/audio')
    @admin
    def download_audio(identity):
        try: after=int(request.args.get('after','0'))
        except ValueError: abort(400)
        with lock:
            d=devices.get(identity)
            if not d or not d['audio'] or time.time()-d['seen']>=8: abort(409)
            return jsonify(chunks=[dict(seq=s,wav=base64.b64encode(b).decode()) for s,stamp,b in d['audio_chunks'] if s>after and time.time()-stamp<2])
    @app.post('/api/devices/<identity>/shares')
    def shares(identity):
        with lock:
            d=device(identity); payload=request.get_json()
            if not isinstance(payload,list) or len(payload)>200: abort(400)
            result=[]
            for entry in payload:
                try:
                    name=safe_name(entry['name']); size=entry['size']
                    if not isinstance(size,int) or not 0<=size<=MAX_FILE: raise ValueError()
                    result.append(dict(name=name,size=size))
                except (KeyError,TypeError,ValueError): abort(400)
            d['share']=result if d['files'] else []
        return '',204
    @app.get('/api/devices/<identity>/shares')
    @admin
    def list_shares(identity):
        with lock: return jsonify(require(identity)['share'])
    @app.get('/api/devices/<identity>/transfers')
    @admin
    def list_transfers(identity):
        with lock:
            require(identity);purge()
            return jsonify([t for t in transfers.values() if t['device']==identity])
    @app.post('/api/devices/<identity>/files')
    @admin
    def send_file(identity):
        with lock:
            require(identity);key,t=create(identity,'to-device',request.headers.get('X-Filename'),'uploading')
        try:
            size=store(key)
            with lock:
                require(identity)
                if key not in transfers: abort(409)
                t['size']=size;t['status']='queued'
        except BaseException:
            with lock: transfers.pop(key,None)
            (folder/(key+'.bin')).unlink(missing_ok=True);raise
        return jsonify(t),201
    @app.post('/api/devices/<identity>/files/request')
    @admin
    def request_file(identity):
        with lock:
            d=require(identity);payload=request.get_json()
            if not isinstance(payload,dict): abort(400)
            name=payload.get('name')
            if not any(s['name']==name for s in d['share']): abort(404)
            _,t=create(identity,'from-device',name,'queued')
        return jsonify(t),201
    @app.get('/api/devices/<identity>/file-jobs')
    def jobs(identity):
        with lock:
            d=device(identity);purge()
            return jsonify([t for t in transfers.values() if t['device']==identity and t['status']=='queued'] if d['files'] else [])
    @app.get('/api/devices/<identity>/file-jobs/<key>')
    def agent_get(identity,key):
        with lock:
            device(identity);require(identity);t=transfer(identity,key)
            if t['direction']!='to-device' or t['status']!='queued': abort(409)
            return Response((folder/(key+'.bin')).read_bytes(),mimetype='application/octet-stream')
    @app.put('/api/devices/<identity>/file-jobs/<key>')
    def agent_put(identity,key):
        with lock:
            device(identity);require(identity);t=transfer(identity,key)
            if t['direction']!='from-device' or t['status']!='queued': abort(409)
            t['status']='uploading'
        try:
            size=store(key)
            with lock:
                require(identity)
                if key not in transfers: abort(409)
                t['size']=size;t['status']='ready';audit(identity,'file from-device ready')
        except BaseException:
            with lock:
                if key in transfers:t['status']='failed'
            (folder/(key+'.bin')).unlink(missing_ok=True);raise
        return '',204
    @app.post('/api/devices/<identity>/file-jobs/<key>/ack')
    def ack(identity,key):
        with lock:
            device(identity);t=transfer(identity,key)
            if t['status']!='queued': abort(409)
            success=request.get_json().get('success') is True
            if t['direction']=='from-device' and success: abort(409)
            t['status']='delivered' if success else 'failed'
            (folder/(key+'.bin')).unlink(missing_ok=True); audit(identity,'file '+t['status'])
        return '',204
    @app.get('/api/devices/<identity>/files/<key>')
    @admin
    def browser_get(identity,key):
        with lock:
            require(identity);t=transfer(identity,key)
            if t['direction']!='from-device' or t['status']!='ready': abort(409)
            return Response((folder/(key+'.bin')).read_bytes(),mimetype='application/octet-stream',
                headers={'Content-Disposition':'attachment; filename="'+t['name']+'"'})
    @app.post('/api/devices/<identity>/disconnect')
    def disconnect(identity):
        with lock:
            d=device(identity);d.update(seen=0,frame=b'',control=False,audio=False,files=False)
            d['commands'].clear();d['audio_chunks'].clear();purge(identity)
            audit(identity,'disconnected')
        return '',204
    return purge
