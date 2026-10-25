"""Reusable enrollment passcodes: salted hashes and bounded enrollment attempts."""
import hashlib,secrets,time,threading
from collections import deque
ITERATIONS=260000

def encode(passcode):
    if not isinstance(passcode,str) or not 16<=len(passcode)<=128:
        raise ValueError('Use a connection passcode of 16 to 128 characters.')
    salt=secrets.token_hex(16)
    digest=hashlib.pbkdf2_hmac('sha256',passcode.encode(),salt.encode(),ITERATIONS).hex()
    return f'pbkdf2_sha256${ITERATIONS}${salt}${digest}'

def verify(passcode,encoded):
    if not encoded or not isinstance(passcode,str) or len(passcode)>128:return False
    try:
        scheme,rounds,salt,digest=encoded.split('$')
        if scheme!='pbkdf2_sha256' or int(rounds)!=ITERATIONS:return False
        candidate=hashlib.pbkdf2_hmac('sha256',passcode.encode(),salt.encode(),ITERATIONS).hex()
        return secrets.compare_digest(candidate,digest)
    except (ValueError,TypeError):return False

class EnrollmentGate:
    def __init__(self):self.peers={};self.all=deque();self.lock=threading.Lock()
    def permit(self,peer):
        with self.lock:
            now=time.monotonic()
            for key in list(self.peers):
                q=self.peers[key]
                while q and now-q[0]>=60:q.popleft()
                if not q:del self.peers[key]
            while self.all and now-self.all[0]>=60:self.all.popleft()
            q=self.peers.setdefault(peer,deque())
            if len(q)>=10 or len(self.all)>=60:return False
            q.append(now);self.all.append(now);return True
