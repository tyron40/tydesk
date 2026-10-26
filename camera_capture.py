"""Visible, locally opted-in Windows webcam sharing, with automatic camera detection and immediate local Stop."""
import threading
import queue
import requests


def open_camera(cv, stop, allowed, index=None):
    # Try the default first, then alternate Windows capture backends/devices.
    for device in ([index] if index is not None else range(4)):
        for backend in (cv.CAP_DSHOW, cv.CAP_MSMF):
            if stop.is_set() or not allowed.is_set():return None, None
            capture=None
            try:
                capture=cv.VideoCapture(device, backend)
                if capture.isOpened():
                    capture.set(cv.CAP_PROP_FRAME_WIDTH,640)
                    capture.set(cv.CAP_PROP_FRAME_HEIGHT,480)
                    for _ in range(3):
                        if stop.is_set() or not allowed.is_set():break
                        ok,frame=capture.read()
                        if ok and frame is not None:return capture,frame
            except Exception:
                pass
            if capture is not None:capture.release()
    if stop.is_set() or not allowed.is_set():return None,None
    raise RuntimeError('No working camera found. Check the camera privacy switch, Windows Settings > Privacy & security > Camera > desktop app access, and close other camera apps.')


def run(base, token, stop, allowed, notify, index=None):
    capture = None;failed=False;done=threading.Event();latest=queue.Queue(maxsize=1)
    def upload():
        with requests.Session() as session:
            session.headers['Authorization']='Bearer '+token
            while not done.is_set() and allowed.is_set() and not stop.is_set():
                try:jpeg=latest.get(timeout=.1)
                except queue.Empty:continue
                if done.is_set() or stop.is_set() or not allowed.is_set():break
                try:
                    response=session.post(base+'/camera',data=jpeg,headers={'Content-Type':'image/jpeg'},timeout=(5,10))
                    if response.status_code==401:
                        allowed.clear();stop.set();notify(('camera_error','Pairing revoked. Camera sharing stopped.'));break
                    response.raise_for_status()
                except requests.RequestException:
                    if allowed.is_set() and not done.is_set():notify(('camera_status','Camera connection delayed · Stop camera releases the camera locally'))
    try:
        import cv2
        if not allowed.is_set() or stop.is_set():return
        capture,first_frame=open_camera(cv2,stop,allowed,index)
        if capture is None:return
        notify(('camera_status','Camera sharing ON · use Stop camera or Disconnect to stop'))
        threading.Thread(target=upload,daemon=True,name='ZDesk camera upload').start()
        while allowed.is_set() and not stop.is_set():
            if first_frame is not None:ok,frame=True,first_frame;first_frame=None
            else:ok,frame=capture.read()
            if not ok:raise RuntimeError('Camera capture stopped. Re-enable camera sharing to retry.')
            height,width=frame.shape[:2]
            if max(height,width)>960:
                frame=cv2.resize(frame,(round(width*960/max(height,width)),round(height*960/max(height,width))))
            ok, jpeg = cv2.imencode('.jpg',frame,[cv2.IMWRITE_JPEG_QUALITY,65])
            if not ok:raise RuntimeError('Could not encode camera image')
            if stop.is_set() or not allowed.is_set():break
            try:latest.get_nowait()
            except queue.Empty:pass
            latest.put_nowait(jpeg.tobytes())
            stop.wait(.7)
    except Exception as exc:
        failed=True;allowed.clear();notify(('camera_error',str(exc)))
    finally:
        done.set()
        if capture is not None:capture.release()
        if not failed:notify(('camera_status','Camera off'))


def start(base, token, stop, allowed, notify, index=None):
    worker=threading.Thread(target=run,args=(base,token,stop,allowed,notify,index),daemon=True,name='ZDesk camera')
    worker.start()
    return worker
