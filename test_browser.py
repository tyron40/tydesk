import os,tempfile,unittest,io,zipfile
os.environ.setdefault('TYDESK_PASSWORD','test-browser-password-long')
os.environ.setdefault('TYDESK_DATA',tempfile.mkdtemp(prefix='tydesk-browser-tests-'))
import server
class BrowserTests(unittest.TestCase):
 def setUp(self):
  server.enrollment_gate=server.connection_access.EnrollmentGate()
  self.client=server.app.test_client()
 def test_companion_page_and_dashboard_choices(self):
  r=self.client.get('/companion');self.assertEqual(r.status_code,200)
  self.assertIn(b'Share this computer',r.data);self.assertIn(b'getDisplayMedia',r.data)
  self.assertIn(b'audio:false',r.data);self.assertIn(b"'X-Allow-Control':'no'",r.data)
  self.assertIn(b'/companion',self.client.get('/').data)
 def test_complete_download_and_no_credentials(self):
  r=self.client.get('/download/windows-source');self.assertEqual(r.status_code,200)
  self.assertIn('attachment;',r.headers['Content-Disposition'])
  with zipfile.ZipFile(io.BytesIO(r.data)) as z:
   names=z.namelist();self.assertIn('ZDesk-Companion/Start-ZDesk.cmd',names)
   self.assertIn('ZDesk-Companion/agent.py',names)
   for name in ['audio_capture.py','file_exchange.py','extensions.py','local_settings.py','requirements.txt','start-agent.ps1']:
    self.assertIn('ZDesk-Companion/'+name,names)
   self.assertTrue(all('data/' not in n and not n.endswith('.dat') for n in names))
   for n in names:self.assertNotIn(server.ADMIN.encode(),z.read(n))
   agent=z.read('ZDesk-Companion/agent.py');self.assertIn(b'https://tydesk-broker.onrender.com',agent)
   self.assertNotIn(b'http://127.0.0.1:8787',agent)
 def test_revoked_browser_pairing_cannot_upload(self):
  admin={'Authorization':'Bearer '+server.ADMIN}
  code=self.client.post('/api/pairing',headers=admin).json['code']
  d=self.client.post('/api/enroll',json={'code':code,'name':'Browser test'}).json
  path='/api/devices/'+d['id'];auth={'Authorization':'Bearer '+d['token'],'Content-Type':'image/jpeg'}
  self.assertEqual(self.client.post(path+'/frame',headers=auth,data=b'frame').status_code,204)
  self.client.delete(path,headers=admin)
  self.assertEqual(self.client.post(path+'/frame',headers=auth,data=b'frame').status_code,401)
if __name__=='__main__':unittest.main()
