"""System playback loopback only; never opens a physical microphone."""
import io, threading, wave

def start(url,identity,token,stop,permission,report):
    thread=threading.Thread(target=run,args=(url,identity,token,stop,permission,report),daemon=True)
    thread.start();return thread

def run(url,identity,token,stop,permission,report):
    try:
        import numpy as np
        import soundcard as sc
        import requests
        session=requests.Session();session.headers['Authorization']='Bearer '+token
        while not stop.is_set():
            if not permission.wait(.25): continue
            speaker=sc.default_speaker()
            if speaker is None: raise RuntimeError('No default playback device.')
            loopback=sc.get_microphone(id=str(speaker.id),include_loopback=True)
            with loopback.recorder(samplerate=24000,channels=2,blocksize=4800) as recorder:
                while permission.is_set() and not stop.is_set():
                    samples=recorder.record(numframes=9600)
                    if stop.is_set() or not permission.is_set(): break
                    pcm=(np.clip(samples,-1,1)*32767).astype('<i2').tobytes()
                    buf=io.BytesIO()
                    with wave.open(buf,'wb') as wav:
                        wav.setnchannels(2);wav.setsampwidth(2);wav.setframerate(24000);wav.writeframes(pcm)
                    r=session.post(f'{url}/api/devices/{identity}/audio',data=buf.getvalue(),
                        headers={'Content-Type':'audio/wav'},timeout=5)
                    if r.status_code==409: continue
                    r.raise_for_status()
        session.close()
    except Exception as exc:
        permission.clear();report(('status','System audio stopped: '+str(exc)[:160]))
