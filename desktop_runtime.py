"""Explicit platform capabilities for the visible desktop companion."""
import os,sys
from pathlib import Path
VERSION='3.8'
def platform_id():return {'win32':'windows','darwin':'macos'}.get(sys.platform,'linux' if sys.platform.startswith('linux') else 'unknown')
def label():return {'windows':'WINDOWS','macos':'MAC','linux':'LINUX'}.get(platform_id(),'DESKTOP')
def system_audio_available():return sys.platform!='darwin'
def guidance():
    if sys.platform=='darwin':return 'Mac: allow Screen Recording and Accessibility in System Settings > Privacy & Security. Camera and microphone require their own OS permissions. System playback audio is not bundled; microphone sharing is available.'
    if sys.platform.startswith('linux'):return 'Linux: use an X11 desktop (Ubuntu 22.04+ or compatible glibc 2.35+). Wayland whole-desktop control is not supported. PulseAudio/PipeWire Pulse compatibility and an unlocked Secret Service/KWallet are needed for audio and saved pairing.'
    return 'Available after Windows sign-in while the PC is awake. Lock screen and UAC are not supported.'
def screenshot(pg):
    if not sys.platform.startswith('linux'):return pg.screenshot()
    if os.environ.get('XDG_SESSION_TYPE','').lower()=='wayland':raise RuntimeError('Log into an X11 desktop session for screen capture and control. Wayland is not supported by this companion.')
    import mss
    from PIL import Image
    with mss.mss() as capture:
        monitors=capture.monitors[1:]
        monitor=next((m for m in monitors if m['left']==0 and m['top']==0),monitors[0])
        image=capture.grab(monitor)
        return Image.frombytes('RGB',image.size,image.rgb)
def keyring_backend():
    import keyring
    backend=keyring.get_keyring()
    secure=('keyring.backends.macOS','keyring.backends.SecretService','keyring.backends.kwallet')
    if type(backend).__module__=='keyring.backends.chainer':
        backend=next((candidate for candidate in backend.backends if type(candidate).__module__ in secure),backend)
    if type(backend).__module__ not in secure:
        raise RuntimeError('Unlock your system keychain/Secret Service/KWallet to remember pairing. Plaintext credential storage is not supported.')
    return backend
KEYRING_SERVICE='com.zdesk.companion';KEYRING_ACCOUNT='enrollment'
def secure_load():return keyring_backend().get_password(KEYRING_SERVICE,KEYRING_ACCOUNT)
def secure_save(value):keyring_backend().set_password(KEYRING_SERVICE,KEYRING_ACCOUNT,value)
def secure_forget():
    backend=keyring_backend()
    if backend.get_password(KEYRING_SERVICE,KEYRING_ACCOUNT) is not None:backend.delete_password(KEYRING_SERVICE,KEYRING_ACCOUNT)
