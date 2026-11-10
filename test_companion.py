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

class TerminalSetupTests(unittest.TestCase):
 def test_screen_only_masks_code_and_requires_local_confirmation(self):
  read=Mock(side_effect=['','CONNECT']); secret=Mock(return_value='sample-code'); write=Mock()
  self.assertEqual(agent.terminal_setup(read=read,read_secret=secret,write=write),('sample-code',set()))
  secret.assert_called_once()
  self.assertNotIn('sample-code',str(read.call_args_list)+str(write.call_args_list))
  self.assertIsNone(agent.terminal_setup(read=Mock(side_effect=['all','']),read_secret=secret,write=write))

 def test_select_all_includes_only_supported_features(self):
  with patch('agent.desktop_runtime.system_audio_available',return_value=False):
   result=agent.terminal_setup(read=Mock(side_effect=['all','CONNECT']),read_secret=lambda _: 'sample',write=Mock())
  self.assertEqual(result,('sample',{'control','microphone','camera','files'}))

 def test_invalid_feature_is_rejected_before_passcode(self):
  secret=Mock()
  with self.assertRaises(ValueError):
   agent.terminal_setup(read=lambda _: 'startup',read_secret=secret,write=Mock())
  secret.assert_not_called()

 def test_terminal_connection_sets_permissions_without_saving_pairing(self):
  app=CompanionTests().app()
  app.control=Mock();app.system_audio=Mock();app.microphone=Mock();app.file_permission=Mock()
  app.mic=threading.Event();app.connect=Mock();app.save=Mock()
  for attr in ['control','system_audio','microphone','camera_permission','file_permission']:
   var=getattr(app,attr);var.set.side_effect=lambda value,var=var: setattr(var.get,'return_value',value)
  agent.connect_from_terminal(app,'sample',{'microphone'})
  self.assertTrue(app.mic.is_set())
  self.assertFalse(any(event.is_set() for event in [app.audio,app.allow,app.camera,app.files]))
  app.connect.assert_called_once();app.save.assert_not_called()
  self.assertEqual([c.args for c in app.code.set.call_args_list],[('sample',),('',)])

 def test_saved_terminal_pairing_skips_code_but_requires_connect(self):
  secret=Mock()
  self.assertIsNone(agent.terminal_setup(read=Mock(side_effect=['microphone','']),read_secret=secret,write=Mock(),saved=True,remember=True))
  self.assertEqual(agent.terminal_setup(read=Mock(side_effect=['','CONNECT']),read_secret=secret,write=Mock(),saved=True,remember=True),('',set()))
  secret.assert_not_called()

 def test_terminal_pairing_saves_only_after_server_enrollment_and_forgets_on_revoke(self):
  app=CompanionTests().app()
  app.terminal_pairing=True;app.save=Mock();app.show=Mock()
  issued={'id':'paired-id','token':'test-token','url':agent.DEFAULT_SERVER}
  with patch('agent.local_settings.save_terminal') as save,patch('agent.local_settings.forget_terminal') as forget,patch('agent.local_settings.forget') as gui_forget:
   app.events.put(('credentials',issued));app.poll();save.assert_called_once_with(issued)
   app.events.put(('revoked','Revoked'));app.poll();forget.assert_called_once();gui_forget.assert_not_called()
  self.assertIsNone(app.credentials)

 def test_terminal_store_keeps_only_device_credential_separate_from_gui(self):
  import tempfile,json
  from pathlib import Path
  from types import SimpleNamespace
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp)
   gui=root/'enrollment.dat';gui.write_bytes(b'gui-store')
   crypt=Mock()
   crypt.CryptProtectData.return_value=b'protected-test-bytes'
   wanted={'id':'test-id','token':'test-token','url':agent.DEFAULT_SERVER}
   crypt.CryptUnprotectData.return_value=(None,json.dumps(wanted).encode())
   with patch.object(agent.local_settings,'ROOT',root),patch.object(agent.local_settings,'os',SimpleNamespace(name='nt')),patch.dict(sys.modules,{'win32crypt':crypt}):
    agent.local_settings.save_terminal({**wanted,'camera':True,'code':'test-passcode'})
    self.assertEqual(json.loads(crypt.CryptProtectData.call_args.args[0]),wanted)
    self.assertEqual((root/'enrollment-terminal.dat').read_bytes(),b'protected-test-bytes')
    self.assertEqual(agent.local_settings.load_terminal(),wanted)
    agent.local_settings.forget_terminal();self.assertIsNone(agent.local_settings.load_terminal())
    self.assertEqual(gui.read_bytes(),b'gui-store')

 def test_preselect_all_skips_feature_prompt_and_still_requires_consent(self):
  secret=Mock(return_value='sample-code');write=Mock();read=Mock(return_value='')
  with patch('agent.desktop_runtime.system_audio_available',return_value=False):
   self.assertIsNone(agent.terminal_setup(read=read,read_secret=secret,write=write,all_sharing=True))
   read.assert_called_once()
   self.assertIn('Type CONNECT',read.call_args.args[0])
   summary=next(c.args[0] for c in write.call_args_list if c.args[0].startswith('Selected:'))
   self.assertIn('microphone (nearby sound)',summary)
   self.assertIn('camera (surroundings)',summary)
   self.assertNotIn('system playback',summary)
   result=agent.terminal_setup(read=lambda _: 'CONNECT',read_secret=secret,write=write,all_sharing=True)
  self.assertEqual(result,('sample-code',{'control','microphone','camera','files'}))

if __name__=='__main__':unittest.main()
