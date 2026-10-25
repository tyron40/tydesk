"""Durable registry client. Only the broker receives its shared secret."""
import os,json,urllib.request
URL=os.environ.get('TYDESK_REGISTRY_URL','')
KEY=os.environ.get('TYDESK_REGISTRY_KEY','')
ENABLED=bool(URL and KEY)
if bool(URL)!=bool(KEY):raise RuntimeError('Both registry URL and key must be configured')
if URL and not URL.startswith('https://'):raise RuntimeError('Registry must use HTTPS')
def call(op,**values):
    req=urllib.request.Request(URL,data=json.dumps({'op':op,**values}).encode(),method='POST',headers={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=20) as response:return json.load(response)
def list_devices():return call('list')
def register(identity,token,name):
    if ENABLED:call('register',id=identity,token=token,name=name)
def revoke(identity):
    if ENABLED:call('revoke',id=identity)
