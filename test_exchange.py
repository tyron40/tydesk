"""Real HTTP round-trip of file jobs using temporary folders and a local broker."""
import os,tempfile,threading,unittest
from pathlib import Path
os.environ.setdefault('TYDESK_PASSWORD','integration-test-password-long')
os.environ.setdefault('TYDESK_DATA',tempfile.mkdtemp(prefix='tydesk-http-'))
import requests
import server
from file_exchange import run
from werkzeug.serving import make_server,WSGIRequestHandler
class Quiet(WSGIRequestHandler):
    def log(self,*args):pass
class ExchangeTests(unittest.TestCase):
    def test_real_files_roundtrip(self):
        http=make_server('127.0.0.1',0,server.app,threaded=True,request_handler=Quiet)
        thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
        base='http://127.0.0.1:'+str(http.server_port);admin=requests.Session();agent=requests.Session()
        admin.headers['Authorization']='Bearer '+server.ADMIN
        try:
            code=admin.post(base+'/api/pairing').json()['code']
            enrolled=agent.post(base+'/api/enroll',json={'code':code,'name':'File integration PC'}).json()
            agent.headers['Authorization']='Bearer '+enrolled['token'];endpoint=base+'/api/devices/'+enrolled['id']
            agent.post(endpoint+'/frame',data=b'jpeg',headers={'Content-Type':'image/jpeg','X-Allow-Files':'yes'}).raise_for_status()
            permission=threading.Event();permission.set();stop=threading.Event()
            with tempfile.TemporaryDirectory() as tmp:
                share=Path(tmp)/'Shared';inbox=Path(tmp)/'Inbox';share.mkdir()
                (share/'out.txt').write_bytes(b'from computer')
                queued=admin.post(endpoint+'/files',data=b'from browser',headers={'X-Filename':'in.txt'})
                self.assertEqual(queued.status_code,201)
                run(agent,endpoint,share,inbox,permission,stop)
                self.assertEqual((inbox/'in.txt').read_bytes(),b'from browser')
                request=admin.post(endpoint+'/files/request',json={'name':'out.txt'});self.assertEqual(request.status_code,201)
                run(agent,endpoint,share,inbox,permission,stop)
                result=admin.get(endpoint+'/files/'+request.json()['id'])
                self.assertEqual(result.content,b'from computer')
                self.assertEqual(result.status_code,200)
            admin.delete(endpoint)
        finally:admin.close();agent.close();http.shutdown();http.server_close()
if __name__=='__main__':unittest.main()
