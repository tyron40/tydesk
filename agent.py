"""Visible desktop companion with opt-in saved enrollment and sign-in startup."""
import io,platform,threading,time,queue,tkinter as tk,sys,json,tempfile
from pathlib import Path
from tkinter import messagebox, ttk
from urllib.parse import urlparse
import requests
import pyautogui as pg
import desktop_runtime
import local_settings
import remote_input
pg.FAILSAFE=True
pg.PAUSE=0
DEFAULT_SERVER='https://zdesk-nnym.onrender.com'

class Companion:
    def __init__(self,root,restore=True):
        self.root=root;self.stop=threading.Event();self.allow=threading.Event();self.audio=threading.Event();self.mic=threading.Event();self.files=threading.Event();self.camera=threading.Event()
        self.events=queue.Queue();self.credentials=None;self.running=False
        self.tray=None;self.tray_ready=threading.Event();self.exiting=False
        self.build_ui(root)
        root.protocol('WM_DELETE_WINDOW',self.close);root.after(100,self.poll)
        try:
            saved=local_settings.load() if restore else None
            if saved:
                self.credentials=saved;self.url.set(saved['url']);self.unattended.set(True);self.background.set(bool(saved.get('background',False)))
                for key,var,event in [('control',self.control,self.allow),('audio',self.system_audio,self.audio),('microphone',self.microphone,self.mic),('files',self.file_permission,self.files),('camera',self.camera_permission,self.camera)]:
                    var.set(bool(saved.get(key)) and (key!='audio' or desktop_runtime.system_audio_available()));self.permission(var,event,False)
                root.after(500,self.connect)
        except Exception as e:self.status.set('Could not load enrollment: '+str(e))
    def build_ui(self,root):
        bg='#0c1422';panel='#152237';ink='#eef5ff';muted='#9fb2cb';mint='#51e2c0'
        root.title('ZDesk — Companion');root.geometry('740x840');root.minsize(640,640);root.configure(bg=bg)
        root.option_add('*Font',('Segoe UI',10))
        style=ttk.Style(root);style.theme_use('clam')
        style.configure('TCheckbutton',background=panel,foreground=ink,padding=7,indicatorbackground='#273a53',indicatorforeground=mint)
        style.map('TCheckbutton',background=[('active',panel)],indicatorbackground=[('selected',mint)])
        header=tk.Frame(root,bg=bg);header.pack(fill='x',padx=30,pady=(24,14))
        tk.Label(header,text='ZDesk',bg=bg,fg=ink,font=('Segoe UI',30,'bold')).pack(side='left')
        tk.Label(header,text=desktop_runtime.label()+' COMPANION  /  '+desktop_runtime.VERSION,bg=bg,fg=mint,font=('Segoe UI',9,'bold')).pack(side='right')
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
        self.url=tk.StringVar(value=DEFAULT_SERVER);self.code=tk.StringVar()
        f=card('01  Connect this computer','Use a one-use code or your reusable connection passcode. Leave blank to reconnect a remembered device.')
        for label,var,secret in [('Server address',self.url,False),('Pairing code or connection passcode',self.code,True)]:
            tk.Label(f,text=label,bg=panel,fg=muted,font=('Segoe UI',9)).pack(anchor='w',pady=(4,4))
            tk.Entry(f,textvariable=var,show='•' if secret else '',bg='#0d1829',fg=ink,insertbackground=mint,relief='flat',highlightthickness=1,highlightbackground='#344964',highlightcolor=mint,font=('Segoe UI',11)).pack(fill='x',ipady=8,pady=(0,5))
        self.camera_permission=tk.BooleanVar();self.camera_status=tk.StringVar(value="Camera off · automatically selects an available camera");self.control=tk.BooleanVar();self.system_audio=tk.BooleanVar();self.microphone=tk.BooleanVar();self.file_permission=tk.BooleanVar();self.unattended=tk.BooleanVar();self.background=tk.BooleanVar()
        f=card('02  Choose what to share','Permissions apply only to this computer. You can disconnect at any time.')
        choices=tk.Frame(f,bg=panel);choices.pack(fill='x',pady=(0,8))
        button(choices,'Select all sharing features',self.select_all_sharing).pack(side='left',padx=(0,8))
        button(choices,'Clear selections',lambda:self.select_all_sharing(False)).pack(side='left')
        tk.Label(f,text='Connect shares your primary display and checked features with the paired dashboard. Camera shows surroundings; microphone shares nearby conversations. Select all chooses these permissions without starting a disconnected session. Changes apply immediately while connected. Stop camera or Clear selections stops optional sharing; Disconnect or Quit also stops the screen.',bg=panel,fg=muted,wraplength=580,justify='left').pack(anchor='w',pady=(0,8))
        for text,var,event in [('Mouse and keyboard control',self.control,self.allow),('System playback audio · PC sounds',self.system_audio,self.audio),('Microphone · surrounding sound',self.microphone,self.mic),('Files in ZDesk Shared and Inbox folders',self.file_permission,self.files)]:
            item=ttk.Checkbutton(f,text=text,variable=var,command=lambda v=var,e=event:self.permission(v,e));item.pack(anchor='w')
            if var is self.system_audio and not desktop_runtime.system_audio_available():item.configure(state='disabled')
        ttk.Checkbutton(f,text='Camera · share surroundings (saved with remembered pairing)',variable=self.camera_permission,command=self.camera_changed).pack(anchor='w')
        camera_row=tk.Frame(f,bg=panel);camera_row.pack(fill='x',pady=5)
        button(camera_row,'Stop camera',self.stop_camera).pack(side='left')
        tk.Label(f,textvariable=self.camera_status,bg=panel,fg=mint,wraplength=580,justify='left').pack(anchor='w')
        ttk.Checkbutton(f,text='Remember this computer and reconnect automatically',variable=self.unattended,command=self.remember_changed).pack(anchor='w')
        ttk.Checkbutton(f,text='Keep available in the tray when I close this window',variable=self.background,command=self.background_changed).pack(anchor='w')
        tk.Label(f,text='Remember saves all checked permissions, including camera and microphone, for automatic reconnect. Tray mode keeps selected sharing running after closing the window, with a visible tray indicator. Enable sign-in start also reconnects when this user signs in.',bg=panel,fg=muted,wraplength=580,justify='left').pack(anchor='w',pady=(6,0))
        f=card('03  Make it easy to return','Tray menu: Open ZDesk, Connect, Disconnect, or Quit ZDesk.')
        row=tk.Frame(f,bg=panel);row.pack(fill='x')
        button(row,'Desktop shortcut',self.shortcut).pack(side='left',padx=(0,8))
        button(row,'Enable sign-in start',self.enable_startup).pack(side='left',padx=(0,8))
        button(row,'Disable',self.disable_startup).pack(side='left')
        button(f,'Forget this computer',self.forget).pack(anchor='w',pady=(12,0))
        self.home=(Path.home()/'TyDesk') if (Path.home()/'TyDesk').exists() else Path.home()/'ZDesk';self.home.mkdir(exist_ok=True)
        tk.Label(f,text='Received files: '+str(self.home/'Inbox')+'\nShared files: '+str(self.home/'Shared'),bg=panel,fg=muted,justify='left',wraplength=570,font=('Segoe UI',9)).pack(anchor='w',pady=(12,0))
        footer=tk.Frame(root,bg=panel,padx=24,pady=15);footer.pack(fill='x',pady=(12,0))
        self.status=tk.StringVar(value='Ready to connect · your screen is not being shared')
        tk.Label(footer,textvariable=self.status,bg=panel,fg=mint,wraplength=650,justify='left').pack(anchor='w',pady=(0,10))
        row=tk.Frame(footer,bg=panel);row.pack(fill='x')
        self.start=button(row,'Connect computer',self.connect,True);self.start.pack(side='left',padx=(0,10))
        button(row,'Disconnect',self.disconnect).pack(side='left')
        button(row,'Quit ZDesk',self.quit).pack(side='right')
        tk.Label(footer,text=desktop_runtime.guidance(),bg=panel,fg=muted,wraplength=650,font=('Segoe UI',8)).pack(anchor='w',pady=(10,0))
    def sharing_options(self):
        return [(self.control,self.allow)]+([(self.system_audio,self.audio)] if desktop_runtime.system_audio_available() else [])+[(self.microphone,self.mic),(self.file_permission,self.files),(self.camera_permission,self.camera)]
    def select_all_sharing(self,enabled=True):
        for var,event in self.sharing_options():
            var.set(enabled);event.set() if enabled else event.clear()
        self.camera_status.set('Camera selected · automatic detection when connected' if enabled else 'Camera off')
        if self.tray:self.tray.title='ZDesk — camera ON' if enabled and self.running else 'ZDesk — remote access companion'
        self.save()
    def camera_changed(self):
        if self.camera_permission.get():
            self.camera.set();self.camera_status.set('Camera selected · automatic camera detection when connected');self.save()
        else:self.stop_camera()
    def stop_camera(self):
        self.camera.clear();self.camera_permission.set(False);self.camera_status.set('Camera off')
        if self.tray:self.tray.title='ZDesk — remote access companion'
        self.save()
    def background_changed(self):
        if self.background.get():self.ensure_tray()
        self.save()
    def ensure_tray(self):
        if self.tray:return
        try:
            import pystray
            from PIL import Image,ImageDraw
            image=Image.new('RGB',(64,64),'#152237');draw=ImageDraw.Draw(image)
            draw.rounded_rectangle((8,10,56,45),radius=7,outline='#51e2c0',width=5);draw.line((32,45,32,54),fill='#51e2c0',width=4);draw.line((22,54,42,54),fill='#51e2c0',width=4)
            def action(kind):return lambda icon,item:self.events.put(('action',kind))
            self.tray=pystray.Icon('ZDesk',image,'ZDesk — remote access companion',pystray.Menu(
                pystray.MenuItem('Open ZDesk',action('show'),default=True),pystray.MenuItem('Connect',action('connect')),
                pystray.MenuItem('Disconnect',action('disconnect')),pystray.MenuItem('Quit ZDesk',action('quit'))))
            def setup(icon):icon.visible=True;self.tray_ready.set()
            def run():
                try:self.tray.run(setup)
                except Exception:self.events.put(('tray_error','Tray could not start. The window will remain open.'))
            if sys.platform=='darwin':self.tray.run_detached(setup)
            else:threading.Thread(target=run,daemon=True).start()
        except Exception as e:self.events.put(('tray_error','Tray unavailable: '+str(e)))
    def show(self):
        self.root.deiconify();self.root.lift();self.root.focus_force()
    def config(self):
        return {**self.credentials,'control':self.control.get(),'audio':self.system_audio.get(),'microphone':self.microphone.get(),'files':self.file_permission.get(),'camera':self.camera_permission.get(),'background':self.background.get()}
    def save(self):
        if self.credentials and self.unattended.get():
            try:local_settings.save(self.config())
            except Exception as e:self.status.set('Could not save: '+str(e))
    def permission(self,var,event,persist=True):
        event.set() if var.get() else event.clear()
        if persist:self.save()
    def remember_changed(self):
        if self.unattended.get():self.save()
        else:local_settings.forget()
    def poll(self):
        try:
            while True:
                kind,text=self.events.get_nowait()
                if kind=='camera_status':
                    self.camera_status.set(text)
                    if self.tray:self.tray.title='ZDesk — camera ON' if self.camera.is_set() else 'ZDesk — remote access companion'
                    continue
                if kind=='camera_done':
                    self.camera_status.set('Camera stopped · saved selection applies on next Connect');continue
                if kind=='camera_error':
                    self.camera.clear();self.camera_status.set('Camera error: '+text)
                    if self.tray:self.tray.title='ZDesk — remote access companion'
                    continue
                if kind=='action':getattr(self,text)();continue
                if kind=='control_error':self.control.set(False);self.save()
                if kind=='tray_error':self.background.set(False);self.tray=None;self.tray_ready.clear();self.show();self.save()
                if kind=='credentials':
                    self.credentials=text;self.code.set('');self.save()
                    if getattr(self,'terminal_pairing',False):
                        try:local_settings.save_terminal(text)
                        except Exception:
                            self.root.after(0,lambda:messagebox.showwarning('Terminal pairing','Connected, but could not remember pairing with Windows DPAPI.'))
                    continue
                if kind=='uninstall':self.confirm_uninstall(text);continue
                if kind=='revoked':
                    self.credentials=None;self.forget_saved_pairing();self.show()
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
        if self.camera_permission.get():self.camera.set()
        self.control_failure=None;self.stop=threading.Event();self.start.config(state='disabled');self.running=True
        threading.Thread(target=self.run,args=(url,code,saved,self.unattended.get()),daemon=True).start()
    def run(self,url,code,saved,retry):
        from file_exchange import run as exchange
        from audio_capture import start as start_audio
        stop=self.stop
        client=requests.Session();credentials=saved;failure=None;audio_thread=None;file_thread=None;input_thread=None;camera_thread=None
        try:
            if not credentials:
                r=client.post(url+'/api/enroll',json={'code':code,'name':platform.node()},timeout=(5,15) if getattr(self,'console_mode',False) else 90)
                if r.status_code in (401,403):raise ValueError('Code expired or passcode incorrect. Paste a new code or check your connection passcode.')
                if r.status_code==429:raise ValueError('Too many connection attempts. Wait one minute and try again.')
                r.raise_for_status()
                credentials={**r.json(),'url':url};self.events.put(('credentials',credentials))
            identity=credentials['id'];client.headers['Authorization']='Bearer '+credentials['token'];base=f'{url}/api/devices/{identity}'
            input_thread=threading.Thread(target=self.input_worker,args=(base,credentials['token'],stop),daemon=True);input_thread.start()
            self.events.put(('status','Sharing primary display • Disconnect to stop'))
            while not stop.is_set():
                try:
                    shot=desktop_runtime.screenshot(pg);shot.thumbnail((1600,1000));buf=io.BytesIO();shot.convert('RGB').save(buf,'JPEG',quality=65)
                    if stop.is_set():break
                    r=client.post(base+'/frame',data=buf.getvalue(),headers={'Content-Type':'image/jpeg','X-Allow-Camera':'yes' if self.camera.is_set() else 'no','X-Allow-Control':'yes' if self.allow.is_set() else 'no','X-Allow-Audio':'yes' if self.audio.is_set() or self.mic.is_set() else 'no','X-Allow-Files':'yes' if self.files.is_set() else 'no','X-TyDesk-Protocol':'2','X-Remote-Cursor':remote_input.cursor_shape(),'X-Companion-Platform':desktop_runtime.platform_id(),'X-Companion-Removal':'1' if sys.platform=='win32' and getattr(sys,'frozen',False) else '0'},timeout=8)
                    if r.status_code==401:raise PermissionError('Saved connection no longer exists. Paste a new pairing code or your reusable passcode, then Connect.')
                    r.raise_for_status()
                    if getattr(self,'console_mode',False) and not getattr(self,'console_connected',False):
                        self.console_connected=True;self.events.put(('connected','Primary display is sharing. Ctrl+C stops.'))
                    if self.camera.is_set() and (camera_thread is None or not camera_thread.is_alive()):
                        from camera_capture import start as start_camera
                        camera_thread=start_camera(base,credentials['token'],stop,self.camera,self.events.put)
                    if (self.audio.is_set() or self.mic.is_set()) and (audio_thread is None or not audio_thread.is_alive()):
                        audio_thread=start_audio(url,identity,credentials['token'],stop,self.audio,self.events.put,microphone=self.mic)
                    if self.files.is_set() and (file_thread is None or not file_thread.is_alive()):
                        file_thread=threading.Thread(target=self.file_worker,args=(base,credentials['token'],stop),daemon=True);file_thread.start()
                    stop.wait(.12)
                except PermissionError:raise
                except (requests.RequestException,OSError) as e:
                    if not retry:raise
                    self.events.put(('status','Connection interrupted; retrying in 5 seconds: '+str(e)[:100]));stop.wait(5)
        except PermissionError as e:
            self.events.put(('revoked','Saved connection cleared. '+str(e)));failure='Stopped: '+str(e)[:220]
        except Exception as e:failure='Stopped: '+str(e)[:220]
        finally:
            stop.set()
            self.camera.clear()
            self.events.put(('camera_done','Camera stopped'))
            if camera_thread:camera_thread.join(timeout=2)
            if input_thread:input_thread.join(timeout=2)
            if audio_thread:audio_thread.join(timeout=2)
            if file_thread:file_thread.join(timeout=2)
            if credentials:
                try:client.post(f"{url}/api/devices/{credentials['id']}/disconnect",timeout=5)
                except requests.RequestException:pass
            client.close();self.events.put(('done',failure or getattr(self,'control_failure',None) or 'Disconnected. Click Start to reconnect.'))
    def input_worker(self,base,token,stop):
        controller=remote_input.Controller(pg)
        management_at=0
        with requests.Session() as session:
            session.headers['Authorization']='Bearer '+token
            try:
                while not stop.is_set():
                    if not self.allow.is_set():controller.release();stop.wait(.1);continue
                    try:
                        if time.monotonic()-management_at>1:
                            management_at=time.monotonic()
                            removal=session.get(base+'/removal',timeout=(.75,.75))
                            if removal.ok and removal.json():self.events.put(('uninstall',removal.json()))
                        r=session.get(base+'/commands',timeout=(.75,.75))
                        if r.status_code==401:
                            self.events.put(('revoked','Saved connection revoked. Enter a new code.'));stop.set();break
                        r.raise_for_status()
                        for command in r.json():
                            if stop.is_set() or not self.allow.is_set():break
                            controller.apply(command)
                        controller.tick()
                    except requests.RequestException:controller.release()
                    stop.wait(.04)
            except Exception as exc:
                self.allow.clear();self.control_failure='Stopped: remote control stopped. '+str(exc)[:140];self.events.put(('control_error',self.control_failure));stop.set()
            finally:controller.release()
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
            native_shell.desktop_shortcut();self.status.set('ZDesk shortcut added to your desktop.')
        except Exception as e:messagebox.showerror('Shortcut',str(e))
    def confirm_uninstall(self,job):
        if not self.running or not self.allow.is_set() or not self.credentials:return
        self.show()
        credentials=dict(self.credentials)
        base=credentials['url']+'/api/devices/'+credentials['id']+'/removal'
        def report(state):
            def send():
                try:requests.post(base,headers={'Authorization':'Bearer '+credentials['token']},json={'id':job['id'],'state':state},timeout=8)
                except requests.RequestException:pass
            threading.Thread(target=send,daemon=False).start()
        if not messagebox.askyesno('Uninstall ZDesk?', 'Your dashboard requested removal of this companion. Remove its sign-in startup, desktop shortcuts and saved pairing, then move this running EXE to the Recycle Bin? Shared and received files stay on this PC.'):
            report('cancelled');return
        try:
            import native_shell
            native_shell.remove_companion()
            self.stop.set();local_settings.forget();self.credentials=None;self.unattended.set(False)
            report('removal_started');self.status.set('Removing ZDesk. Check the Recycle Bin to verify removal.');self.quit()
        except Exception as e:
            report('failed');messagebox.showerror('Removal failed',str(e))
    def enable_startup(self):
        if not self.credentials or not self.unattended.get():
            messagebox.showerror('Pair first','Pair once and enable Remember this computer first.');return
        try:
            import native_shell
            native_shell.startup(True);self.status.set('Sign-in startup enabled. The app remains visible.')
        except Exception as e:messagebox.showerror('Startup',str(e))
    def disable_startup(self):
        try:
            import native_shell
            native_shell.startup(False);self.status.set('Sign-in startup disabled.')
        except Exception as e:messagebox.showerror('Startup',str(e))
    def disconnect(self):
        self.camera.clear();self.stop.set();self.camera_status.set('Camera stopped · Connect resumes selected permissions');self.status.set('Disconnecting…')
        if self.tray:self.tray.title='ZDesk — remote access companion'
    def forget_saved_pairing(self):
        if getattr(self,'terminal_pairing',False):local_settings.forget_terminal()
        else:local_settings.forget()
    def forget(self):
        self.disconnect();self.forget_saved_pairing();self.credentials=None;self.unattended.set(False)
        self.status.set('Enrollment forgotten. Also Revoke the device in your dashboard.')
    def close(self):
        if self.background.get():
            self.ensure_tray()
            if not self.tray_ready.is_set():
                self.status.set('Starting the tray icon. Please close the window again in a moment.');return
            self.save();self.tray.title='ZDesk — camera ON' if self.camera.is_set() else 'ZDesk — remote access companion';self.root.withdraw()
        else:self.quit()
    def quit(self):
        self.exiting=True;self.disconnect()
        if self.tray:self.tray.stop()
        self.root.after(600,self.root.destroy)

def terminal_setup(*, read, read_secret, write=print, saved=False, remember=False, all_sharing=False, start_in_tray=False):
    """Collect consent on the local console before starting a visible session."""
    options = {
        'control': 'mouse and keyboard control',
        'audio': 'system playback audio',
        'microphone': 'microphone (nearby sound)',
        'camera': 'camera (surroundings)',
        'files': 'files in ZDesk Shared and Inbox',
    }
    if not desktop_runtime.system_audio_available():
        del options['audio']
    write('ZDesk will share the primary screen with the paired dashboard.')
    for key, description in options.items():
        write(f'  {key}: {description}')
    write('This starts a visible session and does not enable startup.')
    if start_in_tray:write('The main window stays closed. The visible ZDesk tray icon provides Open, Disconnect and Quit.')
    if remember:write('Windows will protect the saved device token. The passcode and sharing choices are not saved.')
    if all_sharing:
        selected = set(options)
    else:
        selection = read('Optional features (comma-separated, all, or Enter for screen only): ')
        selected = {value.strip().lower() for value in selection.split(',') if value.strip()}
        if selected == {'all'}:
            selected = set(options)
        if not selected <= options.keys():
            raise ValueError('Unknown or unsupported sharing feature. No session started.')
    write('Selected: primary screen' + ''.join(', ' + options[key] for key in options if key in selected))
    if saved:
        write('Using the saved terminal pairing for this Windows account.')
        code = ''
    else:
        code = read_secret('ZDesk pairing code or connection passcode: ').strip()
        if not code or len(code) > 200:
            raise ValueError('Enter a valid-length ZDesk code. No session started.')
    if read('Type CONNECT to start sharing, or press Enter to cancel: ') != 'CONNECT':
        return None
    return code, selected


class ConsoleSession:
    """Foreground console state for the existing, permission-gated capture worker."""
    run = Companion.run
    input_worker = Companion.input_worker
    file_worker = Companion.file_worker

    def __init__(self, selected):
        self.console_mode=True
        self.stop=threading.Event()
        self.events=queue.Queue()
        self.control_failure=None
        self.home=Path.home()/'ZDesk'
        self.home.mkdir(exist_ok=True)
        for key, name in [('control','allow'),('audio','audio'),('microphone','mic'),('camera','camera'),('files','files')]:
            event=threading.Event()
            if key in selected:event.set()
            setattr(self,name,event)


def run_console(setup, *, saved=None, remember=False, write=print):
    """Keep capture tied to this terminal; Ctrl+C signals all existing workers."""
    code, selected=setup
    session=ConsoleSession(selected)
    worker=threading.Thread(target=session.run,args=(DEFAULT_SERVER,code,saved,True),daemon=True)
    write('ZDesk foreground sharing session. Keep this terminal open. Ctrl+C stops sharing.')
    write('Connecting to the paired dashboard…')
    worker.start()
    code=None;setup=None
    last_status=time.monotonic()
    result=0
    try:
        while worker.is_alive() or not session.events.empty():
            try:kind, value=session.events.get(timeout=.25)
            except queue.Empty:
                if time.monotonic()-last_status>=10:
                    write('ZDesk session active — Ctrl+C stops sharing.')
                    last_status=time.monotonic()
                continue
            if kind=='credentials':
                if remember:
                    try:local_settings.save_terminal(value)
                    except Exception:write('Connected, but pairing could not be remembered.')
            elif kind=='revoked':
                if remember:local_settings.forget_terminal()
                write('Pairing revoked. Sharing is stopping.');session.stop.set();result=1
            elif kind=='uninstall':
                write('Removal requires the normal companion. No removal performed.')
            elif kind=='done':
                if str(value).startswith('Stopped:'):result=1
                write(str(value).replace('Click Start to reconnect.','Run the command again to reconnect.'))
            elif kind in ('status','connected','camera_status','camera_done','camera_error','control_error'):
                if kind=='status' and str(value).startswith('Sharing primary display'):
                    continue
                write('ZDesk: '+str(value))
            if kind=='connected':last_status=time.monotonic()
    except KeyboardInterrupt:
        write('Stopping ZDesk…')
    finally:
        session.stop.set()
        for event in (session.allow,session.audio,session.mic,session.camera,session.files):event.clear()
        # The capture worker has bounded network timeouts and releases input/audio.
        worker.join()
        write('ZDesk sharing stopped.')
    return result


def connect_from_terminal(companion, code, selected, *, saved=None, remember=False):
    """Use the same permission switches and pairing path as the desktop UI."""
    switches = {
        'control': (companion.control, companion.allow),
        'audio': (companion.system_audio, companion.audio),
        'microphone': (companion.microphone, companion.mic),
        'camera': (companion.camera_permission, companion.camera),
        'files': (companion.file_permission, companion.files),
    }
    for key, (var, event) in switches.items():
        var.set(key in selected)
        companion.permission(var, event, persist=False)
    if 'camera' in selected:
        companion.camera_status.set('Camera selected · automatic detection when connected')
    companion.terminal_pairing=remember
    if saved:companion.credentials=saved
    companion.code.set(code)
    try:
        companion.connect()
    finally:
        companion.code.set('')


def connect_in_tray(companion, setup, *, saved=None, remember=False, on_ready=None, on_failure=None):
    """Do not begin capture until the visible tray control is ready."""
    companion.ensure_tray()
    deadline = time.monotonic() + 8
    def ready():
        if companion.exiting:
            return
        if companion.tray and companion.tray_ready.is_set():
            companion.background.set(True)
            connect_from_terminal(companion, *setup, saved=saved, remember=remember)
            companion.tray.title = 'ZDesk — sharing screen' + ''.join(' + '+key for key in sorted(setup[1]))
            if on_ready:on_ready()
        elif not companion.tray or time.monotonic() >= deadline:
            if on_failure:
                on_failure();return
            companion.show()
            companion.status.set('Tray unavailable. Sharing has not started. Use Connect in this window.')
        else:
            companion.root.after(100, ready)
    ready()


def ask_keep_running(selected):
    """Local consent, default No; the popup closes after either answer."""
    prompt=tk.Tk()
    prompt.withdraw()
    try:
        features='screen'+''.join(', '+name for name in sorted(selected))
        return messagebox.askyesno('Keep ZDesk running?',
            'Keep ZDesk sharing after you close PowerShell?\n\n'
            'Shared features: '+features+'\n\n'
            'Yes starts a visible ZDesk tray companion with Open, Disconnect and Quit. '
            'It does not start automatically after sign-out or reboot.\n\n'
            'No keeps this session in the foreground terminal; Ctrl+C stops it.',
            parent=prompt,default='no')
    finally:
        prompt.destroy()


if __name__=='__main__':
    background_payload=None
    if sys.argv[1:]==['--background-session']:
        if sys.platform!='win32':sys.exit('Background handoff requires Windows.')
        import ctypes
        if ctypes.windll.shell32.IsUserAnAdmin():sys.exit('Run ZDesk as the signed-in user.')
        from background_session import consume_handoff
        try:background_payload=consume_handoff()
        except Exception:sys.exit('Invalid or expired local background request.')
    if '--desktop-self-test' in sys.argv:
        from desktop_probe import run as probe
        probe(Companion,sys.argv[sys.argv.index('--desktop-self-test')+1]);sys.exit(0)
    if '--self-test' in sys.argv:
        output=Path(sys.argv[sys.argv.index('--self-test')+1])
        try:
            with tempfile.TemporaryDirectory() as temp:
                local_settings.ROOT=Path(temp)/'ZDesk';local_settings.LEGACY_ROOT=Path(temp)/'TyDesk'
                sample={'id':'build-smoke-test','token':'not-a-real-credential','url':'https://example.test'}
                local_settings.save(sample);assert local_settings.load()==sample;local_settings.forget()
            root=tk.Tk();root.withdraw();root.update();root.destroy()
            import native_shell
            # Exercise a cold SoundCard import on a fresh thread, as real audio does.
            from audio_capture import load_audio_backend
            audio_errors=[]
            def cold_audio():
                cleanup=lambda:None
                try:backend,cleanup=load_audio_backend()
                except Exception as exc:audio_errors.append(str(exc))
                finally:cleanup()
            for _ in range(2):
                audio_check=threading.Thread(target=cold_audio);audio_check.start();audio_check.join(10)
                assert not audio_check.is_alive(),'Audio initialization timed out'
            assert not audio_errors,str(audio_errors)
            import soundcard
            import numpy as np
            assert len(np.fromstring(b'\x00'*8,dtype=np.float32))==2,'WASAPI NumPy compatibility check failed'
            import pystray
            import cv2
            assert cv2.__version__
            test_root=tk.Tk();test_app=Companion(test_root);test_root.update();test_app.ensure_tray()
            assert test_app.tray_ready.wait(10),'Tray failed to initialize'
            test_app.background.set(True);test_app.close();test_root.update();assert test_root.state()=='withdrawn'
            test_app.show();test_root.update();assert test_root.state()=='normal'
            test_app.quit();test_root.update();test_root.destroy()
            output.write_text(json.dumps({'ok':True,'tk':True,'dpapi':True,'audio_module':True,'ui':True,'tray':True}))
            sys.exit(0)
        except Exception as exc:
            output.write_text(json.dumps({'ok':False,'error':str(exc)}));sys.exit(1)
    flags = [] if background_payload else sys.argv[1:]
    terminal = '--terminal-setup' in flags
    remember_terminal = terminal and '--remember-pairing' in flags
    all_sharing = terminal and '--all-sharing' in flags
    start_in_tray = bool(background_payload) or (terminal and '--start-in-tray' in flags)
    console_mode = terminal and '--console' in flags
    ask_background = terminal and '--ask-keep-running' in flags
    if ask_background and not console_mode:sys.exit('AskKeepRunning requires Console mode.')
    if console_mode and start_in_tray:sys.exit('Choose foreground console or tray mode, not both.')
    if terminal and (set(flags) - {'--terminal-setup','--remember-pairing','--all-sharing','--start-in-tray','--console','--ask-keep-running'}):
        sys.exit('Unknown terminal setup option. Enter the pairing code only at the masked prompt.')
    if console_mode and sys.platform=='win32':
        import ctypes
        if ctypes.windll.shell32.IsUserAnAdmin():sys.exit('Use a regular Windows terminal for foreground sharing.')
    if console_mode and (sys.platform!='win32' or not sys.stdout or not sys.stdout.isatty()):
        sys.exit('Console mode requires a visible interactive Windows terminal.')
    if terminal and (getattr(sys, 'frozen', False) or not sys.stdin or not sys.stdin.isatty()):
        sys.exit('Open the Windows source launcher from an interactive PowerShell terminal.')
    # A second launch brings the existing window back from the tray.
    mutex=None;show_event=None
    if sys.platform=='win32':
        import ctypes
        from ctypes import wintypes
        kernel=ctypes.windll.kernel32
        kernel.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR];kernel.CreateMutexW.restype=wintypes.HANDLE
        kernel.CreateEventW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.BOOL,wintypes.LPCWSTR];kernel.CreateEventW.restype=wintypes.HANDLE
        kernel.SetEvent.argtypes=[wintypes.HANDLE];kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
        kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle.restype=wintypes.BOOL
        mutex=kernel.CreateMutexW(None,False,'Local\\ZDeskCompanion');already=kernel.GetLastError()==183
        show_event=kernel.CreateEventW(None,False,False,'Local\\ZDeskShowCompanion')
        if already:
            kernel.SetEvent(show_event)
            if terminal:sys.exit('Quit the running ZDesk companion before starting terminal setup.')
            sys.exit(0)
    if terminal:
        from getpass import getpass, GetPassWarning
        import warnings
        saved_terminal = None
        if remember_terminal:
            try:
                saved_terminal = local_settings.load_terminal()
                if saved_terminal and saved_terminal['url'] != DEFAULT_SERVER:
                    sys.exit('Saved terminal pairing uses a different server. No session started.')
            except Exception:
                sys.exit('Could not read saved terminal pairing. No session started.')
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', GetPassWarning)
                setup = terminal_setup(read=input, read_secret=getpass,saved=bool(saved_terminal),remember=remember_terminal,all_sharing=all_sharing,start_in_tray=start_in_tray)
        except (EOFError, KeyboardInterrupt, GetPassWarning):
            sys.exit('Terminal setup canceled; no session started.')
        except ValueError as exc:
            sys.exit(str(exc))
        if setup is None:
            sys.exit('Terminal setup canceled; no session started.')
    if console_mode:
        if ask_background and ask_keep_running(setup[1]):
            # Release our single-instance reservation so the separate tray process
            # can acquire it. No capture has started in this terminal.
            if mutex:
                kernel.CloseHandle(mutex);mutex=None
            if show_event:
                kernel.CloseHandle(show_event);show_event=None
            from background_session import launch
            try:started=launch(setup,saved=saved_terminal,remember=remember_terminal)
            except Exception as exc:sys.exit(str(exc))
            sys.exit(0 if started else 1)
        sys.exit(run_console(setup,saved=saved_terminal,remember=remember_terminal))
    root=tk.Tk()
    if start_in_tray:root.withdraw()
    companion=Companion(root,restore=not (terminal or background_payload));companion.show_event=show_event
    if background_payload:
        from background_session import acknowledge
        def started(path=background_payload['ready']):
            try:acknowledge(path,True)
            except Exception:companion.quit()
        def failed(path=background_payload['ready']):
            try:acknowledge(path,False)
            finally:companion.quit()
        try:
            connect_in_tray(companion,(background_payload['code'],set(background_payload['selected'])),
                saved=background_payload['saved'],remember=background_payload['remember'],
                on_ready=started,on_failure=failed)
        except Exception:
            failed()
        background_payload=None
    if terminal:
        root.update_idletasks()
        if start_in_tray:connect_in_tray(companion,setup,saved=saved_terminal,remember=remember_terminal)
        else:connect_from_terminal(companion,*setup,saved=saved_terminal,remember=remember_terminal)
        del setup
    root.mainloop()
