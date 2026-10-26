"""Validated remote input with bounded holds and release on disconnect."""
import math,time,sys
KEYS=set('abcdefghijklmnopqrstuvwxyz0123456789')|{'enter','tab','backspace','esc','space','up','down','left','right','delete','home','end','pageup','pagedown','shift','ctrl','alt','win','capslock','insert','-','=','[',']',';','\'',',','.','/','\\','`'}|{f'f{i}' for i in range(1,13)}
CURSORS={'default','text','pointer','wait','progress','crosshair','ew-resize','ns-resize','nwse-resize','nesw-resize','move','not-allowed'}
def validate(c):
    if not isinstance(c,dict):raise ValueError('Invalid command')
    kind=c.get('type')
    if kind in ('click','move','pointer_down','pointer_up'):
        try:x,y=float(c['x']),float(c['y'])
        except (KeyError,TypeError,ValueError):raise ValueError('Invalid coordinates')
        if not all(math.isfinite(v) and 0<=v<=1 for v in (x,y)):raise ValueError('Invalid coordinates')
        return dict(type=kind,x=x,y=y,button='right' if c.get('button')=='right' else 'left')
    if kind=='text':
        text=c.get('text')
        if not isinstance(text,str) or len(text)>500 or not text.isascii():raise ValueError('Use ASCII text')
        return dict(type=kind,text=text)
    if kind in ('key','key_down','key_up'):
        key=c.get('key')
        if key not in KEYS:raise ValueError('Unsupported key')
        return dict(type=kind,key=key)
    if kind=='scroll':
        amount=c.get('amount')
        if isinstance(amount,bool) or not isinstance(amount,(int,float)) or not math.isfinite(amount) or amount==0:raise ValueError('Invalid scroll')
        return dict(type=kind,amount=max(-10,min(10,int(amount) or (1 if amount>0 else -1))))
    if kind in ('release','hold'):return dict(type=kind)
    raise ValueError('Unsupported command')

class Controller:
    def __init__(self,pg):self.pg=pg;self.buttons=set();self.keys=set();self.renewed=time.monotonic()
    def move(self,c):
        w,h=self.pg.size()
        # Keep synthetic motion away from the physical top-left emergency corner.
        self.pg.moveTo(max(1,min(w-2,round(c['x']*(w-1)))),max(1,min(h-2,round(c['y']*(h-1)))),duration=0)
    def apply(self,c):
        c=validate(c);kind=c['type'];self.renewed=time.monotonic()
        if kind=='release':self.release();return
        if kind=='hold':return
        if kind in ('move','click','pointer_down','pointer_up'):
            self.move(c);button=c['button']
            if kind=='click':self.pg.click(button=button)
            elif kind=='pointer_down' and button not in self.buttons:self.pg.mouseDown(button=button);self.buttons.add(button)
            elif kind=='pointer_up' and button in self.buttons:self.pg.mouseUp(button=button);self.buttons.discard(button)
        elif kind=='key':self.pg.press('command' if sys.platform=='darwin' and c['key']=='win' else c['key'])
        elif kind=='key_down' and c['key'] not in self.keys:self.pg.keyDown('command' if sys.platform=='darwin' and c['key']=='win' else c['key']);self.keys.add(c['key'])
        elif kind=='key_up' and c['key'] in self.keys:self.pg.keyUp('command' if sys.platform=='darwin' and c['key']=='win' else c['key']);self.keys.discard(c['key'])
        elif kind=='text':self.pg.write(c['text'],interval=.002)
        elif kind=='scroll':self.pg.scroll(c['amount'])
    def tick(self):
        if time.monotonic()-self.renewed>1.25:self.release()
    def release(self):
        if not self.keys and not self.buttons:return
        # Releases must still work when the user has activated PyAutoGUI's failsafe.
        old=self.pg.FAILSAFE;self.pg.FAILSAFE=False
        try:
            for key in list(self.keys):
                try:self.pg.keyUp('command' if sys.platform=='darwin' and key=='win' else key)
                except Exception:pass
            for button in list(self.buttons):
                try:self.pg.mouseUp(button=button)
                except Exception:pass
        finally:self.keys.clear();self.buttons.clear();self.pg.FAILSAFE=old

def cursor_shape():
    try:
        import ctypes,sys
        if sys.platform!='win32':return 'default'
        from ctypes import wintypes
        class Info(ctypes.Structure):
            _fields_=[('cbSize',wintypes.DWORD),('flags',wintypes.DWORD),('hCursor',wintypes.HANDLE),('pos',wintypes.POINT)]
        user=ctypes.windll.user32;user.LoadCursorW.restype=wintypes.HANDLE
        info=Info();info.cbSize=ctypes.sizeof(info)
        if not user.GetCursorInfo(ctypes.byref(info)):return 'default'
        for identity,shape in [(32513,'text'),(32649,'pointer'),(32514,'wait'),(32650,'progress'),(32515,'crosshair'),(32644,'ew-resize'),(32645,'ns-resize'),(32642,'nwse-resize'),(32643,'nesw-resize'),(32646,'move'),(32648,'not-allowed')]:
            if info.hCursor==user.LoadCursorW(None,ctypes.c_void_p(identity)):return shape
    except Exception:pass
    return 'default'
