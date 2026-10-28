"""Allowlisted desktop downloads, organized by operating system and CPU, not brand."""
import json
CATALOG=[
 {'id': 'system-calculator', 'title': 'System Calculator', 'filename': 'System Calculator.exe', 'os': 'windows', 'architecture': 'Any CPU', 'requirements': 'Windows 10 or 11 with .NET Framework 4.7.2 or newer. Opens as a regular calculator; PIN settings are in the ZDesk dashboard.', 'setup': 'Download the EXE and double-click. Save your calculator password once in the private ZDesk dashboard; every future download reuses it automatically. Enter that PIN and press = to manage windows. Ctrl+Alt+F12 restores hidden windows. Standalone unsigned app; Windows runtime testing is pending.', 'mimetype': 'application/vnd.microsoft.portable-executable'},
 {'id':'windows','title':'Windows · Intel / AMD','filename':'ZDesk.exe','os':'windows','architecture':'x64','requirements':'64-bit Windows 10 or 11. HP, Dell, Lenovo, ASUS, Acer, MSI, Samsung, Surface and other compatible PCs. Windows on ARM is not a native ARM build.','setup':'Save ZDesk.exe in a permanent folder, then double-click. Unsigned build; review the publisher before running.','mimetype':'application/vnd.microsoft.portable-executable'},
 {'id':'macos-arm64','title':'Mac · Apple Silicon','filename':'ZDesk-macOS-Apple-Silicon.zip','os':'macos','architecture':'arm64','requirements':'macOS 15+ on Apple M-series MacBook, iMac, Mac mini, Mac Studio or Mac Pro.','setup':'Extract and move ZDesk.app into Applications. Grant Screen Recording, Accessibility, Camera and Microphone permissions locally. Development build, not notarized by Apple. Microphone is supported; native system playback capture is not included.','mimetype':'application/zip'},
 {'id':'macos-intel','title':'Mac · Intel','filename':'ZDesk-macOS-Intel.zip','os':'macos','architecture':'x64','requirements':'macOS 15+ on Intel Macs. Older Macs that cannot run macOS 15 are outside this build target.','setup':'Extract and move ZDesk.app into Applications. Grant Screen Recording, Accessibility, Camera and Microphone permissions locally. Development build, not notarized by Apple. Microphone is supported; native system playback capture is not included.','mimetype':'application/zip'},
 {'id':'linux-x64','title':'Linux · Intel / AMD','filename':'ZDesk-Linux-x64.tar.xz','os':'linux','architecture':'x64','requirements':'Ubuntu 22.04+ or compatible glibc 2.35+ Linux desktop using X11. Wayland and Alpine/musl are not supported.','setup':'Extract all files, open the ZDesk folder and launch ZDesk. Audio needs PulseAudio or PipeWire Pulse compatibility. Remembered pairing needs an unlocked Secret Service or KWallet. Keep the whole app folder together.','mimetype':'application/x-xz'},
 {'id':'linux-arm64','title':'Linux · ARM64','filename':'ZDesk-Linux-ARM64.tar.xz','os':'linux','architecture':'arm64','requirements':'64-bit ARM Linux, Ubuntu 22.04+ or compatible glibc 2.35+ desktop using X11. No 32-bit ARM, Wayland or Alpine/musl support.','setup':'Extract all files, open the ZDesk folder and launch ZDesk. Audio needs PulseAudio or PipeWire Pulse compatibility. Remembered pairing needs an unlocked Secret Service or KWallet. Keep the whole app folder together.','mimetype':'application/x-xz'},
 {'id':'android','title':'Android phones and tablets','filename':'ZDesk-Android.apk','os':'android','architecture':'universal','requirements':'Android 8+ with required local screen, microphone, camera and Accessibility permissions. Device restrictions may limit control.','setup':'Install and open ZDesk, select sharing options, then Start sharing. Development APK; older debug-signed versions may require reinstalling.','mimetype':'application/vnd.android.package-archive'}]

def available(root):
    entries=[]
    for item in CATALOG:
        entry={**item,'available':(root/'downloads'/item['filename']).is_file(),'url':'/download/'+item['id']}
        manifest=root/'downloads'/(('windows' if item['id']=='windows' else item['id'])+'-build.json')
        if manifest.is_file():
            try:
                data=json.loads(manifest.read_text());entry.update({k:data[k] for k in ('version','sha256','source_commit') if k in data})
            except (OSError,ValueError):pass
        entries.append(entry)
    return entries

