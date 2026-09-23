import json
import unittest
from pathlib import Path

P = Path('artifacts/gate_btc_2/family_handoffs/XAGENT_SIGNAL_BINDING_AUDIT_20260922.json')


class XAgentSignalBindingAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x = json.loads(P.read_text(encoding='utf-8'))

    def test_no_posthoc_binding(self):
        x = self.x
        self.assertEqual(x['family_id'], 'F-XAGENT-DISAGREE')
        self.assertFalse(x['economics_read_for_binding_selection'])
        self.assertEqual(x['eligible_existing_trios'], [])
        self.assertEqual(
            x['conclusion'],
            'NO_EXISTING_THREE_SIGNAL_BINDING_CAN_BE_FROZEN_WITHOUT_NEW_SCIENTIFIC_SEMANTICS'
        )

    def test_required_contract_preserved(self):
        r = self.x['required_binding']
        self.assertEqual(r['minimum_signals'], 3)
        self.assertEqual(r['range'], [-1.0, 1.0])
        self.assertTrue(r['distinct_evidence_or_family_channels'])
        self.assertEqual(r['missing_policy'], 'EXCLUDE_AND_COUNT_NOT_ZERO_FILL')
        self.assertTrue(r['common_causal_timestamps_required'])

    def test_xmm_xvol_not_silently_directionalized(self):
        rows = {r['channel']: r for r in self.x['reviewed_channels']}
        self.assertFalse(rows['F-XMM-INVENTORY']['eligible_as_existing_xagent_signal'])
        self.assertFalse(rows['F-XVOL-SURFACE']['eligible_as_existing_xagent_signal'])
        self.assertTrue(any('economic_direction is null' in z for z in rows['F-XMM-INVENTORY']['reasons']))
        self.assertTrue(any('economic_direction is null' in z for z in rows['F-XVOL-SURFACE']['reasons']))

    def test_parallel_frontier_is_zero_credit_outcome_blind(self):
        p = self.x['parallel_frontier']
        self.assertTrue(p['applicable'])
        self.assertFalse(p['manual_selection'])
        self.assertFalse(p['pnl_selection'])
        self.assertEqual(p['family_namespace'], 'PF::')
        self.assertEqual(p['historical_credit'], 0)
        self.assertEqual(p['retroactive_credit'], 0)
        self.assertFalse(p['promotion_authority'])

    def test_safety(self):
        s = self.x['safety']
        self.assertTrue(s['RESEARCH_ONLY'])
        self.assertTrue(s['SHADOW_ONLY'])
        self.assertFalse(s['ENGINE_FEED'])
        self.assertEqual(s['ORDERS'], 0)
        self.assertEqual(s['REAL_CAPITAL'], 0)
        self.assertTrue(s['NO_RETUNE'])
        self.assertTrue(s['NO_BACKFILL'])
        self.assertTrue(s['H1_H31_UNTOUCHED'])


if __name__ == '__main__':
    unittest.main()
