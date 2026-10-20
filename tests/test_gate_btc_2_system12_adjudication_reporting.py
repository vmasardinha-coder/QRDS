import copy
import json
import unittest
import tests.test_gate_btc_2_system12_readiness as legacy
from gate_btc_2_system12_readiness import (
    ADJUDICATION_AUTHORITY, retain_replication_progress, retain_adjudication_progress,
)


class AdjudicationReportingTests(unittest.TestCase):
    def inputs(self):
        s, c, r = legacy.ReplicationContinuityTests().inputs()
        return retain_replication_progress(s, c, r), c, json.loads(ADJUDICATION_AUTHORITY.read_text(encoding='utf-8'))

    def test_separate_review_is_retained_without_operational_promotion(self):
        args = self.inputs(); before = copy.deepcopy(args)
        out = retain_adjudication_progress(*args)
        self.assertTrue(out['independent_adjudication_executed'])
        self.assertEqual(out['status'], 'FROZEN_PARITY_ADJUDICATED_PENDING_FORMAL_RELEASE')
        for k in ['system12_complete', 'system13_dependency_released', 'engine_feed',
                  'system12_completion_authorized', 'system13_release_authorized']:
            self.assertIs(out[k], False)
        for k in ['orders', 'real_capital_brl', 'scientific_credit']:
            self.assertEqual(out[k], 0)
        self.assertEqual(args, before)

    def test_changed_review_cannot_claim_signature_or_release(self):
        for key in ['decision', 'scope', 'blocking_limitations', 'contract_semantic_sha256']:
            with self.subTest(key=key):
                s, c, review = self.inputs()
                review[key] = 'changed'
                out = retain_adjudication_progress(s, c, review)
                self.assertEqual(out['adjudication_receipt_status'], 'INVALID')
                self.assertFalse(out['independent_adjudication_executed'])
        s, c, review = self.inputs()
        review['operational_effect']['system13_dependency_released'] = True
        self.assertEqual(retain_adjudication_progress(s, c, review)['adjudication_receipt_status'], 'INVALID')

    def test_missing_review_preserves_existing_stage(self):
        s, c, _ = self.inputs()
        out = retain_adjudication_progress(s, c, None)
        self.assertEqual(out['status'], s['status'])
        self.assertFalse(out['independent_adjudication_executed'])

    def test_review_cannot_replace_invalid_or_different_replication(self):
        s, c, review = self.inputs()
        s['replication_continuity_status'] = 'INVALID_FROZEN_REPLICATION_RECEIPT'
        out = retain_adjudication_progress(s, c, review)
        self.assertFalse(out['independent_adjudication_executed'])
        s, c, review = self.inputs(); c['bindings']['dataset_semantic_sha256'] = 'different'
        self.assertEqual(retain_adjudication_progress(s, c, review)['adjudication_receipt_status'], 'INVALID')

    def test_current_collection_failure_is_not_hidden_by_frozen_review(self):
        s, c, review = self.inputs()
        s.update(upstream_system11_ready=False, status='BLOCKED_INVALID_SYSTEM11_EVIDENCE')
        out = retain_adjudication_progress(s, c, review)
        self.assertTrue(out['independent_adjudication_executed'])
        self.assertEqual(out['status'], 'BLOCKED_INVALID_SYSTEM11_EVIDENCE')
        self.assertFalse(out['system13_dependency_released'])


if __name__ == '__main__':
    unittest.main()
