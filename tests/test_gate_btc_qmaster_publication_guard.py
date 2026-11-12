import unittest
from tools.gate_btc_qmaster_publication_guard import assess

class GuardTests(unittest.TestCase):
 def state(self,day,h='a'):
  return dict(data_as_of=day,status='PASS',operational_status='NOT_APPROVED',orders_generated=0,real_capital_used=0,csv_sha256=h*64)
 def test_first_publication(self):self.assertEqual(assess(self.state('2026-11-11')),'ADVANCE')
 def test_newer_source_advances(self):self.assertEqual(assess(self.state('2026-11-11'),self.state('2026-11-10')),'ADVANCE')
 def test_old_source_never_replaces_new(self):self.assertEqual(assess(self.state('2026-11-07'),self.state('2026-11-10')),'REFUSED_SOURCE_REGRESSION')
 def test_identical_cutoff_is_noop(self):self.assertEqual(assess(self.state('2026-11-11'),self.state('2026-11-11')),'UNCHANGED')
 def test_same_cutoff_changed_hash_requires_review(self):
  with self.assertRaisesRegex(ValueError,'REVIEW_REQUIRED'):assess(self.state('2026-11-11','b'),self.state('2026-11-11'))
 def test_unsafe_source_fails(self):
  d=self.state('2026-11-11');d['orders_generated']=1
  with self.assertRaisesRegex(ValueError,'AUTHORITY'):assess(d)
 def test_invalid_date_fails(self):
  with self.assertRaises(ValueError):assess(self.state('not-a-date'))
