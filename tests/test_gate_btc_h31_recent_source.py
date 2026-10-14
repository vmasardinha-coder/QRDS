import sys, unittest, tempfile, json
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import gate_btc_h31_recent_source as s

class RecentSourceTests(unittest.TestCase):
    def test_continuation_is_future_only_and_preserves_legacy(self):
        old={'2026-08-10':{'WIN':'WINQ26','WDO':'WDOU26'}}
        new=s.source_schedule(old)
        self.assertEqual(new['2026-08-10'],old['2026-08-10'])
        self.assertNotIn('2026-10-14',new)
        self.assertEqual(new['2026-10-15'],{'WIN':'WINZ26','WDO':'WDOX26'})
        c=s.load_contract();self.assertEqual(len(c['warmup_dates']),20)
        self.assertEqual(c['warmup_credit'],0)
        self.assertFalse(c['h1_economics_read'])
    def test_warmup_rejects_a_rehashed_credit(self):
        r={'date':'2026-09-16','contract_sha256':s.CONTRACT_SHA256,'structural_qa':'PASS','prospective_scored':False,'ret30_bps':1.,'eligible_observation_increment':1,'source_sha256':'a'*64}
        r['receipt_sha256']=s.digest(r)
        with self.assertRaisesRegex(RuntimeError,'CREDIT'):s.validate_receipt(r,r['date'])
    def test_missing_minute_cannot_be_filled_by_m5(self):
        def frame(periods,freq):
            ts=pd.date_range('2026-09-16 09:00',periods=periods,freq=freq,tz='America/Sao_Paulo')
            return pd.DataFrame({'timestamp':ts.astype(str),'date':'2026-09-16','root':'WDO','symbol':'WDOV26','open':5000.,'high':5000.,'low':5000.,'close':5000.,'volume':5.,'trades':1})
        with self.assertRaisesRegex(RuntimeError,'LATTICE'):s.validate_bars('2026-09-16','WDOV26',frame(29,'min'),frame(6,'5min'))
    def test_receipt_change_fails_seal(self):
        r={'date':'2026-09-16','contract_sha256':s.CONTRACT_SHA256,'structural_qa':'PASS','prospective_scored':False,'ret30_bps':1.,'eligible_observation_increment':0,'source_sha256':'a'*64}
        r['receipt_sha256']=s.digest(r);s.validate_receipt(r,r['date']);r['ret30_bps']=2.
        with self.assertRaisesRegex(RuntimeError,'SEAL'):s.validate_receipt(r,r['date'])

if __name__=='__main__':unittest.main()
