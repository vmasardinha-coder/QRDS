import gzip
import importlib.util
import json
import unittest
from pathlib import Path

PATH=Path('tools/gate_btc_factory/us_mega_tech_data_probe.py')
spec=importlib.util.spec_from_file_location('probe',PATH)
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)

class ProbeTests(unittest.TestCase):
    def test_parse_sec_tickers(self):
        obj={'0':{'ticker':'AAPL','cik_str':320193,'title':'Apple Inc.'}}
        out=p.parse_sec_tickers(obj)
        self.assertEqual(out['AAPL']['cik'],320193)
    def test_decode_json_accepts_gzip(self):
        raw=gzip.compress(json.dumps({'ok':True}).encode('utf-8'))
        self.assertEqual(p.decode_json(raw),{'ok':True})
    def test_parse_nasdaq_rows_filters_incomplete(self):
        obj={'data':{'tradesTable':{'rows':[{'date':'09/18/2026','close':'$100','volume':'1,000','open':'$99','high':'$101','low':'$98'},{'date':None,'close':'$99','volume':'900'}]}}}
        rows=p.parse_nasdaq_rows(obj)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['date'],'09/18/2026')
    def test_safety_locks(self):
        self.assertTrue(p.SAFETY['RESEARCH_ONLY'])
        self.assertTrue(p.SAFETY['SHADOW_ONLY'])
        self.assertFalse(p.SAFETY['ENGINE_FEED'])
        self.assertEqual(p.SAFETY['ORDERS'],0)
        self.assertEqual(p.SAFETY['REAL_CAPITAL'],0)
        self.assertTrue(p.SAFETY['NO_BACKFILL'])
        self.assertTrue(p.SAFETY['NO_RETUNE'])

if __name__=='__main__':unittest.main()
