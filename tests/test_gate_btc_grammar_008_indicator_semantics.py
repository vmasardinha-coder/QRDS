import json
import unittest
from pathlib import Path

P=Path('tools/gate_btc_factory/GRAMMAR_008_INDICATOR_SEMANTICS_20260921.json')

class Grammar008IndicatorSemanticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.x=json.loads(P.read_text())
    def test_boundary(self):
        x=self.x
        self.assertEqual(x['status'],'FROZEN_BEFORE_FIRST_GRAMMAR_008_MARKET_DATA_READ')
        self.assertFalse(x['market_data_read_at_freeze']);self.assertFalse(x['outcomes_read_at_freeze']);self.assertFalse(x['economics_read_at_freeze'])
        self.assertEqual(x['scientific_credit'],0)
    def test_exact_math(self):
        d=self.x['definitions']
        self.assertEqual(d['POPULATION_SD']['ddof'],0)
        self.assertEqual(d['EMA']['alpha'],'2/(n+1)')
        self.assertEqual(d['RSI14']['method'],'WILDER')
        self.assertIn('3*EMA1-3*EMA2+EMA3',d['TEMA']['formula'])
    def test_underspecified_candidate_fails_closed(self):
        z=self.x['candidate_semantic_dispositions']
        self.assertEqual(z['MORNING_STAR'],'INELIGIBLE_FAIL_CLOSED_UNDERSPECIFIED_LARGE_FIRST_BODY')
        self.assertEqual(self.x['registered_candidate_count'],24)
        self.assertEqual(self.x['executable_candidate_count'],22)
    def test_safety(self):
        s=self.x['safety'];self.assertTrue(s['RESEARCH_ONLY']);self.assertTrue(s['SHADOW_ONLY']);self.assertTrue(s['FAIL_CLOSED'])
        self.assertFalse(s['ENGINE_FEED']);self.assertEqual(s['ORDERS'],0);self.assertEqual(s['REAL_CAPITAL'],0)

if __name__=='__main__': unittest.main()
