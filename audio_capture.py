"""Continuous system playback capture; bounded upload queue, explicit local permission for each source."""
import io,threading,wave,queue,time,sys
from contextlib import ExitStack

def start(url,identity,token,stop,permission,report,microphone=None):
    thread=threading.Thread(target=run,args=(url,identity,token,stop,permission,report,microphone),daemon=True)
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

def merge_wav(payloads):
    """Combine consecutive capture chunks without re-sampling or dropping samples."""
    data=[];frames=0
    for payload in payloads:
        with wave.open(io.BytesIO(payload),'rb') as wav:
            if (wav.getnchannels(),wav.getsampwidth(),wav.getframerate())!=(2,2,24000):raise ValueError('Invalid audio format')
            frames+=wav.getnframes();data.append(wav.readframes(wav.getnframes()))
    if not 0<frames<=48000:raise ValueError('Audio batch exceeds two seconds')
    output=io.BytesIO()
    with wave.open(output,'wb') as wav:
        wav.setnchannels(2);wav.setsampwidth(2);wav.setframerate(24000);wav.writeframes(b''.join(data))
    return output.getvalue()

def take_batch(first,chunks,mode,now=None,include_source=False):
    now=time.monotonic() if now is None else now
    entries=[first]
    for _ in range(4):
        try:entries.append(chunks.get_nowait())
        except queue.Empty:break
    valid=[entry for entry in entries if now-entry[0]<=3 and entry[2]==mode]
    source=(valid[0][3] if len(valid[0])>3 else 'both' if all(mode) else 'microphone' if mode[1] else 'system') if valid else None
    payloads=[entry[1] for entry in valid if len(entry)==3 or entry[3]==source]
    result=merge_wav(payloads) if payloads else None
    return (result,source) if include_source else result

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

def load_audio_backend():
    # SoundCard initializes COM during its first import and rejects S_FALSE.
    # Import on the fresh capture thread before adding our balanced COM reference.
    import soundcard as sc
    return sc,initialize_audio_thread()

def sources(sc,system,microphone):
    result=[]
    if system:
        speaker=sc.default_speaker()
        if speaker is None:raise RuntimeError('No playback device is enabled.')
        loopback=sc.get_microphone(id=str(speaker.id),include_loopback=True)
        if not loopback.isloopback:raise RuntimeError('Playback loopback is unavailable.')
        result.append(loopback)
    if microphone:
        mic=sc.default_microphone()
        if mic is None or mic.isloopback:raise RuntimeError('No physical microphone is available. Select a physical input in your system sound settings and allow microphone access for ZDesk.')
        result.append(mic)
    return result

def source_error(kind, exc):
    text=str(exc)
    if '80070490' in text.lower() or 'no playback device' in text.lower() or 'no physical microphone' in text.lower():
        return ('No usable default playback output. Select an output in Windows Sound settings.' if kind=='system'
                else 'No usable default microphone. Select an input in Windows Sound settings and check microphone privacy access.')
    return ('Playback' if kind=='system' else 'Microphone')+' unavailable: '+text[:110]


def open_recorders(sc, mode, stack):
    """Open only locally allowed sources, independently of each other's failures."""
    opened=[];errors=[]
    for allowed,kind in zip(mode,('system','microphone')):
        if not allowed:continue
        child=stack.enter_context(ExitStack())
        try:
            device=sources(sc,kind=='system',kind=='microphone')[0]
            recorder=child.enter_context(device.recorder(samplerate=24000,channels=2,blocksize=4800))
            opened.append((kind,recorder,child))
        except Exception as exc:
            child.close();errors.append(source_error(kind,exc))
    return opened,errors


def run(url,identity,token,stop,permission,report,microphone=None):
    import requests
    microphone=microphone or threading.Event()
    signature=lambda:(permission.is_set(),microphone.is_set())
    active=lambda:any(signature())
    chunks=queue.Queue(maxsize=15);done=threading.Event();state={'state':'waiting','message':'Starting shared audio capture','level':0};state_lock=threading.Lock()
    def status(kind,message,level=0):
        with state_lock:state.update(state=kind,message=message[:160],level=level)
    reported={'message':None,'at':-float('inf')}
    def warn(message):
        now=time.monotonic()
        if reported['message']!=message or now-reported['at']>=30:
            report(('status','Shared audio: '+message[:200]))
            reported.update(message=message,at=now)
    def upload():
        last_error=0;interrupted=False;backoff=.3
        with requests.Session() as session:
            session.headers['Authorization']='Bearer '+token
            while not stop.is_set() and not done.is_set() and active():
                try:
                    try:entry=chunks.get(timeout=.2)
                    except queue.Empty:entry=None
                    if stop.is_set() or done.is_set() or not active():return
                    if entry is not None:
                        current=signature();payload,source=take_batch(entry,chunks,current,include_source=True)
                        if payload is None or current!=signature() or not active():continue
                        mode=current
                        with state_lock:level=state['level']
                        r=session.post(f'{url}/api/devices/{identity}/audio',data=payload,
                            headers={'Content-Type':'audio/wav','X-Audio-Level':str(level),'X-Audio-Source':source},timeout=(5,15))
                        if r.status_code==401:stop.set();return
                        if r.status_code==409:stop.wait(.3);continue
                        r.raise_for_status()
                        if interrupted:report(('status','Shared audio upload restored • screen sharing active'))
                        interrupted=False;backoff=.3
                except requests.RequestException:
                    interrupted=True
                    if time.monotonic()-last_error>5:
                        report(('status','Audio upload delayed • reconnecting automatically. Screen sharing remains available.'));last_error=time.monotonic()
                    stop.wait(backoff);backoff=min(3,backoff*2)
    def diagnostics():
        with requests.Session() as session:
            session.headers['Authorization']='Bearer '+token
            while not stop.is_set() and not done.is_set() and active():
                with state_lock:data=dict(state)
                if data['state']!='capturing':
                    try:
                        response=session.post(f'{url}/api/devices/{identity}/audio-status',json=data,timeout=(3,5))
                        if response.status_code==401:stop.set();return
                    except requests.RequestException:pass
                done.wait(3)
    diagnostic=threading.Thread(target=diagnostics,daemon=True);diagnostic.start()
    sender=threading.Thread(target=upload,daemon=True);sender.start()
    cleanup_com=lambda:None
    try:
        sc,cleanup_com=load_audio_backend()
        while not stop.is_set() and active():
            try:
                mode=signature()
                with ExitStack() as stack:
                    recorders,errors=open_recorders(sc,mode,stack)
                    if not recorders:raise RuntimeError(' '.join(errors) or 'No selected audio input is available.')
                    if errors:warn(' '.join(errors)+' Continuing with the available source; reconnect to retry missing hardware.')
                    while active() and not stop.is_set() and signature()==mode:
                        import numpy as np
                        parts=[];kinds=[];remaining=[]
                        for kind,recorder,child in recorders:
                            if stop.is_set() or signature()!=mode:break
                            try:
                                parts.append(recorder.record(numframes=4800));kinds.append(kind);remaining.append((kind,recorder,child))
                            except Exception as exc:
                                child.close();warn(source_error(kind,exc))
                        recorders=remaining
                        if stop.is_set() or signature()!=mode:break
                        if not parts:raise RuntimeError('Selected audio devices stopped. Check Windows Sound settings and reconnect.')
                        source='both' if len(kinds)==2 else kinds[0]
                        samples=np.mean(parts,axis=0)
                        payload,level=pcm_wav(samples);newest(chunks,(time.monotonic(),payload,mode,source))
                        status('capturing','Sharing '+('system and microphone audio' if source=='both' else 'microphone / surrounding sound' if source=='microphone' else 'system playback audio'),level)
            except Exception as exc:
                status('error',str(exc));warn(str(exc));stop.wait(3)
    except Exception as exc:
        status('error',str(exc));report(('status','Shared audio unavailable: '+str(exc)[:140]));stop.wait(1.2)
    finally:
        done.set();sender.join(timeout=3);cleanup_com()
