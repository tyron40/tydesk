import os, tempfile, time, unittest
os.environ.setdefault('TYDESK_PASSWORD','test-removal-server-password')
os.environ.setdefault('TYDESK_DATA',tempfile.mkdtemp())
import server


class RemovalTests(unittest.TestCase):
    def setUp(self):
        server.enrollment_gate=server.connection_access.EnrollmentGate()
        self.c=server.app.test_client()
        self.admin={'Authorization':'Bearer '+server.ADMIN}
        code=self.c.post('/api/pairing',headers=self.admin).json['code']
        enrolled=self.c.post('/api/enroll',json={'code':code}).json
        self.identity=enrolled['id'];self.base='/api/devices/'+self.identity
        self.auth={'Authorization':'Bearer '+enrolled['token']}
        self.frame()

    def frame(self,control='yes',platform='android',supported='1'):
        return self.c.post(self.base+'/frame',data=b'jpeg',headers={**self.auth,
            'Content-Type':'image/jpeg','X-Allow-Control':control,
            'X-Companion-Platform':platform,'X-Companion-Removal':supported})

    def test_admin_only_and_local_capability_and_control_required(self):
        self.assertEqual(self.c.post(self.base+'/uninstall').status_code,401)
        self.frame(control='no')
        self.assertEqual(self.c.post(self.base+'/uninstall',headers=self.admin).status_code,409)
        self.frame(platform='unknown')
        self.assertEqual(self.c.post(self.base+'/uninstall',headers=self.admin).status_code,409)
        self.frame();server.devices[self.identity]['seen']=0
        self.assertEqual(self.c.post(self.base+'/uninstall',headers=self.admin).status_code,409)

    def test_single_delivery_and_expiry_and_authenticated_ack(self):
        response=self.c.post(self.base+'/uninstall',headers=self.admin)
        self.assertEqual(response.status_code,202);job=response.json
        self.assertEqual(self.c.get(self.base+'/removal').status_code,401)
        delivered=self.c.get(self.base+'/removal',headers=self.auth).json
        self.assertEqual(delivered['id'],job['id'])
        self.assertEqual(self.c.get(self.base+'/removal',headers=self.auth).json,None)
        self.assertEqual(self.c.post(self.base+'/removal',headers=self.auth,json={'id':'wrong','state':'removal_started'}).status_code,400)
        self.assertEqual(self.c.post(self.base+'/removal',headers=self.auth,json={'id':job['id'],'state':'completed'}).status_code,400)
        self.assertEqual(self.c.post(self.base+'/removal',headers=self.auth,json={'id':job['id'],'state':'cancelled'}).status_code,204)
        self.assertEqual(self.c.post(self.base+'/removal',headers=self.auth,json={'id':job['id'],'state':'removal_started'}).status_code,400)
        self.c.post(self.base+'/uninstall',headers=self.admin)
        server.devices[self.identity]['removal']['expires']=time.time()-1
        self.assertEqual(self.c.get(self.base+'/removal',headers=self.auth).json,None)
        self.assertEqual(server.devices[self.identity]['removal']['state'],'expired')

    def test_removal_not_delivered_after_control_disabled(self):
        self.c.post(self.base+'/uninstall',headers=self.admin);self.frame(control='no')
        self.assertEqual(self.c.get(self.base+'/removal',headers=self.auth).json,None)

if __name__=='__main__':unittest.main()
