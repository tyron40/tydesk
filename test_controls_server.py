import unittest,os,tempfile,io,wave
os.environ.setdefault('TYDESK_PASSWORD','test-control-server-password')
os.environ.setdefault('TYDESK_DATA',tempfile.mkdtemp())
import server
class ControlServerTests(unittest.TestCase):
 def setUp(self):
  server.enrollment_gate=server.connection_access.EnrollmentGate()
  self.c=server.app.test_client();self.admin={'Authorization':'Bearer '+server.ADMIN}
  code=self.c.post('/api/pairing',headers=self.admin).json['code'];d=self.c.post('/api/enroll',json={'code':code}).json
  self.path='/api/devices/'+d['id'];self.auth={'Authorization':'Bearer '+d['token']}
  self.c.post(self.path+'/frame',headers={**self.auth,'Content-Type':'image/jpeg','X-Allow-Control':'yes','X-Allow-Audio':'yes','X-TyDesk-Protocol':'2','X-Remote-Cursor':'text'},data=b'frame')
 def test_batched_motion_drag_keys_and_coalescing(self):
  commands=[{'type':'pointer_down','x':.1,'y':.1},{'type':'move','x':.2,'y':.2},{'type':'move','x':.8,'y':.8},{'type':'pointer_up','x':.8,'y':.8},{'type':'key_down','key':'ctrl'},{'type':'key','key':'c'},{'type':'key_up','key':'ctrl'}]
  self.assertEqual(self.c.post(self.path+'/commands',headers=self.admin,json={'commands':commands}).status_code,204)
  values=self.c.get(self.path+'/commands',headers=self.auth).json
  self.assertEqual([c['type'] for c in values],['pointer_down','move','pointer_up','key_down','key','key_up']);self.assertEqual(values[1]['x'],.8)
  self.assertEqual(self.c.get(self.path+'/frame',headers=self.admin).headers['X-Remote-Cursor'],'text')
 def test_invalid_batch_is_atomic_and_release_purges_pending(self):
  self.assertEqual(self.c.post(self.path+'/commands',headers=self.admin,json={'commands':[{'type':'key','key':'a'},{'type':'move','x':9,'y':0}]}).status_code,400)
  self.assertEqual(self.c.get(self.path+'/commands',headers=self.auth).json,[])
  for c in [{'type':'key_down','key':'alt'},{'type':'release'}]:self.c.post(self.path+'/commands',headers=self.admin,json=c)
  self.assertEqual(self.c.get(self.path+'/commands',headers=self.auth).json,[{'type':'release'}])
 def test_audio_diagnostics_and_tone_transport_and_truncation(self):
  self.assertEqual(self.c.post(self.path+'/audio-status',headers=self.auth,json={'state':'error','message':'No playback device','level':0}).status_code,204)
  self.assertEqual(self.c.get(self.path+'/audio',headers=self.admin).json['status']['message'],'No playback device')
  out=io.BytesIO()
  with wave.open(out,'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(24000);w.writeframes(b'\x00'*19200)
  audio=out.getvalue();self.assertEqual(self.c.post(self.path+'/audio',headers=self.auth,data=audio).status_code,204)
  self.assertEqual(len(self.c.get(self.path+'/audio',headers=self.admin).json['chunks']),1)
  self.assertEqual(self.c.post(self.path+'/audio',headers=self.auth,data=audio[:-16]).status_code,400)
 def test_static_modules_available_and_dashboard_renders(self):
  self.assertEqual(self.c.get('/').status_code,200)
  for path in ['/static/remote-control.js','/static/system-audio.js']:
   with self.c.get(path) as response:self.assertEqual(response.status_code,200)
if __name__=='__main__':unittest.main()
