"""Visible Windows companion with opt-in saved enrollment and sign-in startup."""
import io,platform,threading,time,queue,tkinter as tk,sys,json,tempfile
from pathlib import Path
from tkinter import messagebox
from urllib.parse import urlparse
import requests
import pyautogui as pg
import local_settings
pg.FAILSAFE=True

class Companion:
    def __init__(self,root):
        self.root=root;self.stop=threading.Event();self.allow=threading.Event();self.audio=threading.Event();self.files=threading.Event()
        self.events=queue.Queue();self.credentials=None;self.running=False
        root.title('TyDesk • Remote access enabled only by you');root.geometry('640x700')
        tk.Label(root,text='TyDesk',font=('Segoe UI',26,'bold')).pack(pady=12)
        tk.Label(root,text='Screen sharing companion • close this window to stop').pack()
        self.url=tk.StringVar(value='https://tydesk-broker.onrender.com');self.code=tk.StringVar()
        for label,var in [('Server URL',self.url),('One-use pairing code (first connection)',self.code)]:
            tk.Label(root,text=label).pack(pady=(10,0));tk.Entry(root,textvariable=var,width=68).pack()
        self.control=tk.BooleanVar();self.system_audio=tk.BooleanVar();self.file_permission=tk.BooleanVar();self.unattended=tk.BooleanVar()
        for text,var,event in [('Allow mouse and keyboard control',self.control,self.allow),('Share system playback audio (no microphone)',self.system_audio,self.audio),('Allow file exchange using TyDesk folders',self.file_permission,self.files)]:
            tk.Checkbutton(root,text=text,variable=var,command=lambda v=var,e=event:self.permission(v,e)).pack(anchor='w',padx=35,pady=3)
        tk.Checkbutton(root,text='Pair once and remember this computer',variable=self.unattended,command=self.remember_changed).pack(anchor='w',padx=35,pady=5)
        self.home=Path.home()/'TyDesk';self.home.mkdir(exist_ok=True)
        tk.Label(root,text='Files sent to this PC: '+str(self.home/'Inbox')+'\nFiles available to download: '+str(self.home/'Shared'),wraplength=570).pack(pady=7)
        self.status=tk.StringVar(value='Disconnected • no screen sharing');tk.Label(root,textvariable=self.status,wraplength=570).pack(pady=8)
        self.start=tk.Button(root,text='Start / reconnect',command=self.connect);self.start.pack()
        tk.Button(root,text='Disconnect',command=self.disconnect).pack(pady=5)
        tk.Button(root,text='Forget saved enrollment',command=self.forget).pack()
        tk.Button(root,text='Add TyDesk desktop shortcut',command=self.shortcut).pack(pady=5)
        tk.Button(root,text='Enable start at Windows sign-in',command=self.enable_startup).pack(pady=3)
        tk.Button(root,text='Disable start at Windows sign-in',command=self.disable_startup).pack(pady=3)
        tk.Label(root,text='Keep the app in its current folder after creating a shortcut.\nBefore-login and secure-desktop access are not supported.',fg='#555').pack(pady=8)
        root.protocol('WM_DELETE_WINDOW',self.close);root.after(100,self.poll)
        try:
            saved=local_settings.load()
            if saved:
                self.credentials=saved;self.url.set(saved['url']);self.unattended.set(True)
                for key,var,event in [('control',self.control,self.allow),('audio',self.system_audio,self.audio),('files',self.file_permission,self.files)]:
                    var.set(bool(saved.get(key)));self.permission(var,event,False)
                if '--autostart' in sys.argv:root.after(500,self.connect)
        except Exception as e:self.status.set('Could not load enrollment: '+str(e))
    def config(self):
        return {**self.credentials,'control':self.control.get(),'audio':self.system_audio.get(),'files':self.file_permission.get()}
    def save(self):
        if self.credentials and self.unattended.get():
            try:local_settings.save(self.config())
            except Exception as e:self.status.set('Could not save: '+str(e))
    def permission(self,var,event,persist=True):
        event.set() if var.get() else event.clear()
        if persist:self.save()
    def remember_changed(self):
        if self.unattended.get():
            if not messagebox.askokcancel('Enable unattended reconnect?', 'This Windows user will reconnect and share the screen automatically when TyDesk starts. Enabled control, audio and file permissions will also be remembered. Keep the companion visible; Disconnect stops this session.'):self.unattended.set(False);return
            self.save()
        else:local_settings.forget()
    def poll(self):
        try:
            while True:
                kind,text=self.events.get_nowait()
                if kind=='credentials':self.credentials=text;self.save();continue
                self.status.set(text)
                if kind=='done':self.running=False;self.start.config(state='normal')
        except queue.Empty:pass
        self.root.after(100,self.poll)
    def connect(self):
        if self.running:return
        url=self.url.get().strip().rstrip('/');parsed=urlparse(url)
        if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('','/'):
            messagebox.showerror('Server','Enter an HTTPS origin, with no path or credentials.');return
        if parsed.scheme=='http' and parsed.hostname not in ('localhost','127.0.0.1','::1'):
            messagebox.showerror('HTTPS required','Use HTTPS for another computer.');return
        saved=self.credentials if self.credentials and self.credentials['url']==url else None
        code=self.code.get().strip()
        if not saved and not code:messagebox.showerror('Pairing','Paste a new dashboard pairing code.');return
        if not (saved and self.unattended.get()) and not messagebox.askokcancel('Start screen sharing?', 'The dashboard owner can see your primary display. Only the checked permissions are enabled.'):return
        self.stop=threading.Event();self.start.config(state='disabled');self.running=True
        threading.Thread(target=self.run,args=(url,code,saved,self.unattended.get()),daemon=True).start()
    def run(self,url,code,saved,retry):
        from file_exchange import run as exchange
        from audio_capture import start as start_audio
        stop=self.stop
        client=requests.Session();credentials=saved;failure=None;audio_thread=None;file_thread=None
        try:
            if not credentials:
                r=client.post(url+'/api/enroll',json={'code':code,'name':platform.node()},timeout=10);r.raise_for_status()
                credentials={**r.json(),'url':url};self.events.put(('credentials',credentials))
            identity=credentials['id'];client.headers['Authorization']='Bearer '+credentials['token'];base=f'{url}/api/devices/{identity}'
            self.events.put(('status','Sharing primary display • Disconnect to stop'))
            while not stop.is_set():
                try:
                    shot=pg.screenshot();shot.thumbnail((1600,1000));buf=io.BytesIO();shot.convert('RGB').save(buf,'JPEG',quality=65)
                    if stop.is_set():break
                    r=client.post(base+'/frame',data=buf.getvalue(),headers={'Content-Type':'image/jpeg','X-Allow-Control':'yes' if self.allow.is_set() else 'no','X-Allow-Audio':'yes' if self.audio.is_set() else 'no','X-Allow-Files':'yes' if self.files.is_set() else 'no'},timeout=8)
                    if r.status_code==401:raise PermissionError('Enrollment revoked. Forget saved enrollment and pair again.')
                    r.raise_for_status()
                    if self.audio.is_set() and (audio_thread is None or not audio_thread.is_alive()):
                        audio_thread=start_audio(url,identity,credentials['token'],stop,self.audio,self.events.put)
                    r=client.get(base+'/commands',timeout=8);r.raise_for_status()
                    for c in r.json():
                        if stop.is_set() or not self.allow.is_set():break
                        if c['type']=='click':
                            w,h=pg.size();pg.click(min(w-1,int(c['x']*w)),min(h-1,int(c['y']*h)),button=c['button'])
                        elif c['type']=='text':
                            for character in c['text']:
                                if stop.is_set() or not self.allow.is_set():break
                                pg.write(character,interval=.01)
                        elif c['type']=='key':pg.press(c['key'])
                        elif c['type']=='scroll':pg.scroll(c['amount'])
                    if self.files.is_set() and (file_thread is None or not file_thread.is_alive()):
                        file_thread=threading.Thread(target=self.file_worker,args=(base,credentials['token'],stop),daemon=True);file_thread.start()
                    stop.wait(.25)
                except PermissionError:raise
                except (requests.RequestException,OSError) as e:
                    if not retry:raise
                    self.events.put(('status','Connection interrupted; retrying in 5 seconds: '+str(e)[:100]));stop.wait(5)
        except Exception as e:failure='Stopped: '+str(e)[:220]
        finally:
            stop.set()
            if audio_thread:audio_thread.join(timeout=6)
            if file_thread:file_thread.join(timeout=2)
            if credentials:
                try:client.post(f"{url}/api/devices/{credentials['id']}/disconnect",timeout=5)
                except requests.RequestException:pass
            client.close();self.events.put(('done',failure or 'Disconnected. Click Start to reconnect.'))
    def file_worker(self,base,token,stop):
        from file_exchange import run as exchange
        with requests.Session() as session:
            session.headers['Authorization']='Bearer '+token
            while self.files.is_set() and not stop.is_set():
                try:exchange(session,base,self.home/'Shared',self.home/'Inbox',self.files,stop)
                except Exception as e:self.events.put(('status','File exchange: '+str(e)[:160]))
                stop.wait(3)
    def shortcut(self):
        try:
            import native_shell
            native_shell.desktop_shortcut();self.status.set('TyDesk shortcut added to your desktop.')
        except Exception as e:messagebox.showerror('Shortcut',str(e))
    def enable_startup(self):
        if not self.credentials or not self.unattended.get():
            messagebox.showerror('Pair first','Pair once and enable Remember this computer first.');return
        if not messagebox.askokcancel('Start at Windows sign-in?', 'TyDesk will open visibly and reconnect using your remembered screen/control/audio/file permissions whenever this Windows user signs in.'):return
        try:
            import native_shell
            native_shell.startup(True);self.status.set('Windows sign-in startup enabled. The app remains visible.')
        except Exception as e:messagebox.showerror('Startup',str(e))
    def disable_startup(self):
        try:
            import native_shell
            native_shell.startup(False);self.status.set('Windows sign-in startup disabled.')
        except Exception as e:messagebox.showerror('Startup',str(e))
    def disconnect(self):self.stop.set();self.status.set('Disconnecting…')
    def forget(self):
        self.disconnect();local_settings.forget();self.credentials=None;self.unattended.set(False)
        self.status.set('Enrollment forgotten. Also Revoke the device in your dashboard.')
    def close(self):self.disconnect();self.root.after(500,self.root.destroy)

if __name__=='__main__':
    if '--self-test' in sys.argv:
        output=Path(sys.argv[sys.argv.index('--self-test')+1])
        try:
            with tempfile.TemporaryDirectory() as temp:
                local_settings.ROOT=Path(temp)
                sample={'id':'build-smoke-test','token':'not-a-real-credential','url':'https://example.test'}
                local_settings.save(sample);assert local_settings.load()==sample;local_settings.forget()
            root=tk.Tk();root.withdraw();root.update();root.destroy()
            import native_shell
            import soundcard
            output.write_text(json.dumps({'ok':True,'tk':True,'dpapi':True,'audio_module':True}))
            sys.exit(0)
        except Exception as exc:
            output.write_text(json.dumps({'ok':False,'error':str(exc)}));sys.exit(1)
    # Single instance per Windows user: duplicate sign-in tasks cannot share twice.
    mutex=None
    if sys.platform=='win32':
        import ctypes
        mutex=ctypes.windll.kernel32.CreateMutexW(None,False,'Local\\TyDeskCompanion')
        if ctypes.windll.kernel32.GetLastError()==183:sys.exit(0)
    root=tk.Tk();Companion(root);root.mainloop()
