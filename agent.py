"""Visible Windows companion with opt-in saved enrollment and sign-in startup."""
import io,platform,threading,time,queue,tkinter as tk,sys,json,tempfile
from pathlib import Path
from tkinter import messagebox, ttk
from urllib.parse import urlparse
import requests
import pyautogui as pg
import local_settings
pg.FAILSAFE=True

class Companion:
    def __init__(self,root):
        self.root=root;self.stop=threading.Event();self.allow=threading.Event();self.audio=threading.Event();self.files=threading.Event()
        self.events=queue.Queue();self.credentials=None;self.running=False
        self.tray=None;self.tray_ready=threading.Event();self.exiting=False
        self.build_ui(root)
        root.protocol('WM_DELETE_WINDOW',self.close);root.after(100,self.poll)
        try:
            saved=local_settings.load()
            if saved:
                self.credentials=saved;self.url.set(saved['url']);self.unattended.set(True);self.background.set(bool(saved.get('background',False)))
                for key,var,event in [('control',self.control,self.allow),('audio',self.system_audio,self.audio),('files',self.file_permission,self.files)]:
                    var.set(bool(saved.get(key)));self.permission(var,event,False)
                root.after(500,self.connect)
        except Exception as e:self.status.set('Could not load enrollment: '+str(e))
    def build_ui(self,root):
        bg='#0c1422';panel='#152237';ink='#eef5ff';muted='#9fb2cb';mint='#51e2c0'
        root.title('TyDesk — Companion');root.geometry('740x840');root.minsize(640,640);root.configure(bg=bg)
        root.option_add('*Font',('Segoe UI',10))
        style=ttk.Style(root);style.theme_use('clam')
        style.configure('TCheckbutton',background=panel,foreground=ink,padding=7,indicatorbackground='#273a53',indicatorforeground=mint)
        style.map('TCheckbutton',background=[('active',panel)],indicatorbackground=[('selected',mint)])
        header=tk.Frame(root,bg=bg);header.pack(fill='x',padx=30,pady=(24,14))
        tk.Label(header,text='TyDesk',bg=bg,fg=ink,font=('Segoe UI',30,'bold')).pack(side='left')
        tk.Label(header,text='WINDOWS COMPANION  /  3.0',bg=bg,fg=mint,font=('Segoe UI',9,'bold')).pack(side='right')
        tk.Label(root,text='Your computer. Within reach.',bg=bg,fg=ink,font=('Segoe UI',18,'bold')).pack(anchor='w',padx=30)
        tk.Label(root,text='Connect once, then return from your device dashboard.',bg=bg,fg=muted).pack(anchor='w',padx=30,pady=(4,14))
        # Scroll the settings on smaller screens; connection controls stay accessible.
        holder=tk.Frame(root,bg=bg);holder.pack(fill='both',expand=True,padx=24)
        canvas=tk.Canvas(holder,bg=bg,highlightthickness=0);scroll=ttk.Scrollbar(holder,orient='vertical',command=canvas.yview)
        scroll.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True);canvas.configure(yscrollcommand=scroll.set)
        body=tk.Frame(canvas,bg=bg);window=canvas.create_window((0,0),window=body,anchor='nw')
        body.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(window,width=e.width))
        root.bind('<MouseWheel>',lambda e:canvas.yview_scroll(int(-e.delta/120),'units'))
        def card(title,subtitle):
            f=tk.Frame(body,bg=panel,highlightbackground='#293b53',highlightthickness=1,padx=20,pady=16);f.pack(fill='x',pady=(0,12))
            tk.Label(f,text=title,bg=panel,fg=ink,font=('Segoe UI',12,'bold')).pack(anchor='w')
            tk.Label(f,text=subtitle,bg=panel,fg=muted,wraplength=585,justify='left').pack(anchor='w',pady=(3,10));return f
        def button(parent,text,command,primary=False):
            return tk.Button(parent,text=text,command=command,bg=mint if primary else '#273a53',fg='#082b23' if primary else ink,
                activebackground='#77eed2' if primary else '#334b69',activeforeground='#082b23' if primary else ink,
                relief='flat',borderwidth=0,padx=15,pady=10,cursor='hand2',font=('Segoe UI',10,'bold'))
        self.url=tk.StringVar(value='https://tydesk-broker.onrender.com');self.code=tk.StringVar()
        f=card('01  Connect this computer','Use a one-use code or your reusable connection passcode. Leave blank to reconnect a remembered device.')
        for label,var,secret in [('Server address',self.url,False),('Pairing code or connection passcode',self.code,True)]:
            tk.Label(f,text=label,bg=panel,fg=muted,font=('Segoe UI',9)).pack(anchor='w',pady=(4,4))
            tk.Entry(f,textvariable=var,show='•' if secret else '',bg='#0d1829',fg=ink,insertbackground=mint,relief='flat',highlightthickness=1,highlightbackground='#344964',highlightcolor=mint,font=('Segoe UI',11)).pack(fill='x',ipady=8,pady=(0,5))
        self.control=tk.BooleanVar();self.system_audio=tk.BooleanVar();self.file_permission=tk.BooleanVar();self.unattended=tk.BooleanVar();self.background=tk.BooleanVar()
        f=card('02  Choose what to share','Permissions apply only to this computer. You can disconnect at any time.')
        for text,var,event in [('Mouse and keyboard control',self.control,self.allow),('System playback audio · no microphone',self.system_audio,self.audio),('Files in TyDesk Shared and Inbox folders',self.file_permission,self.files)]:
            ttk.Checkbutton(f,text=text,variable=var,command=lambda v=var,e=event:self.permission(v,e)).pack(anchor='w')
        ttk.Checkbutton(f,text='Remember this computer and reconnect automatically',variable=self.unattended,command=self.remember_changed).pack(anchor='w')
        ttk.Checkbutton(f,text='Keep available in the tray when I close this window',variable=self.background,command=self.background_changed).pack(anchor='w')
        f=card('03  Make it easy to return','Tray menu: Open TyDesk, Connect, Disconnect, or Quit TyDesk.')
        row=tk.Frame(f,bg=panel);row.pack(fill='x')
        button(row,'Desktop shortcut',self.shortcut).pack(side='left',padx=(0,8))
        button(row,'Enable sign-in start',self.enable_startup).pack(side='left',padx=(0,8))
        button(row,'Disable',self.disable_startup).pack(side='left')
        button(f,'Forget this computer',self.forget).pack(anchor='w',pady=(12,0))
        self.home=Path.home()/'TyDesk';self.home.mkdir(exist_ok=True)
        tk.Label(f,text='Received files: '+str(self.home/'Inbox')+'\nShared files: '+str(self.home/'Shared'),bg=panel,fg=muted,justify='left',wraplength=570,font=('Segoe UI',9)).pack(anchor='w',pady=(12,0))
        footer=tk.Frame(root,bg=panel,padx=24,pady=15);footer.pack(fill='x',pady=(12,0))
        self.status=tk.StringVar(value='Ready to connect · your screen is not being shared')
        tk.Label(footer,textvariable=self.status,bg=panel,fg=mint,wraplength=650,justify='left').pack(anchor='w',pady=(0,10))
        row=tk.Frame(footer,bg=panel);row.pack(fill='x')
        self.start=button(row,'Connect computer',self.connect,True);self.start.pack(side='left',padx=(0,10))
        button(row,'Disconnect',self.disconnect).pack(side='left')
        button(row,'Quit TyDesk',self.quit).pack(side='right')
        tk.Label(footer,text='Available after Windows sign-in while the PC is awake. Lock screen and UAC are not supported.',bg=panel,fg=muted,wraplength=650,font=('Segoe UI',8)).pack(anchor='w',pady=(10,0))
    def background_changed(self):
        if self.background.get():
            if not messagebox.askokcancel('Keep remote access available?', 'Closing the window will leave TyDesk running with a visible tray icon and your selected sharing permissions. Use Disconnect or Quit TyDesk from the tray to stop access.'):
                self.background.set(False);return
            self.ensure_tray()
        self.save()
    def ensure_tray(self):
        if self.tray:return
        try:
            import pystray
            from PIL import Image,ImageDraw
            image=Image.new('RGB',(64,64),'#152237');draw=ImageDraw.Draw(image)
            draw.rounded_rectangle((8,10,56,45),radius=7,outline='#51e2c0',width=5);draw.line((32,45,32,54),fill='#51e2c0',width=4);draw.line((22,54,42,54),fill='#51e2c0',width=4)
            def action(kind):return lambda icon,item:self.events.put(('action',kind))
            self.tray=pystray.Icon('TyDesk',image,'TyDesk — remote access companion',pystray.Menu(
                pystray.MenuItem('Open TyDesk',action('show'),default=True),pystray.MenuItem('Connect',action('connect')),
                pystray.MenuItem('Disconnect',action('disconnect')),pystray.MenuItem('Quit TyDesk',action('quit'))))
            def setup(icon):icon.visible=True;self.tray_ready.set()
            def run():
                try:self.tray.run(setup)
                except Exception:self.events.put(('tray_error','Tray could not start. The window will remain open.'))
            threading.Thread(target=run,daemon=True).start()
        except Exception as e:self.events.put(('tray_error','Tray unavailable: '+str(e)))
    def show(self):
        self.root.deiconify();self.root.lift();self.root.focus_force()
    def config(self):
        return {**self.credentials,'control':self.control.get(),'audio':self.system_audio.get(),'files':self.file_permission.get(),'background':self.background.get()}
    def save(self):
        if self.credentials and self.unattended.get():
            try:local_settings.save(self.config())
            except Exception as e:self.status.set('Could not save: '+str(e))
    def permission(self,var,event,persist=True):
        event.set() if var.get() else event.clear()
        if persist:self.save()
    def remember_changed(self):
        if self.unattended.get():
            if not messagebox.askokcancel('Enable unattended reconnect?', 'This Windows user will reconnect and share the screen automatically when TyDesk starts. Enabled control, audio and file permissions will also be remembered. TyDesk remains visible as a window or tray icon; Disconnect stops this session.'):self.unattended.set(False);return
            self.save()
        else:local_settings.forget()
    def poll(self):
        try:
            while True:
                kind,text=self.events.get_nowait()
                if kind=='action':getattr(self,text)();continue
                if kind=='tray_error':self.background.set(False);self.tray=None;self.tray_ready.clear();self.show();self.save()
                if kind=='credentials':self.credentials=text;self.code.set('');self.save();continue
                if kind=='revoked':
                    self.credentials=None;local_settings.forget();self.show()
                if kind=='done':self.show() if text.startswith('Stopped:') else None
                self.status.set(text)
                if kind=='done':self.running=False;self.start.config(state='normal')
        except queue.Empty:pass
        if getattr(self,'show_event',None):
            import ctypes
            if ctypes.windll.kernel32.WaitForSingleObject(self.show_event,0)==0:self.show()
        if not self.exiting:self.root.after(100,self.poll)
    def connect(self):
        if self.running:return
        url=self.url.get().strip().rstrip('/');parsed=urlparse(url)
        if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('','/'):
            messagebox.showerror('Server','Enter an HTTPS origin, with no path or credentials.');return
        if parsed.scheme=='http' and parsed.hostname not in ('localhost','127.0.0.1','::1'):
            messagebox.showerror('HTTPS required','Use HTTPS for another computer.');return
        code=self.code.get().strip()
        saved=self.credentials if not code and self.credentials and self.credentials['url']==url else None
        if not saved and not code:messagebox.showerror('Pairing','Paste a dashboard pairing code or your reusable connection passcode.');return
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
                r=client.post(url+'/api/enroll',json={'code':code,'name':platform.node()},timeout=90)
                if r.status_code in (401,403):raise ValueError('Code expired or passcode incorrect. Paste a new code or check your connection passcode.')
                if r.status_code==429:raise ValueError('Too many connection attempts. Wait one minute and try again.')
                r.raise_for_status()
                credentials={**r.json(),'url':url};self.events.put(('credentials',credentials))
            identity=credentials['id'];client.headers['Authorization']='Bearer '+credentials['token'];base=f'{url}/api/devices/{identity}'
            self.events.put(('status','Sharing primary display • Disconnect to stop'))
            while not stop.is_set():
                try:
                    shot=pg.screenshot();shot.thumbnail((1600,1000));buf=io.BytesIO();shot.convert('RGB').save(buf,'JPEG',quality=65)
                    if stop.is_set():break
                    r=client.post(base+'/frame',data=buf.getvalue(),headers={'Content-Type':'image/jpeg','X-Allow-Control':'yes' if self.allow.is_set() else 'no','X-Allow-Audio':'yes' if self.audio.is_set() else 'no','X-Allow-Files':'yes' if self.files.is_set() else 'no'},timeout=8)
                    if r.status_code==401:raise PermissionError('Saved connection no longer exists. Paste a new pairing code or your reusable passcode, then Connect.')
                    r.raise_for_status()
                    if self.audio.is_set() and (audio_thread is None or not audio_thread.is_alive()):
                        audio_thread=start_audio(url,identity,credentials['token'],stop,self.audio,self.events.put)
                    r=client.get(base+'/commands',timeout=8)
                    if r.status_code==401:raise PermissionError('Saved connection was revoked. Enter a new code or connection passcode.')
                    r.raise_for_status()
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
        except PermissionError as e:
            self.events.put(('revoked','Saved connection cleared. '+str(e)));failure='Stopped: '+str(e)[:220]
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
        if not messagebox.askokcancel('Start at Windows sign-in?', 'TyDesk will open and reconnect using your remembered screen/control/audio/file permissions whenever this Windows user signs in.'):return
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
    def close(self):
        if self.background.get():
            self.ensure_tray()
            if not self.tray_ready.is_set():
                self.status.set('Starting the tray icon. Please close the window again in a moment.');return
            self.save();self.root.withdraw()
            try:self.tray.notify('TyDesk is still available. Use the tray menu to open, disconnect, or quit.','TyDesk')
            except Exception:pass
        else:self.quit()
    def quit(self):
        self.exiting=True;self.disconnect()
        if self.tray:self.tray.stop()
        self.root.after(600,self.root.destroy)

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
            import pystray
            test_root=tk.Tk();test_app=Companion(test_root);test_root.update();test_app.ensure_tray()
            assert test_app.tray_ready.wait(10),'Tray failed to initialize'
            test_app.background.set(True);test_app.close();test_root.update();assert test_root.state()=='withdrawn'
            test_app.show();test_root.update();assert test_root.state()=='normal'
            test_app.quit();test_root.update();test_root.destroy()
            output.write_text(json.dumps({'ok':True,'tk':True,'dpapi':True,'audio_module':True,'ui':True,'tray':True}))
            sys.exit(0)
        except Exception as exc:
            output.write_text(json.dumps({'ok':False,'error':str(exc)}));sys.exit(1)
    # A second launch brings the existing window back from the tray.
    mutex=None;show_event=None
    if sys.platform=='win32':
        import ctypes
        from ctypes import wintypes
        kernel=ctypes.windll.kernel32
        kernel.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR];kernel.CreateMutexW.restype=wintypes.HANDLE
        kernel.CreateEventW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.BOOL,wintypes.LPCWSTR];kernel.CreateEventW.restype=wintypes.HANDLE
        kernel.SetEvent.argtypes=[wintypes.HANDLE];kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
        mutex=kernel.CreateMutexW(None,False,'Local\\TyDeskCompanion');already=kernel.GetLastError()==183
        show_event=kernel.CreateEventW(None,False,False,'Local\\TyDeskShowCompanion')
        if already:kernel.SetEvent(show_event);sys.exit(0)
    root=tk.Tk();companion=Companion(root);companion.show_event=show_event;root.mainloop()
