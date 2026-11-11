import base64
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

import background_session as background


def packet(**changes):
    value=dict(version=1,created=time.time(),code='synthetic-pair-code',
        selected=['microphone'],saved=None,remember=True,ready='ready.json')
    value.update(changes)
    return value


def fake_crypto():
    crypto=Mock()
    crypto.CryptProtectData.side_effect=lambda value,*args:b'fake-protection:'+base64.b64encode(value)
    crypto.CryptUnprotectData.side_effect=lambda value,*args:(None,base64.b64decode(value.removeprefix(b'fake-protection:')))
    return crypto


class BackgroundTests(unittest.TestCase):
    def test_handoff_is_short_lived_and_has_fixed_permissions_and_server(self):
        for bad in (packet(created=time.time()-60),packet(selected=['admin']),packet(code=''),
            packet(saved={'id':'x','token':'y','url':'https://wrong.test'})):
            with self.assertRaises(ValueError):background._validate(bad)

    def test_secret_is_protected_and_consumed_without_plaintext_file(self):
        with patch.dict(sys.modules,{'win32crypt':fake_crypto()}):
            encoded=background.encode_handoff(packet())
            self.assertNotIn('synthetic-pair-code',encoded)
            with patch.dict(os.environ,{background.ENV_KEY:encoded}):
                self.assertEqual(background.consume_handoff()['code'],'synthetic-pair-code')
                self.assertNotIn(background.ENV_KEY,os.environ)

    def test_success_requires_visible_tray_ack_and_no_plaintext_command_arguments(self):
        with tempfile.TemporaryDirectory() as folder:
            pythonw=Path(folder)/'pythonw.exe';pythonw.touch()
            worker=Mock();worker.poll.return_value=None
            def spawn(args,**kwargs):
                self.assertNotIn('synthetic-pair-code',str(args))
                cipher=kwargs['env'][background.ENV_KEY]
                self.assertNotIn('synthetic-pair-code',cipher)
                with patch.dict(os.environ,{background.ENV_KEY:cipher}):
                    value=background.consume_handoff()
                background.acknowledge(value['ready'],True)
                self.assertEqual(value['selected'],['microphone'])
                return worker
            with patch.dict(sys.modules,{'win32crypt':fake_crypto()}),patch.object(background.sys,'platform','win32'),patch.object(background.sys,'executable',str(Path(folder)/'python.exe')),patch.object(background.subprocess,'Popen',side_effect=spawn):
                output=Mock()
                self.assertTrue(background.launch(('synthetic-pair-code',{'microphone'}),write=output))
                self.assertNotIn('synthetic-pair-code',str(output.call_args_list))
            worker.terminate.assert_not_called()

    def test_missing_ack_terminates_child_instead_of_leaving_unknown_session(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'pythonw.exe').touch()
            worker=Mock();worker.poll.return_value=None
            with patch.dict(sys.modules,{'win32crypt':fake_crypto()}),patch.object(background.sys,'platform','win32'),patch.object(background.sys,'executable',str(Path(folder)/'python.exe')),patch.object(background.subprocess,'Popen',return_value=worker),patch.object(background.time,'monotonic',side_effect=[0,99]):
                with self.assertRaises(RuntimeError):
                    background.launch(('synthetic-pair-code',{'microphone'}),write=Mock())
            worker.terminate.assert_called_once()
            worker.wait.assert_called_once()

    @unittest.skipUnless(sys.platform=='win32','Windows DPAPI only')
    def test_actual_dpapi_roundtrip(self):
        encoded=background.encode_handoff(packet())
        with patch.dict(os.environ,{background.ENV_KEY:encoded}):
            self.assertEqual(background.consume_handoff()['code'],'synthetic-pair-code')


if __name__=='__main__':unittest.main()
