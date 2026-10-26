import os, unittest, tempfile
os.environ['TYDESK_DATA']=tempfile.mkdtemp(prefix='tydesk-tests-')
os.environ['TYDESK_PASSWORD']='test-password-long-enough'
import server
class BrokerTests(unittest.TestCase):
    def setUp(self):
        server.enrollment_gate=server.connection_access.EnrollmentGate()
        self.c=server.app.test_client(); self.admin={'Authorization':'Bearer '+server.ADMIN}
        server.devices.clear(); server.pairings.clear();server.db.execute('DELETE FROM devices');server.db.commit()
    def enroll(self):
        code=self.c.post('/api/pairing',headers=self.admin).json['code']
        d=self.c.post('/api/enroll',json={'code':code,'name':'Test PC'}).json
        return d,code
    def test_auth_and_one_use_pairing(self):
        self.assertEqual(self.c.get('/api/devices').status_code,401)
        d,code=self.enroll()
        self.assertEqual(self.c.post('/api/enroll',json={'code':code}).status_code,403)
        self.assertEqual(len(self.c.get('/api/devices',headers=self.admin).json),1)
    def test_local_consent_frames_and_revocation(self):
        d,_=self.enroll(); path='/api/devices/'+d['id']; agent={'Authorization':'Bearer '+d['token']}
        self.assertEqual(self.c.post(path+'/commands',headers=self.admin,json={'type':'key','key':'enter'}).status_code,409)
        self.assertEqual(self.c.post(path+'/frame',headers={**agent,'Content-Type':'image/jpeg','X-Allow-Control':'yes'},data=b'frame').status_code,204)
        self.assertEqual(self.c.get(path+'/frame',headers=self.admin).data,b'frame')
        self.assertEqual(self.c.post(path+'/commands',headers=self.admin,json={'type':'click','x':1,'y':0}).status_code,204)
        self.assertEqual(len(self.c.get(path+'/commands',headers=agent).json),1)
        self.assertEqual(self.c.get(path+'/commands',headers=agent).json,[])
        self.c.delete(path,headers=self.admin)
        self.assertEqual(self.c.get(path+'/commands',headers=agent).status_code,401)
    def test_invalid_and_expired_commands(self):
        d,_=self.enroll(); path='/api/devices/'+d['id']; server.devices[d['id']]['control']=True
        for command in [{'type':'click','x':-1,'y':0},{'type':'click','x':float('nan'),'y':0},{'type':'key','key':'powershell'},{'type':'text','text':'é'},{'type':'scroll','amount':'bad'}]:
            self.assertEqual(self.c.post(path+'/commands',headers=self.admin,json=command).status_code,400)
        server.devices[d['id']]['commands'].append((0,{'type':'key','key':'enter'}))
        self.assertEqual(self.c.get(path+'/commands',headers={'Authorization':'Bearer '+d['token']}).json,[])
    def test_disabled_control_clears_pending(self):
        d,_=self.enroll(); path='/api/devices/'+d['id']; device=server.devices[d['id']];device['control']=True
        self.c.post(path+'/commands',headers=self.admin,json={'type':'key','key':'enter'})
        agent={'Authorization':'Bearer '+d['token'],'Content-Type':'image/jpeg','X-Allow-Control':'no'}
        self.c.post(path+'/frame',headers=agent,data=b'frame')
        self.assertEqual(len(device['commands']),0)
    def online(self,d):
        path='/api/devices/'+d['id'];agent={'Authorization':'Bearer '+d['token']}
        self.c.post(path+'/frame',headers={**agent,'Content-Type':'image/jpeg','X-Allow-Control':'yes','X-Allow-Audio':'yes','X-Allow-Files':'yes'},data=b'frame')
        return path,agent
    def test_audio_permission_and_buffer(self):
        import io,wave
        d,_=self.enroll();path,agent=self.online(d);buf=io.BytesIO()
        with wave.open(buf,'wb') as w:
            w.setnchannels(2);w.setsampwidth(2);w.setframerate(24000);w.writeframes(b'\x00'*38400)
        self.assertEqual(self.c.post(path+'/audio',headers=agent,data=buf.getvalue()).status_code,204)
        chunks=self.c.get(path+'/audio',headers=self.admin).json['chunks']
        self.assertEqual(len(chunks),1)
        self.assertEqual(self.c.get(path+'/audio?after='+str(chunks[0]['seq']),headers=self.admin).json['chunks'],[])
        self.assertEqual(self.c.post(path+'/audio',headers=agent,data=b'not wav').status_code,400)
        self.c.post(path+'/frame',headers={**agent,'Content-Type':'image/jpeg'},data=b'frame')
        self.assertEqual(self.c.get(path+'/audio',headers=self.admin).status_code,409)
    def test_batched_audio_and_network_jitter_preserve_order_with_bounded_age(self):
        import io,wave,base64,time
        d,_=self.enroll();path,agent=self.online(d)
        def packet(frames):
            buf=io.BytesIO()
            with wave.open(buf,'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(24000);w.writeframes(b'\x00'*(frames*4))
            return buf.getvalue()
        for _ in range(10):self.assertEqual(self.c.post(path+'/audio',headers=agent,data=packet(4800)).status_code,204)
        # This used to be limited to eight packets and two seconds.
        chunks=server.devices[d['id']]['audio_chunks'];seq,_,payload=chunks[0];chunks[0]=(seq,time.time()-3,payload)
        received=self.c.get(path+'/audio',headers=self.admin).json['chunks'];self.assertEqual([c['seq'] for c in received],list(range(1,11)))
        self.assertEqual(self.c.post(path+'/audio',headers=agent,data=packet(24000)).status_code,204)
        self.assertEqual(self.c.post(path+'/audio',headers=agent,data=packet(48001)).status_code,400)
        seq,_,payload=chunks[0];chunks[0]=(seq,time.time()-5,payload)
        self.assertEqual(self.c.get(path+'/audio',headers=self.admin).json['chunks'][0]['seq'],2)
    def test_bidirectional_file_transfer_and_revocation(self):
        d,_=self.enroll();path,agent=self.online(d)
        upload=self.c.post(path+'/files',headers={**self.admin,'X-Filename':'hello.txt'},data=b'hello')
        self.assertEqual(upload.status_code,201);key=upload.json['id']
        self.assertEqual(self.c.get(path+'/file-jobs/'+key,headers=agent).data,b'hello')
        self.assertEqual(self.c.post(path+'/file-jobs/'+key+'/ack',headers=agent,json={'success':True}).status_code,204)
        self.c.post(path+'/shares',headers=agent,json=[{'name':'export.txt','size':5}])
        requested=self.c.post(path+'/files/request',headers=self.admin,json={'name':'export.txt'})
        self.assertEqual(requested.status_code,201);key=requested.json['id']
        self.assertEqual(self.c.put(path+'/file-jobs/'+key,headers=agent,data=b'world').status_code,204)
        self.assertEqual(self.c.get(path+'/files/'+key,headers=self.admin).data,b'world')
        other,_=self.enroll()
        self.assertEqual(self.c.get(path+'/file-jobs',headers={'Authorization':'Bearer '+other['token']}).status_code,401)
        self.c.delete(path,headers=self.admin)
        self.assertEqual(self.c.get(path+'/files/'+key,headers=self.admin).status_code,409)
    def test_filename_traversal_and_file_permission(self):
        d,_=self.enroll();path,agent=self.online(d)
        for name in ['../x','x/y','CON','hello.exe:stream','foo.']:
            self.assertEqual(self.c.post(path+'/files',headers={**self.admin,'X-Filename':name},data=b'evil').status_code,400)
        self.c.post(path+'/frame',headers={**agent,'Content-Type':'image/jpeg'},data=b'frame')
        self.assertEqual(self.c.post(path+'/files',headers={**self.admin,'X-Filename':'ok.txt'},data=b'x').status_code,409)
    def test_enrollment_persistence_and_disconnect(self):
        d,_=self.enroll();path,agent=self.online(d)
        row=server.db.execute('SELECT token FROM devices WHERE id=?',(d['id'],)).fetchone()
        self.assertNotEqual(row[0],d['token'])
        import hashlib
        self.assertEqual(row[0],hashlib.sha256(d['token'].encode()).hexdigest())
        self.assertEqual(self.c.post(path+'/disconnect',headers=agent).status_code,204)
        self.assertEqual(self.c.get(path+'/frame',headers=self.admin).status_code,404)
        self.assertFalse(self.c.get('/api/devices',headers=self.admin).json[0]['online'])
if __name__=='__main__': unittest.main()
