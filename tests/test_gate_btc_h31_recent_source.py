import sys, unittest, tempfile, json, io, zipfile
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
        self.assertEqual(len(c['sessions']),12)
        self.assertEqual(new['2026-10-30']['WIN'],'WINZ26')
        self.assertEqual(new['2026-10-30']['WDO_candidates'],['WDOX26','WDOZ26'])
        self.assertNotIn('2026-11-02',new)
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
    def test_fixed_offset_b3_timestamps_normalize_before_lattice_comparison(self):
        def frame(periods,freq,volume,trades):
            ts=pd.date_range('2026-09-16 09:00',periods=periods,freq=freq,tz='UTC-03:00')
            return pd.DataFrame({'timestamp':ts.astype(str),'date':'2026-09-16','root':'WDO','symbol':'WDOV26','open':5000.,'high':5000.,'low':5000.,'close':5000.,'volume':volume,'trades':trades})
        result=s.validate_bars('2026-09-16','WDOV26',frame(30,'min',5.,1),frame(6,'5min',25.,5))
        self.assertEqual(len(result),6)
    def test_front_selection_cannot_read_later_volume_or_win_outcome(self):
        text='CodigoInstrumento;AcaoAtualizacao;QuantidadeNegociada;HoraFechamento;TipoSessaoPregao\nWDOX26;0;100;09:00:00;1\nWDOZ26;0;50;09:00:00;1\nWDOZ26;0;10000;09:30:00;1\nWINZ26;0;90000;09:00:00;1\n'
        data=io.BytesIO()
        with zipfile.ZipFile(data,'w') as z:z.writestr('2026-10-21_NEGOCIOSAVISTA.TXT',text)
        front,volumes=s.choose_wdo(data.getvalue())
        self.assertEqual(front,'WDOX26');self.assertEqual(volumes,{'WDOX26':100.,'WDOZ26':50.})
    def test_receipt_change_fails_seal(self):
        r={'date':'2026-09-16','contract_sha256':s.CONTRACT_SHA256,'structural_qa':'PASS','prospective_scored':False,'ret30_bps':1.,'eligible_observation_increment':0,'source_sha256':'a'*64}
        r['receipt_sha256']=s.digest(r);s.validate_receipt(r,r['date']);r['ret30_bps']=2.
        with self.assertRaisesRegex(RuntimeError,'SEAL'):s.validate_receipt(r,r['date'])

if __name__=='__main__':unittest.main()
