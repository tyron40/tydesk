import unittest,io,wave,queue
import numpy as np
from audio_capture import pcm_wav,newest
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
if __name__=='__main__':unittest.main()
