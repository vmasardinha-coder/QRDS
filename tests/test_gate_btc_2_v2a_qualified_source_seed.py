import json
import re
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SEED=ROOT/'tools'/'gate_btc_2_v2a_qualified_source_seed_v1.json'
HEX64=re.compile(r'^[0-9a-f]{64}$')

class QualifiedSourceSeedTests(unittest.TestCase):
    def test_seed_is_partial_exact_and_zero_credit(self):
        d=json.loads(SEED.read_text(encoding='utf-8'))
        self.assertEqual(d['schema'],'gate_btc.v2a_qualified_source_seed.v1')
        self.assertEqual(d['epoch_id'],'GATE_BTC_2_V2A_PROSPECTIVE_EPOCH_2026_09_03')
        self.assertEqual(d['status'],'PARTIAL_SEED_NOT_D0_REGISTRY')
        entries=d['entries']
        self.assertGreater(len(entries),0)
        symbols=[e['symbol'] for e in entries]
        self.assertEqual(len(symbols),len(set(symbols)))
        for e in entries:
            self.assertEqual(e['qualification'],'QUALIFIED_EXACT_SOURCE')
            self.assertTrue(e['source_identity'])
            self.assertTrue(e['source_symbol'])
            self.assertTrue(HEX64.fullmatch(e['provenance_sha256']))
            self.assertEqual(e['timezone'],'UTC')
            self.assertTrue(e['cutoff_semantics'])
            self.assertTrue(e['qa_pass'])
            self.assertIsInstance(e['adjudication_pr'],int)
            self.assertGreater(e['adjudication_pr'],0)
        c=d['credit_boundary']
        self.assertEqual(c['epoch_credit'],0)
        self.assertEqual(c['d0_credit'],0)
        self.assertEqual(c['historical_credit'],0)
        self.assertFalse(c['complete_registry_claimed'])
        self.assertFalse(c['collector_override_activation_allowed'])
        s=d['safety']
        self.assertTrue(s['RESEARCH_ONLY'] and s['SHADOW_ONLY'] and s['NOT_APPROVED'])
        self.assertFalse(s['ENGINE_FEED'])
        self.assertEqual(s['ORDERS'],0)
        self.assertEqual(s['REAL_CAPITAL_BRL'],0)
        self.assertTrue(s['NO_RETUNE'] and s['NO_BACKFILL'] and s['NO_COUNTER_RESET'] and s['NO_SILENT_SOURCE_SUBSTITUTION'] and s['FAIL_CLOSED'])

if __name__=='__main__': unittest.main()
