"""Visible, locally opted-in Windows webcam sharing, never saved or auto-enabled."""
import threading
import requests


def run(base, token, stop, allowed, notify, index=0):
    capture = None;failed=False
    try:
        import cv2
        capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if not capture.isOpened():
            raise RuntimeError('Camera unavailable. Check Windows camera privacy settings and other apps.')
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        notify(('camera_status','Camera sharing ON · use Stop camera or Disconnect to stop'))
        with requests.Session() as session:
            session.headers['Authorization'] = 'Bearer '+token
            while allowed.is_set() and not stop.is_set():
                ok, frame = capture.read()
                if not ok:
                    raise RuntimeError('Camera capture stopped. Re-enable camera sharing to retry.')
                height,width=frame.shape[:2]
                if max(height,width)>960:
                    frame=cv2.resize(frame,(round(width*960/max(height,width)),round(height*960/max(height,width))))
                ok, jpeg = cv2.imencode('.jpg',frame,[cv2.IMWRITE_JPEG_QUALITY,65])
                if not ok:raise RuntimeError('Could not encode camera image')
                if stop.is_set() or not allowed.is_set():break
                try:
                    response=session.post(base+'/camera',data=jpeg.tobytes(),headers={'Content-Type':'image/jpeg'},timeout=(5,10))
                    if response.status_code==401:
                        stop.set();raise RuntimeError('Pairing revoked. Camera sharing stopped.')
                    response.raise_for_status()
                except requests.RequestException:
                    notify(('camera_status','Camera connection delayed · Disconnect stops capture'))
                stop.wait(.7)
    except Exception as exc:
        failed=True;allowed.clear()
        notify(('camera_error',str(exc)))
    finally:
        if capture is not None:capture.release()
        if not failed:notify(('camera_status','Camera off'))


def start(base, token, stop, allowed, notify, index=0):
    worker=threading.Thread(target=run,args=(base,token,stop,allowed,notify,index),daemon=True,name='ZDesk camera')
    worker.start()
    return worker
