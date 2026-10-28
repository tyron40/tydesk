import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from flask import Flask
import calculator_routes

class CalculatorRoutesTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'downloads').mkdir();self.binary=(Path(__file__).parent/'downloads'/'System Calculator.exe').read_bytes()
        (self.root/'downloads'/'System Calculator.exe').write_bytes(self.binary)
        self.saved=None
        def registry(op,**values):
            if op=='set_calculator':self.saved=values['calculator_config'];return {'ok':True}
            if op=='get_calculator':return {'calculator_config':self.saved}
            raise AssertionError(op)
        self.patches=[patch.object(calculator_routes,'ROOT',self.root),patch.object(calculator_routes.device_registry,'ENABLED',True),patch.object(calculator_routes.device_registry,'call',side_effect=registry),patch.dict(os.environ,{'TYDESK_PASSWORD':'unit-test-owner-password'})]
        for p in self.patches:p.start()
        self.app=Flask(__name__);calculator_routes.install(self.app);self.client=self.app.test_client();self.auth={'Authorization':'Bearer unit-test-owner-password'}
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()
    def test_save_once_all_downloads_reuse_password_even_after_recreating_app(self):
        salt=bytes(range(16));config=(salt+hashlib.pbkdf2_hmac('sha256',b'072839',salt,210000,32)).hex()
        self.assertEqual(self.client.put('/api/calculator-settings',json={'config':config},headers=self.auth).status_code,200)
        self.assertEqual(self.client.get('/api/calculator-settings',headers=self.auth).json,{'configured':True})
        for client in [self.client,self.app.test_client()]:
            with client.get('/download/system-calculator') as r:
                self.assertEqual(r.status_code,200);self.assertEqual(r.data,self.binary+bytes.fromhex(config)+calculator_routes.MARKER)
                self.assertEqual(r.headers['X-Calculator-Configured'],'yes');self.assertIn('attachment;',r.headers['Content-Disposition']);self.assertIn('System Calculator.exe',r.headers['Content-Disposition'])
        other=Flask('restarted');calculator_routes.install(other)
        self.assertEqual(other.test_client().get('/download/system-calculator').data,self.binary+bytes.fromhex(config)+calculator_routes.MARKER)
    def test_settings_require_owner_and_validate_hash(self):
        self.assertEqual(self.client.get('/api/calculator-settings').status_code,401)
        self.assertEqual(self.client.put('/api/calculator-settings',json={'config':'ab'*48}).status_code,401)
        for value in ['123456','ff'*47,None,'GG'*48]:
            self.assertEqual(self.client.put('/api/calculator-settings',json={'config':value},headers=self.auth).status_code,400)
        self.assertIsNone(self.saved)
    def test_download_does_not_silently_lose_saved_password_on_registry_failure(self):
        with patch.object(calculator_routes.device_registry,'call',side_effect=OSError('offline')):
            self.assertEqual(self.client.get('/download/system-calculator').status_code,503)
            self.assertEqual(self.client.get('/api/calculator-settings',headers=self.auth).status_code,503)
    def test_first_download_is_regular_app_without_setup_prompt(self):
        with self.client.get('/download/system-calculator') as r:
            self.assertEqual(r.status_code,200);self.assertEqual(r.data,self.binary)
            self.assertEqual(r.headers['X-Calculator-Configured'],'no')
if __name__=='__main__':unittest.main()
