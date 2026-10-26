"""Packaged smoke test without enrollment, camera/mic capture or security changes."""
import json,sys
from pathlib import Path

def run(Companion,output):
    import tkinter as tk
    import cv2,requests,keyring
    import desktop_runtime
    assert cv2.__version__ and requests.__version__
    root=tk.Tk();app=Companion(root,restore=False);root.update()
    assert app.root.title()=='ZDesk — Companion'
    if sys.platform.startswith('linux'):
        import pyautogui
        image=desktop_runtime.screenshot(pyautogui)
        assert image.width>0 and image.height>0
    app.exiting=True;app.stop.set();root.destroy()
    Path(output).write_text(json.dumps({'ok':True,'platform':desktop_runtime.platform_id(),'architecture':__import__('platform').machine(),'ui':True,'camera_module':cv2.__version__,'no_capture_permissions_requested':True}))
