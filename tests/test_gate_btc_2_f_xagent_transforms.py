from __future__ import annotations
import importlib.util, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MODULE_PATH=ROOT/'tools'/'gate_btc_2_f_xagent_transforms.py'
spec=importlib.util.spec_from_file_location('xagent',MODULE_PATH); xagent=importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(xagent)

class XAgentTests(unittest.TestCase):
    def test_disagreement_consensus(self):
        r=xagent.disagreement_features([0.8,0.7,0.9,None])
        self.assertTrue(r['eligible']); self.assertEqual(r['available_count'],3); self.assertEqual(r['unavailable_count'],1)
        self.assertGreater(r['consensus_mean'],0.0); self.assertLess(r['pairwise_disagreement'],0.2)
    def test_disagreement_split(self):
        r=xagent.disagreement_features([1.0,-1.0,0.5,-0.5])
        self.assertTrue(r['eligible']); self.assertGreater(r['pairwise_disagreement'],0.5); self.assertEqual(r['sign_split_fraction'],0.5)
    def test_unavailable_not_zero_filled(self):
        r=xagent.disagreement_features([1.0,1.0,None])
        self.assertFalse(r['eligible']); self.assertEqual(r['disposition'],'ABSTAIN / INSUFFICIENT_INDEPENDENT_SIGNALS')
    def test_signal_range_fail_closed(self):
        with self.assertRaises(ValueError): xagent.disagreement_features([0.1,0.2,1.1])
    def test_veto_priority(self):
        r=xagent.risk_veto_decision(['ALLOW','ABSTAIN_UNAVAILABLE','VETO'])
        self.assertEqual(r['aggregate_decision'],'VETO')
    def test_unavailable_abstains_not_allows(self):
        r=xagent.risk_veto_decision(['ALLOW','ABSTAIN_UNAVAILABLE'])
        self.assertEqual(r['aggregate_decision'],'ABSTAIN')
    def test_all_allow(self):
        r=xagent.risk_veto_decision(['ALLOW','ALLOW'])
        self.assertEqual(r['aggregate_decision'],'ALLOW')
    def test_invalid_state_fails(self):
        with self.assertRaises(ValueError): xagent.risk_veto_decision(['ALLOW','NEUTRAL'])

if __name__=='__main__': unittest.main()
