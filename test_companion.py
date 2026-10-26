"""Connection recovery and close-to-tray lifecycle without hardware capture."""
import sys,unittest,queue,threading
from unittest.mock import Mock,patch
sys.modules.setdefault('pyautogui',Mock())
import agent
class CompanionTests(unittest.TestCase):
 def app(self):
  a=agent.Companion.__new__(agent.Companion);a.root=Mock();a.running=False;a.exiting=False
  a.credentials={'id':'old','token':'old-token','url':'https://example.test'}
  a.url=Mock();a.url.get.return_value='https://example.test';a.code=Mock();a.code.get.return_value=''
  a.unattended=Mock();a.unattended.get.return_value=True;a.background=Mock();a.background.get.return_value=True
  a.start=Mock();a.status=Mock();a.stop=threading.Event();a.events=queue.Queue();a.allow=threading.Event();a.audio=threading.Event();a.files=threading.Event();a.camera=threading.Event();a.camera_permission=Mock();a.camera_status=Mock();a.tray=None
  return a
 def test_camera_consent_is_saved_and_stop_camera_revokes_saved_choice(self):
  a=self.app();a.camera_permission.get.return_value=True;a.save=Mock()
  with patch('agent.messagebox.askokcancel') as popup:
   a.camera_changed();popup.assert_not_called()
  self.assertTrue(a.camera.is_set());a.save.assert_called_once()
  a.stop_camera();self.assertFalse(a.camera.is_set());a.camera_permission.set.assert_called_with(False)
  self.assertEqual(a.save.call_count,2)
 def test_all_sharing_selects_permissions_without_connecting_or_enabling_startup(self):
  a=self.app();a.control=Mock();a.system_audio=Mock();a.microphone=Mock();a.file_permission=Mock();a.mic=threading.Event();a.save=Mock();a.connect=Mock()
  with patch('agent.messagebox.askokcancel') as popup:
   a.select_all_sharing();popup.assert_not_called()
  self.assertTrue(all(e.is_set() for _,e in a.sharing_options()));a.connect.assert_not_called()
  a.unattended.set.assert_not_called();a.background.set.assert_not_called()
  a.select_all_sharing(False);self.assertTrue(all(not e.is_set() for _,e in a.sharing_options()))
  self.assertEqual(a.save.call_count,2)
 def test_camera_setting_survives_disconnect_but_hardware_stops(self):
  a=self.app();a.camera.set();a.camera_permission.get.return_value=True
  a.disconnect();self.assertFalse(a.camera.is_set());self.assertTrue(a.stop.is_set())
  a.camera_permission.set.assert_not_called()
 def test_selected_camera_resumes_on_connect(self):
  a=self.app();a.camera_permission.get.return_value=True
  with patch('agent.threading.Thread'):a.connect()
  self.assertTrue(a.camera.is_set())
 def test_new_code_overrides_stale_saved_enrollment(self):
  a=self.app();a.code.get.return_value='fresh-pairing-code'
  with patch('agent.threading.Thread') as thread,patch('agent.messagebox.askokcancel',return_value=True):
   a.connect();self.assertEqual(thread.call_args.kwargs['args'],('https://example.test','fresh-pairing-code',None,True))
 def test_blank_code_reuses_saved_device(self):
  a=self.app()
  with patch('agent.threading.Thread') as thread:a.connect();self.assertEqual(thread.call_args.kwargs['args'][2],a.credentials)
 def test_tray_close_keeps_worker_alive_and_quit_stops_it(self):
  a=self.app();a.tray=Mock();a.tray_ready=threading.Event();a.tray_ready.set();a.save=Mock();a.ensure_tray=Mock()
  a.close();self.assertFalse(a.stop.is_set());a.root.withdraw.assert_called_once()
  a.quit();self.assertTrue(a.stop.is_set());a.tray.stop.assert_called_once()
 def test_tray_not_ready_does_not_hide_window(self):
  a=self.app();a.tray_ready=threading.Event();a.ensure_tray=Mock()
  a.close();a.root.withdraw.assert_not_called();self.assertFalse(a.stop.is_set())
 def test_revoked_credential_is_cleared_without_automatic_reenrollment(self):
  a=self.app();a.show=Mock();a.show_event=None
  a.events.put(('revoked','Saved connection was revoked.'));a.events.put(('done','Stopped: enter a new code'))
  with patch('agent.local_settings.forget') as forget:
   a.poll();forget.assert_called_once();self.assertIsNone(a.credentials)
 def test_uninstall_cancel_keeps_app_and_pairing(self):
  a=self.app();a.running=True;a.allow.set();a.show=Mock()
  with patch('agent.messagebox.askyesno',return_value=False),patch('agent.threading.Thread') as thread,patch('agent.local_settings.forget') as forget:
   a.confirm_uninstall({'id':'request'});forget.assert_not_called();self.assertFalse(a.stop.is_set());thread.assert_called_once()
 def test_uninstall_never_runs_without_local_control(self):
  a=self.app();a.running=True;a.show=Mock()
  with patch('agent.messagebox.askyesno') as confirm:
   a.confirm_uninstall({'id':'request'});confirm.assert_not_called()
if __name__=='__main__':unittest.main()
