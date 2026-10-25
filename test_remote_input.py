import unittest
from unittest.mock import Mock,patch
from remote_input import Controller,validate
class InputTests(unittest.TestCase):
 def setUp(self):
  self.pg=Mock();self.pg.size.return_value=(1920,1080);self.pg.FAILSAFE=True;self.c=Controller(self.pg)
 def test_move_drag_and_release_coordinates(self):
  self.c.apply({'type':'pointer_down','x':.1,'y':.2});self.c.apply({'type':'move','x':.8,'y':.7});self.c.apply({'type':'pointer_up','x':.8,'y':.7})
  self.pg.mouseDown.assert_called_once_with(button='left');self.pg.mouseUp.assert_called_once_with(button='left')
  self.pg.moveTo.assert_called_with(1535,755,duration=0);self.assertFalse(self.c.buttons)
 def test_lost_connection_releases_keys_and_buttons(self):
  self.c.apply({'type':'key_down','key':'ctrl'});self.c.apply({'type':'pointer_down','x':0,'y':0});self.c.renewed=0
  self.c.tick();self.pg.keyUp.assert_called_once_with('ctrl');self.pg.mouseUp.assert_called_once_with(button='left');self.assertTrue(self.pg.FAILSAFE)
 def test_hold_renews_lease_and_duplicates_are_idempotent(self):
  self.c.apply({'type':'key_down','key':'shift'});self.c.apply({'type':'key_down','key':'shift'});self.c.apply({'type':'hold'});self.c.tick()
  self.pg.keyDown.assert_called_once_with('shift');self.pg.keyUp.assert_not_called();self.c.release()
 def test_invalid_input_rejected(self):
  for c in [{'type':'move','x':float('nan'),'y':0},{'type':'move','x':2,'y':.5},{'type':'key_down','key':'powershell'},{'type':'scroll','amount':True}]:
   with self.assertRaises(ValueError):validate(c)
if __name__=='__main__':unittest.main()
