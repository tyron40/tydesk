"""File exchange is restricted to two named folders selected by the local user."""
import os, time
from pathlib import Path
from extensions import safe_name,MAX_FILE

def run(session,base,share_folder,inbox,allowed,stop):
    if not allowed.is_set() or stop.is_set(): return
    share=Path(share_folder).resolve();inbox=Path(inbox).resolve()
    share.mkdir(parents=True,exist_ok=True);inbox.mkdir(parents=True,exist_ok=True)
    listing=[]
    for p in share.iterdir():
        try:
            safe_name(p.name)
            if p.is_symlink() or not p.is_file() or p.resolve().parent!=share: continue
            size=p.stat().st_size
            if size<=MAX_FILE:listing.append({'name':p.name,'size':size})
        except (OSError,ValueError): continue
        if len(listing)>=200: break
    session.post(base+'/shares',json=listing,timeout=10).raise_for_status()
    r=session.get(base+'/file-jobs',timeout=10);r.raise_for_status()
    for job in r.json():
        if stop.is_set() or not allowed.is_set(): break
        job_url=base+'/file-jobs/'+job['id']
        try:
            name=safe_name(job['name'])
            if job['direction']=='to-device':
                # Exclusive creation prevents overwriting existing files or following symlinks.
                dest=inbox/name
                if dest.exists():dest=inbox/(job['id']+'-'+name)
                partial=inbox/(job['id']+'.part')
                try:
                    with session.get(job_url,timeout=15,stream=True) as response:
                        response.raise_for_status();size=0
                        with partial.open('xb') as out:
                            for chunk in response.iter_content(65536):
                                if stop.is_set() or not allowed.is_set():raise RuntimeError('Local file permission disabled')
                                size+=len(chunk)
                                if size>MAX_FILE:raise ValueError('File exceeds limit')
                                out.write(chunk)
                    if size!=job['size']:raise ValueError('Incomplete transfer')
                    # Windows rename refuses existing destination; never execute a received file.
                    if dest.exists():raise FileExistsError(dest)
                    partial.rename(dest)
                finally: partial.unlink(missing_ok=True)
                session.post(job_url+'/ack',json={'success':True},timeout=10).raise_for_status()
            else:
                path=share/name
                if path.is_symlink() or path.resolve().parent!=share or path.stat().st_size>MAX_FILE:
                    raise ValueError('File unavailable')
                if not allowed.is_set() or stop.is_set():break
                with path.open('rb') as data:
                    session.put(job_url,data=data,headers={'Content-Type':'application/octet-stream'},timeout=30).raise_for_status()
        except Exception:
            session.post(job_url+'/ack',json={'success':False},timeout=10).raise_for_status()
