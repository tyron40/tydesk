import os,tempfile,time,unittest,threading,sys
from unittest.mock import Mock,patch
os.environ.setdefault('TYDESK_PASSWORD','camera-route-test-password')
os.environ.setdefault('TYDESK_DATA',tempfile.mkdtemp())
import server
import camera_capture


class CameraTests(unittest.TestCase):
 def setUp(self):
  server.enrollment_gate=server.connection_access.EnrollmentGate()
  self.client=server.app.test_client();self.admin={'Authorization':'Bearer '+server.ADMIN}
  code=self.client.post('/api/pairing',headers=self.admin).json['code']
  enrollment=self.client.post('/api/enroll',json={'code':code}).json
  self.identity=enrollment['id'];self.base='/api/devices/'+self.identity
  self.auth={'Authorization':'Bearer '+enrollment['token']};self.jpeg=b'\xff\xd8test-frame\xff\xd9'
  self.permission('no')
 def permission(self,enabled):
  self.client.post(self.base+'/frame',headers={**self.auth,'Content-Type':'image/jpeg','X-Allow-Camera':enabled},data=b'screen')
 def upload(self):
  return self.client.post(self.base+'/camera',headers={**self.auth,'Content-Type':'image/jpeg'},data=self.jpeg)
 def test_local_permission_and_separate_camera_authentication(self):
  self.assertEqual(self.upload().status_code,409)
  self.permission('yes');self.assertEqual(self.upload().status_code,204)
  self.assertEqual(self.client.get(self.base+'/camera').status_code,401)
  self.assertEqual(self.client.get(self.base+'/camera',headers=self.auth).status_code,401)
  response=self.client.get(self.base+'/camera',headers=self.admin)
  self.assertEqual(response.data,self.jpeg);self.assertEqual(response.headers['Cache-Control'],'no-store')
  self.assertEqual(self.client.post(self.base+'/commands',headers=self.admin,json={'type':'enable_camera'}).status_code,400)
 def test_permission_off_and_disconnect_clear_the_last_frame(self):
  self.permission('yes');self.upload();self.permission('no')
  self.assertEqual(server.devices[self.identity]['camera_frame'],b'')
  self.assertEqual(self.client.get(self.base+'/camera',headers=self.admin).status_code,404)
  self.permission('yes');self.upload();self.client.post(self.base+'/disconnect',headers=self.auth)
  self.assertFalse(server.devices[self.identity]['camera'])
  self.assertEqual(server.devices[self.identity]['camera_frame'],b'')
 def test_expired_camera_frames_and_invalid_payloads_are_rejected(self):
  self.permission('yes');self.upload();server.devices[self.identity]['camera_seen']=time.time()-9
  self.assertEqual(self.client.get(self.base+'/camera',headers=self.admin).status_code,404)
  self.assertEqual(self.client.post(self.base+'/camera',headers={**self.auth,'Content-Type':'image/jpeg'},data=b'not an image').status_code,400)
 def test_capture_releases_camera_and_stops_when_local_permission_is_removed(self):
  allowed=threading.Event();allowed.set();stop=threading.Event();capture=Mock();capture.isOpened.return_value=True
  frame=Mock();frame.shape=(480,640,3);capture.read.return_value=(True,frame)
  cv=Mock();cv.VideoCapture.return_value=capture;cv.imencode.return_value=(True,Mock(tobytes=lambda:self.jpeg))
  session=Mock();session.headers={};session.__enter__=lambda s:s;session.__exit__=lambda *a:None
  def upload(*args,**kwargs):allowed.clear();return Mock(status_code=204)
  session.post.side_effect=upload
  with patch.dict(sys.modules,{'cv2':cv}),patch('camera_capture.requests.Session',return_value=session):
   camera_capture.run(self.base,'test-token',stop,allowed,Mock())
  capture.release.assert_called_once();session.post.assert_called_once()

 def test_stopping_camera_releases_hardware_during_a_slow_upload(self):
  allowed=threading.Event();allowed.set();stop=threading.Event();uploading=threading.Event();finish=threading.Event();released=threading.Event()
  capture=Mock();capture.isOpened.return_value=True;capture.release.side_effect=released.set
  frame=Mock();frame.shape=(480,640,3);capture.read.return_value=(True,frame)
  cv=Mock();cv.VideoCapture.return_value=capture;cv.imencode.return_value=(True,Mock(tobytes=lambda:self.jpeg))
  session=Mock();session.headers={};session.__enter__=lambda s:s;session.__exit__=lambda *a:None
  def upload(*args,**kwargs):uploading.set();finish.wait(3);return Mock(status_code=204)
  session.post.side_effect=upload
  with patch.dict(sys.modules,{'cv2':cv}),patch('camera_capture.requests.Session',return_value=session):
   worker=threading.Thread(target=camera_capture.run,args=(self.base,'test-token',stop,allowed,Mock()))
   worker.start();self.assertTrue(uploading.wait(1));allowed.clear()
   try:self.assertTrue(released.wait(1),'Camera must release without waiting for the upload')
   finally:finish.set();worker.join(2)

if __name__=='__main__':unittest.main()
