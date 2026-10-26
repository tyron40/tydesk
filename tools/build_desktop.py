"""Build a native desktop bundle on its matching GitHub-hosted OS/CPU."""
import hashlib,json,os,platform,subprocess,sys,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from download_catalog import CATALOG
from desktop_runtime import VERSION

def main():
 target=sys.argv[1];entry=next(e for e in CATALOG if e['id']==target)
 assert entry['os']==('macos' if sys.platform=='darwin' else 'linux')
 actual='arm64' if platform.machine().lower() in ('arm64','aarch64') else 'x64'
 assert actual==entry['architecture'],(actual,entry['architecture'])
 command=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed','--name','ZDesk','--collect-all','cv2','--collect-all','soundcard','--collect-all','keyring','--hidden-import','pystray._darwin' if sys.platform=='darwin' else 'pystray._xorg','agent.py']
 subprocess.run(command,cwd=ROOT,check=True)
 folder=ROOT/'dist'/'ZDesk';output=ROOT/'downloads'/entry['filename'];output.parent.mkdir(exist_ok=True)
 if sys.platform=='darwin':
  import plistlib
  bundle=ROOT/'dist/ZDesk.app';plist=bundle/'Contents/Info.plist';data=plistlib.loads(plist.read_bytes())
  data.update(CFBundleIdentifier='com.zdesk.companion',CFBundleShortVersionString=VERSION,CFBundleVersion=VERSION,
   NSCameraUsageDescription='ZDesk shares your selected camera with your paired dashboard only when enabled locally. Use Stop camera or Disconnect to stop.',
   NSMicrophoneUsageDescription='ZDesk shares your microphone and surrounding sound only when enabled locally. Disconnect or uncheck Microphone to stop.',
   NSHighResolutionCapable=True)
  plist.write_bytes(plistlib.dumps(data))
  subprocess.run(['codesign','--force','--deep','--sign','-',str(bundle)],check=True)
  subprocess.run(['codesign','--verify','--deep',str(bundle)],check=True)
  executable=bundle/'Contents/MacOS/ZDesk'
 else:executable=folder/'ZDesk'
 subprocess.run([str(executable),'--desktop-self-test',str(ROOT/'desktop-smoke.json')],check=True,timeout=90)
 report=json.loads((ROOT/'desktop-smoke.json').read_text());assert report['ok'];assert report['architecture'].lower() in (('arm64','aarch64') if actual=='arm64' else ('x86_64','amd64'))
 if sys.platform=='darwin':
  subprocess.run(['ditto','-c','-k','--sequesterRsrc','--keepParent',str(bundle),str(output)],check=True)
 else:
  (folder/'READ-ME.txt').write_text('ZDesk '+VERSION+'\n\n'+entry['requirements']+'\n\n'+entry['setup']+'\n\nOpen ZDesk, enter your dashboard connection passcode, select local sharing permissions, and Connect. Camera/microphone remain visibly indicated. Disconnect or Quit stops sharing.\n')
  with tarfile.open(output,'w:gz') as tar:tar.add(folder,arcname='ZDesk')
 assert output.stat().st_size<95*1024*1024,'Bundle exceeds direct-download distribution limit'
 manifest={'version':VERSION,'source_commit':os.environ.get('GITHUB_SHA','local'),'architecture':entry['architecture'],'platform':entry['os'],'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'development_build':True,'notarized':False,'hardware_tested':False,'packaged_smoke':report}
 (output.parent/(target+'-build.json')).write_text(json.dumps(manifest,indent=2))
 print('PASS native build and packaged UI smoke:',target,output.stat().st_size)
if __name__=='__main__':main()
