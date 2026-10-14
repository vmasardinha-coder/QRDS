import unittest
from tools.gate_btc_bybit_recovery_receipt import classify


class RecoveryReceiptTests(unittest.TestCase):
    def fixture(self, conclusion='success'):
        run = dict(id=123, name='GATE BTC Bybit Spot Recovery Audit', head_branch='main',
                   status='completed', conclusion='success')
        jobs = {'jobs': [dict(id=456, run_id=123, name='bybit-spot-recovery-audit',
                              status='completed', conclusion=conclusion)]}
        return run, jobs

    def test_workflow_success_with_skipped_collection_waits_without_price_evidence(self):
        receipt = classify(*self.fixture('skipped'))
        self.assertFalse(receipt['eligible'])
        self.assertEqual(receipt['status'], 'WAIT_UPSTREAM_RECOVERY_JOB_SKIPPED')
        self.assertEqual(receipt['scientific_credit'], 0)
        self.assertFalse(receipt['engine_feed'])

    def test_only_successful_exact_job_is_eligible(self):
        self.assertTrue(classify(*self.fixture())['eligible'])
        for conclusion in ('failure', 'cancelled', None):
            with self.subTest(conclusion=conclusion), self.assertRaises(ValueError):
                classify(*self.fixture(conclusion))

    def test_missing_duplicate_or_other_run_receipt_is_rejected(self):
        run, jobs = self.fixture()
        for payload in ({'jobs': []}, {'jobs': jobs['jobs'] * 2},
                        {'jobs': [{**jobs['jobs'][0], 'run_id': 999}]}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                classify(run, payload)

    def test_non_main_or_wrong_workflow_is_rejected(self):
        run, jobs = self.fixture()
        for change in ({'head_branch': 'untrusted'}, {'name': 'unrelated'},
                       {'conclusion': 'failure'}, {'status': 'in_progress'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                classify({**run, **change}, jobs)
