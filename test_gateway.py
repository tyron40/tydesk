import unittest
from unittest.mock import Mock
import gateway


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.client=gateway.app.test_client()
        self.session=Mock();gateway.local.session=self.session
        self.remote=Mock(status_code=200,headers={'Content-Type':'application/json','Content-Encoding':'gzip','Set-Cookie':'private=secret'})
        self.remote.iter_content.return_value=iter([b'[]'])
        self.session.send.return_value=self.remote

    def test_fixed_target_bearer_body_and_no_cookie_forwarding(self):
        response=self.client.post('/api/devices/one/commands',json={'type':'release'},headers={'Authorization':'Bearer device-token','Cookie':'other-client=private','X-Companion-Platform':'android','Host':'attacker.test'})
        self.assertEqual(response.data,b'[]')
        prepared=self.session.send.call_args.args[0]
        self.assertEqual(prepared.url,gateway.UPSTREAM+'/api/devices/one/commands')
        self.assertEqual(prepared.headers['Authorization'],'Bearer device-token')
        self.assertNotIn('Cookie',prepared.headers);self.assertNotIn('Host',prepared.headers)
        self.assertNotIn('Set-Cookie',response.headers);self.assertNotIn('Content-Encoding',response.headers)
        self.assertFalse(self.session.send.call_args.kwargs['allow_redirects'])

    def test_auth_errors_and_download_headers_preserved(self):
        self.remote.status_code=401
        response=self.client.get('/api/devices');self.assertEqual(response.status_code,401)
        self.remote.status_code=200;self.remote.headers={'Content-Disposition':'attachment; filename=ZDesk-Android.apk','Content-Type':'application/vnd.android.package-archive'}
        response=self.client.get('/download/android')
        self.assertIn('ZDesk-Android.apk',response.headers['Content-Disposition'])

    def test_upstream_failures_recoverable_and_health_local(self):
        self.session.send.side_effect=gateway.requests.Timeout()
        self.assertEqual(self.client.get('/').status_code,503)
        self.assertEqual(self.client.get('/healthz').status_code,200)

if __name__=='__main__':unittest.main()
