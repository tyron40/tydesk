"""Platform and download checks without opening capture devices or enrolling."""
import json,os,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import Mock,patch
import desktop_runtime,desktop_shell,local_settings,download_catalog,camera_capture
from flask import Flask
import browser_routes

class DesktopTests(unittest.TestCase):
 def test_matching_platform_and_safe_mac_audio_capability(self):
  with patch('desktop_runtime.sys.platform','darwin'):
   self.assertEqual(desktop_runtime.platform_id(),'macos');self.assertFalse(desktop_runtime.system_audio_available())
  with patch('desktop_runtime.sys.platform','linux'):
   self.assertEqual(desktop_runtime.platform_id(),'linux')
 def test_secure_pairing_never_falls_back_to_plaintext(self):
  backend=Mock();backend.__class__=type('Keyring',(),{'__module__':'keyring.backends.fail'})
  with patch.dict('sys.modules',{'keyring':Mock(get_keyring=lambda:backend)}):
   with self.assertRaisesRegex(RuntimeError,'Plaintext'):desktop_runtime.secure_save('private-token')
 def test_secure_chainer_ignores_plaintext_backend(self):
  secure=type('Keyring',(),{'__module__':'keyring.backends.SecretService'})()
  insecure=type('Plain',(),{'__module__':'keyrings.alt.file'})()
  chain=type('ChainerBackend',(),{'__module__':'keyring.backends.chainer','backends':[insecure,secure]})()
  with patch.dict('sys.modules',{'keyring':Mock(get_keyring=lambda:chain)}):self.assertIs(desktop_runtime.keyring_backend(),secure)
 def test_mac_command_modifier_is_released_correctly(self):
  import remote_input
  pg=Mock();controller=remote_input.Controller(pg)
  with patch('remote_input.sys.platform','darwin'):
   controller.apply({'type':'key_down','key':'win'});controller.release()
  pg.keyDown.assert_called_with('command');pg.keyUp.assert_called_with('command');self.assertFalse(controller.keys)
 def test_nonwindows_pairing_uses_secure_backend_for_save_load_and_forget(self):
  with patch('local_settings.os.name','posix'),patch('desktop_runtime.secure_save') as save,patch('desktop_runtime.secure_load',return_value='{"id":"one","camera":true}') as load,patch('desktop_runtime.secure_forget') as forget:
   local_settings.save({'id':'one','camera':True});self.assertEqual(json.loads(save.call_args.args[0]),{'id':'one','camera':True});self.assertTrue(local_settings.load()['camera']);local_settings.forget();forget.assert_called_once()
 def test_startup_is_opt_in_user_scoped_and_removable(self):
  with tempfile.TemporaryDirectory() as folder,patch('desktop_shell.Path.home',return_value=Path(folder)),patch('desktop_shell.sys.platform','darwin'):
   path=Path(folder)/'Library/LaunchAgents/com.zdesk.companion.plist'
   self.assertFalse(path.exists());desktop_shell.startup(True)
   import plistlib
   config=plistlib.loads(path.read_bytes());self.assertTrue(config['RunAtLoad']);self.assertNotIn('KeepAlive',config)
   desktop_shell.startup(False);self.assertFalse(path.exists())
  with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'XDG_CONFIG_HOME':folder}),patch('desktop_shell.sys.platform','linux'):
   desktop_shell.startup(True);path=Path(folder)/'autostart/zdesk.desktop';self.assertIn('--autostart',path.read_text());desktop_shell.startup(False);self.assertFalse(path.exists())
 def test_camera_uses_native_backends_and_releases_failures(self):
  for platform,first in [('darwin',1200),('linux',200),('win32',700)]:
   cv=Mock(CAP_DSHOW=700,CAP_MSMF=1400,CAP_AVFOUNDATION=1200,CAP_V4L2=200,CAP_ANY=0);capture=Mock();capture.isOpened.return_value=True;capture.read.return_value=(True,object());cv.VideoCapture.return_value=capture
   allowed=threading.Event();allowed.set()
   with patch('camera_capture.sys.platform',platform):camera_capture.open_camera(cv,threading.Event(),allowed)
   self.assertEqual(cv.VideoCapture.call_args.args,(0,first))
 def test_all_native_downloads_are_allowlisted_and_never_fake_availability(self):
  app=Flask(__name__);browser_routes.install(app);client=app.test_client()
  with tempfile.TemporaryDirectory() as folder,patch.object(browser_routes,'ROOT',Path(folder)):
   root=Path(folder);(root/'downloads').mkdir()
   response=client.get('/api/downloads');self.assertEqual(len(response.json['platforms']),6);self.assertFalse(any(d['available'] for d in response.json['platforms']))
   for target in ('macos-arm64','macos-intel','linux-x64','linux-arm64'):
    self.assertEqual(client.get('/download/'+target).status_code,503)
    entry=next(e for e in download_catalog.CATALOG if e['id']==target);(root/'downloads'/entry['filename']).write_bytes(b'test-package')
    with client.get('/download/'+target) as r:self.assertEqual(r.status_code,200);self.assertEqual(r.data,b'test-package');self.assertIn(entry['filename'],r.headers['Content-Disposition'])
   self.assertEqual(client.get('/download/unknown').status_code,404)
   self.assertEqual(client.get('/download/../local_settings.py').status_code,404)
if __name__=='__main__':unittest.main()
