import unittest,io,wave,queue
import numpy as np
from audio_capture import pcm_wav,newest,initialize_audio_thread
class AudioTests(unittest.TestCase):
 def test_known_tone_roundtrip_has_nonzero_signal_and_valid_stereo_pcm(self):
  tone=np.sin(2*np.pi*440*np.arange(4800)/24000)*.3
  payload,level=pcm_wav(np.column_stack([tone,tone]));self.assertGreater(level,.2)
  with wave.open(io.BytesIO(payload),'rb') as wav:
   self.assertEqual((wav.getnchannels(),wav.getframerate(),wav.getnframes()),(2,24000,4800));samples=np.frombuffer(wav.readframes(4800),dtype='<i2')
  self.assertGreater(np.max(samples),9000)
 def test_nonfinite_samples_are_safe_and_silence_measures_zero(self):
  _,level=pcm_wav(np.zeros((4800,2)));self.assertEqual(level,0)
  payload,level=pcm_wav(np.array([[np.nan,np.inf],[-np.inf,0]],dtype=float));self.assertTrue(np.isfinite(level));self.assertLessEqual(level,1)
 def test_slow_network_discards_old_chunks(self):
  q=queue.Queue(maxsize=2)
  for i in range(8):newest(q,i)
  self.assertEqual([q.get(),q.get()],[6,7])
class WindowsAudioThreadTests(unittest.TestCase):
 @unittest.skipUnless(__import__('sys').platform=='win32','Windows WASAPI only')
 def test_loopback_enumeration_restarts_on_fresh_threads(self):
  import threading,soundcard as sc
  errors=[]
  def worker():
   cleanup=lambda:None
   try:
    cleanup=initialize_audio_thread();sc.all_speakers()
   except Exception as exc:errors.append(str(exc))
   finally:cleanup()
  for _ in range(2):
   thread=threading.Thread(target=worker);thread.start();thread.join(10);self.assertFalse(thread.is_alive())
  self.assertEqual(errors,[])
class BackendOrderTests(unittest.TestCase):
 def test_library_import_precedes_explicit_thread_initialization(self):
  import builtins,sys
  from unittest.mock import patch,Mock
  import audio_capture
  order=[];original=builtins.__import__;fake=Mock()
  def imported(name,*args,**kwargs):
   if name=='soundcard':order.append('import');return fake
   return original(name,*args,**kwargs)
  with patch('builtins.__import__',side_effect=imported),patch.object(audio_capture,'initialize_audio_thread',side_effect=lambda:order.append('initialize') or (lambda:None)):
   backend,cleanup=audio_capture.load_audio_backend()
  self.assertEqual(order,['import','initialize']);self.assertIs(backend,fake)
if __name__=='__main__':unittest.main()

class UploadRecoveryTests(unittest.TestCase):
 def exercise(self,fail_audio=False,fail_status=False):
  import threading,time,requests
  from unittest.mock import Mock,patch
  import audio_capture
  stop=threading.Event();permission=threading.Event();permission.set();reports=[];calls=[]
  recorder=Mock();recorder.__enter__=Mock(return_value=recorder);recorder.__exit__=Mock(return_value=False)
  def record(**kwargs):
   time.sleep(.3 if fail_status else .02)
   return np.zeros((4800,2))
  recorder.record.side_effect=record
  loop=Mock();loop.isloopback=True;loop.recorder.return_value=recorder
  backend=Mock();backend.default_speaker.return_value=Mock(id='output',name='Test output');backend.get_microphone.return_value=loop
  session=Mock();session.__enter__=Mock(return_value=session);session.__exit__=Mock(return_value=False);session.headers={}
  attempts=0
  def post(url,**kwargs):
   nonlocal attempts
   calls.append((url,kwargs))
   if url.endswith('/audio-status'):
    if fail_status:raise requests.ReadTimeout()
    return Mock(status_code=204)
   attempts+=1
   if fail_audio and attempts==1:raise requests.ReadTimeout()
   stop.set();return Mock(status_code=204)
  session.post.side_effect=post
  with patch.object(audio_capture,'load_audio_backend',return_value=(backend,lambda:None)),patch('requests.Session',return_value=session):
   thread=threading.Thread(target=audio_capture.run,args=('https://test.invalid','device','test-token',stop,permission,reports.append))
   thread.start();thread.join(5);stop.set();thread.join(1)
  self.assertFalse(thread.is_alive());self.assertTrue(any(u.endswith('/audio') for u,k in calls));self.assertTrue(permission.is_set())
  return reports,calls
 def test_audio_timeout_recovers_without_clearing_permission(self):
  reports,calls=self.exercise(fail_audio=True)
  self.assertTrue(any('restored' in text for kind,text in reports))
  self.assertTrue(all(k['timeout'][1]>=15 for u,k in calls if u.endswith('/audio')))
 def test_diagnostics_timeout_does_not_block_audio(self):self.exercise(fail_status=True)
