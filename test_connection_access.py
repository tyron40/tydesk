import os,tempfile,unittest
from unittest.mock import patch
os.environ.setdefault('TYDESK_PASSWORD','test-passcode-admin-password')
os.environ.setdefault('TYDESK_DATA',tempfile.mkdtemp())
import server,connection_access
class AccessTests(unittest.TestCase):
 def setUp(self):
  self.c=server.app.test_client();self.admin={'Authorization':'Bearer '+server.ADMIN}
  server.enrollment_gate=connection_access.EnrollmentGate();server.passcode_hash=None
  self.c.delete('/api/access-passcode',headers=self.admin)
 def test_reuse_rotate_disable_and_revocation(self):
  code='A unique connection phrase 123!'
  self.assertEqual(self.c.put('/api/access-passcode',json={'passcode':code}).status_code,401)
  self.assertEqual(self.c.put('/api/access-passcode',headers=self.admin,json={'passcode':'1234'}).status_code,400)
  self.assertTrue(self.c.put('/api/access-passcode',headers=self.admin,json={'passcode':code}).json['enabled'])
  self.assertNotIn(code,self.c.get('/api/access-passcode',headers=self.admin).text)
  self.assertNotIn(code,server.passcode_hash)
  first=self.c.post('/api/enroll',json={'code':code}).json
  second=self.c.post('/api/enroll',json={'code':code}).json
  self.assertNotEqual(first['id'],second['id'])
  self.c.put('/api/access-passcode',headers=self.admin,json={'passcode':'A different connection phrase 456!'})
  self.assertEqual(self.c.post('/api/enroll',json={'code':code}).status_code,403)
  auth={'Authorization':'Bearer '+first['token']};path='/api/devices/'+first['id']
  self.assertEqual(self.c.get(path+'/commands',headers=auth).status_code,200)
  self.c.delete(path,headers=self.admin)
  self.assertEqual(self.c.get(path+'/commands',headers=auth).status_code,401)
  self.c.delete('/api/access-passcode',headers=self.admin)
  self.assertEqual(self.c.post('/api/enroll',json={'code':'A different connection phrase 456!'}).status_code,403)
 def test_persistence_failure_does_not_activate_passcode(self):
  with patch.object(server.device_registry,'set_passcode',side_effect=OSError):
   self.assertEqual(self.c.put('/api/access-passcode',headers=self.admin,json={'passcode':'A valid connection phrase 123!'}).status_code,503)
  self.assertFalse(self.c.get('/api/access-passcode',headers=self.admin).json['enabled'])
 def test_enrollment_attempts_are_bounded_and_expire(self):
  gate=connection_access.EnrollmentGate()
  with patch('connection_access.time.monotonic',return_value=1):
   self.assertTrue(all(gate.permit('peer') for _ in range(10)))
   self.assertFalse(gate.permit('peer'))
  with patch('connection_access.time.monotonic',return_value=62):self.assertTrue(gate.permit('peer'))
  for _ in range(10):self.assertEqual(self.c.post('/api/enroll',json={'code':'bad'}).status_code,403)
  self.assertEqual(self.c.post('/api/enroll',json={'code':'bad'}).status_code,429)
if __name__=='__main__':unittest.main()
