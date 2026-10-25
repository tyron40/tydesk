"""Continuous system playback capture; bounded upload queue, no physical microphone."""
import io,threading,wave,queue,time,sys

def start(url,identity,token,stop,permission,report):
    thread=threading.Thread(target=run,args=(url,identity,token,stop,permission,report),daemon=True)
    thread.start();return thread

def pcm_wav(samples):
    import numpy as np
    samples=np.nan_to_num(samples,nan=0,posinf=1,neginf=-1)
    level=float(np.sqrt(np.mean(samples*samples)))
    pcm=(np.clip(samples,-1,1)*32767).astype('<i2').tobytes();buf=io.BytesIO()
    with wave.open(buf,'wb') as wav:
        wav.setnchannels(2);wav.setsampwidth(2);wav.setframerate(24000);wav.writeframes(pcm)
    return buf.getvalue(),min(1,level)

def newest(q,value):
    try:q.put_nowait(value)
    except queue.Full:
        try:q.get_nowait()
        except queue.Empty:pass
        try:q.put_nowait(value)
        except queue.Full:pass

def initialize_audio_thread():
    """WASAPI requires COM on every capture thread, including after re-enabling audio."""
    if sys.platform!='win32':return lambda:None
    import ctypes
    ole=ctypes.windll.ole32
    ole.CoInitializeEx.argtypes=[ctypes.c_void_p,ctypes.c_uint32];ole.CoInitializeEx.restype=ctypes.c_long
    result=ole.CoInitializeEx(None,0)
    if result in (0,1):return ole.CoUninitialize
    if result==-2147417850:return lambda:None # Existing COM apartment remains usable.
    raise RuntimeError('Could not initialize Windows playback capture ('+str(result)+')')

def run(url,identity,token,stop,permission,report):
    import requests
    chunks=queue.Queue(maxsize=3);done=threading.Event();state={'state':'waiting','message':'Starting system playback capture','level':0};state_lock=threading.Lock()
    def status(kind,message,level=0):
        with state_lock:state.update(state=kind,message=message[:160],level=level)
    def upload():
        last_status=0;last_error=0
        with requests.Session() as session:
            session.headers['Authorization']='Bearer '+token
            while not stop.is_set() and not done.is_set() and permission.is_set():
                try:
                    if time.monotonic()-last_status>1:
                        with state_lock:data=dict(state)
                        r=session.post(f'{url}/api/devices/{identity}/audio-status',json=data,timeout=2)
                        if r.status_code==401:stop.set();return
                        last_status=time.monotonic()
                    try:stamp,payload=chunks.get(timeout=.2)
                    except queue.Empty:continue
                    if time.monotonic()-stamp>.8:continue
                    r=session.post(f'{url}/api/devices/{identity}/audio',data=payload,headers={'Content-Type':'audio/wav'},timeout=2)
                    if r.status_code==401:stop.set();return
                    if r.status_code!=409:r.raise_for_status()
                except requests.RequestException as exc:
                    if time.monotonic()-last_error>5:report(('status','Audio connection interrupted; retrying. '+str(exc)[:90]));last_error=time.monotonic()
                    stop.wait(.3)
    sender=threading.Thread(target=upload,daemon=True);sender.start()
    cleanup_com=lambda:None
    try:
        cleanup_com=initialize_audio_thread()
        import soundcard as sc
        while not stop.is_set() and permission.is_set():
            try:
                speaker=sc.default_speaker()
                if speaker is None:raise RuntimeError('No playback device. Connect speakers/headphones or enable a Windows output device.')
                loopback=sc.get_microphone(id=str(speaker.id),include_loopback=True)
                if not loopback.isloopback:raise RuntimeError('Playback loopback unavailable; no microphone will be opened.')
                with loopback.recorder(samplerate=24000,channels=2,blocksize=4800) as recorder:
                    check=time.monotonic()
                    while permission.is_set() and not stop.is_set():
                        samples=recorder.record(numframes=4800)
                        if stop.is_set() or not permission.is_set():break
                        payload,level=pcm_wav(samples);newest(chunks,(time.monotonic(),payload))
                        status('capturing','Capturing '+str(speaker.name),level)
                        if time.monotonic()-check>2:
                            check=time.monotonic();current=sc.default_speaker()
                            if current is None or current.id!=speaker.id:break
            except Exception as exc:
                status('error',str(exc));report(('status','System audio: '+str(exc)[:140]));stop.wait(3)
    except Exception as exc:
        status('error',str(exc));report(('status','System audio unavailable: '+str(exc)[:140]));stop.wait(1.2)
    finally:
        done.set();sender.join(timeout=3);cleanup_com()
