import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'tools'/'gate_btc_2_system8_universe_source_coingecko_v1.json'

class System8UniverseSourcePreregTests(unittest.TestCase):
    def test_contract_is_frozen_and_zero_credit(self):
        d=json.loads(SRC.read_text(encoding='utf-8'))
        self.assertEqual(d['schema'],'gate_btc.2_0.system8_universe_source_preregistration.v1')
        self.assertEqual(d['epoch_id'],'GATE_BTC_2_SYSTEM8_PROSPECTIVE_EPOCH_2026_09_03')
        self.assertEqual(d['source_id'],'COINGECKO_PUBLIC_MARKETS_TOP150_USD_V1')
        self.assertEqual(d['status'],'PREREGISTERED_NOT_QUALIFIED')
        r=d['request_contract']
        self.assertEqual(r['vs_currency'],'usd')
        self.assertEqual(r['order'],'market_cap_desc')
        self.assertEqual(r['per_page'],100)
        self.assertEqual(r['pages'],[1,2])
        self.assertEqual(r['target_universe_size'],150)
        self.assertEqual(r['identity_key'],'id')
        q=d['qualification_requirements']
        self.assertTrue(q['raw_http_bytes_preserved'])
        self.assertTrue(q['sha256_per_page_required'])
        self.assertEqual(q['minimum_combined_rows'],150)
        c=d['credit_boundary']
        self.assertEqual(c['preregistration_credit'],0)
        self.assertEqual(c['qualification_credit'],0)
        self.assertEqual(c['pre_merge_capture_credit'],0)
        self.assertEqual(c['historical_credit'],0)
        self.assertTrue(c['first_epoch_universe_credit_requires_separate_post_qualification_activation'])
        s=d['safety']
        self.assertTrue(s['RESEARCH_ONLY'] and s['SHADOW_ONLY'] and s['NOT_APPROVED'])
        self.assertFalse(s['ENGINE_FEED'])
        self.assertEqual(s['ORDERS'],0)
        self.assertEqual(s['REAL_CAPITAL_BRL'],0)
        self.assertTrue(s['NO_RETUNE'] and s['NO_BACKFILL'] and s['NO_COUNTER_RESET'] and s['NO_SILENT_SOURCE_SUBSTITUTION'] and s['FAIL_CLOSED'])

if __name__=='__main__': unittest.main()
