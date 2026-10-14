import sys, unittest, tempfile, json, io, zipfile
from pathlib import Path
import pandas as pd
from datetime import datetime
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import gate_btc_h31_recent_source as s
import gate_btc_b3_h31_prospective_collect as collector

class RecentSourceTests(unittest.TestCase):
    def test_continuation_is_future_only_and_preserves_legacy(self):
        old={'2026-08-10':{'WIN':'WINQ26','WDO':'WDOU26'}}
        new=s.source_schedule(old)
        self.assertEqual(new['2026-08-10'],old['2026-08-10'])
        self.assertNotIn('2026-10-14',new)
        self.assertEqual(new['2026-10-15'],{'WIN':'WINZ26','WDO':'WDOX26'})
        c=s.load_contract();self.assertEqual(len(c['warmup_dates']),30)
        self.assertEqual(c['warmup_credit'],0)
        self.assertEqual(len(c['sessions']),40)
        self.assertEqual(new['2026-10-30']['WIN'],'WINZ26')
        self.assertEqual(new['2026-10-30']['WDO_candidates'],['WDOX26','WDOZ26'])
        self.assertNotIn('2026-11-02',new)
        self.assertNotIn('2026-11-20',new)
        self.assertEqual(new['2026-12-11']['WDO_candidates'],['WDOZ26','WDOF27'])
        self.assertFalse(c['h1_economics_read'])
    def test_warmup_rejects_a_rehashed_credit(self):
        r={'date':'2026-09-16','contract_sha256':s.CONTRACT_SHA256,'structural_qa':'PASS','prospective_scored':False,'ret30_bps':1.,'eligible_observation_increment':1,'source_sha256':'a'*64}
        r['receipt_sha256']=s.digest(r)
        with self.assertRaisesRegex(RuntimeError,'CREDIT'):s.validate_receipt(r,r['date'])
    def test_missing_minute_cannot_be_filled_by_m5(self):
        def frame(periods,freq):
            ts=pd.date_range('2026-09-16 09:00',periods=periods,freq=freq,tz='America/Sao_Paulo')
            return pd.DataFrame({'timestamp':ts.astype(str),'date':'2026-09-16','root':'WDO','symbol':'WDOV26','open':5000.,'high':5000.,'low':5000.,'close':5000.,'volume':5.,'trades':1})
        with self.assertRaisesRegex(RuntimeError,'M1_M5_MISMATCH'):s.validate_bars('2026-09-16','WDOV26',frame(29,'min'),frame(6,'5min'))
    def test_fixed_offset_b3_timestamps_normalize_before_lattice_comparison(self):
        def frame(periods,freq,volume,trades):
            ts=pd.date_range('2026-09-16 09:00',periods=periods,freq=freq,tz='UTC-03:00')
            return pd.DataFrame({'timestamp':ts.astype(str),'date':'2026-09-16','root':'WDO','symbol':'WDOV26','open':5000.,'high':5000.,'low':5000.,'close':5000.,'volume':volume,'trades':trades})
        result=s.validate_bars('2026-09-16','WDOV26',frame(30,'min',5.,1),frame(6,'5min',25.,5))
        self.assertEqual(len(result),6)
    def test_auction_delayed_first_trade_preserves_observed_m5_without_fill(self):
        ts=pd.date_range('2026-09-16 09:04',periods=26,freq='min',tz='UTC-03:00')
        observed=pd.DataFrame({'timestamp':ts.astype(str),'date':'2026-09-16','root':'WDO','symbol':'WDOV26','open':5000.,'high':5000.,'low':5000.,'close':5000.,'volume':5.,'trades':1})
        m5=s.recompute_m5(observed);m5['date']='2026-09-16';m5.timestamp=m5.timestamp.astype(str)
        result=s.validate_bars('2026-09-16','WDOV26',observed,m5)
        self.assertEqual(len(result),6);self.assertEqual(result.iloc[0].trades,1)
    def test_missing_first_m5_bucket_still_fails(self):
        ts=pd.date_range('2026-09-16 09:06',periods=24,freq='min',tz='UTC-03:00')
        observed=pd.DataFrame({'timestamp':ts.astype(str),'date':'2026-09-16','root':'WDO','symbol':'WDOV26','open':5000.,'high':5000.,'low':5000.,'close':5000.,'volume':5.,'trades':1})
        m5=s.recompute_m5(observed);m5['date']='2026-09-16';m5.timestamp=m5.timestamp.astype(str)
        with self.assertRaisesRegex(RuntimeError,'LATTICE'):
            s.validate_bars('2026-09-16','WDOV26',observed,m5)
    def test_front_selection_cannot_read_later_volume_or_win_outcome(self):
        text='CodigoInstrumento;AcaoAtualizacao;QuantidadeNegociada;HoraFechamento;TipoSessaoPregao\nWDOX26;0;100;09:00:00;1\nWDOZ26;0;50;09:00:00;1\nWDOZ26;0;10000;09:30:00;1\nWINZ26;0;90000;09:00:00;1\n'
        data=io.BytesIO()
        with zipfile.ZipFile(data,'w') as z:z.writestr('2026-10-21_NEGOCIOSAVISTA.TXT',text)
        front,volumes=s.choose_wdo(data.getvalue())
        self.assertEqual(front,'WDOX26');self.assertEqual(volumes,{'WDOX26':100.,'WDOZ26':50.})
    def test_future_target_cannot_download_or_credit_before_its_session(self):
        contract={'first_eligible_date':'2026-08-25'}
        with tempfile.TemporaryDirectory() as d, patch.object(collector,'datetime') as clock, patch.object(collector,'trailing') as warmup, patch.object(collector,'fetch_official_session') as fetch:
            clock.now.return_value=datetime(2026,10,14,tzinfo=s.ZoneInfo('America/Sao_Paulo'))
            with self.assertRaisesRegex(RuntimeError,'WINDOW_EXPIRED_OR_NOT_OPEN'):
                collector.compute_event('2026-10-15',contract,Path(d))
            warmup.assert_not_called();fetch.assert_not_called();self.assertEqual(list(Path(d).iterdir()),[])
    def test_warmup_selection_uses_quality_then_dates_not_return_size(self):
        candidates=s.load_contract()['warmup_dates']
        def quality(day,ledger):
            if day=='2026-09-22':return None
            return {'ret30_bps':1e9 if day=='2026-09-01' else 1.,'receipt_sha256':day}
        with patch.object(s,'qualify',side_effect=quality):
            selected=s.trailing('2026-10-15',Path('unused'))
        self.assertEqual([r['date'] for r in selected],[d for d in candidates if d!='2026-09-22'][-20:])
        self.assertNotIn('2026-09-01',[r['date'] for r in selected])
    def test_twelve_valid_inputs_cannot_start_canonical_warmup(self):
        dates=set(s.load_contract()['warmup_dates'][-12:])
        def quality(day,ledger):return {'ret30_bps':1.,'receipt_sha256':day} if day in dates else None
        with patch.object(s,'qualify',side_effect=quality), patch.object(s,'frozen_seed',return_value=[]):
            with self.assertRaisesRegex(RuntimeError,'NEEDS_20_STRUCTURAL_PASS_INPUTS got=12'):
                s.trailing('2026-10-15',Path('unused'))
    def test_original_frozen_seed_completes_inputs_without_scored_credit(self):
        dates=set(s.load_contract()['warmup_dates'][-12:])
        historic=[{'date':'2025-12-'+str(d).zfill(2),'ret30_bps':1.,'source':'FROZEN_COMMUNITY_WARMUP','receipt_sha256':'frozen'} for d in range(1,21)]
        def quality(day,ledger):return {'ret30_bps':1.,'receipt_sha256':day} if day in dates else None
        with patch.object(s,'qualify',side_effect=quality), patch.object(s,'frozen_seed',return_value=historic):
            rows=s.trailing('2026-10-15',Path('unused'))
        self.assertEqual(len(rows),20)
        self.assertEqual(sum(r['source']=='FROZEN_COMMUNITY_WARMUP' for r in rows),8)
        self.assertEqual(sum(r['source']=='RECENT_OFFICIAL_B3_INPUT_ONLY' for r in rows),12)
    def test_frozen_binding_path_seed_hash_and_cache_leave_counter_untouched(self):
        from types import SimpleNamespace
        dates=[d for d in pd.bdate_range('2025-11-03',periods=25) if d.strftime('%Y-%m-%d')!='2025-11-20'][:20]
        lines=['Data;Hora;Abertura;Fechamento']
        for day in dates:
            for minute in range(0,30,5):lines.append(day.strftime('%d/%m/%Y')+f';09:{minute:02d};5.000,0;5.000,5')
        raw=('\n'.join(lines)+'\n').encode('cp1252')
        response=SimpleNamespace(content=raw,raise_for_status=lambda:None)
        with tempfile.TemporaryDirectory() as d, patch('requests.get',return_value=response) as fetch:
            status=Path(d)/'STATUS.json';status.write_text('immutable-counter')
            rows=s.frozen_seed(d);again=s.frozen_seed(d)
            self.assertEqual(len(rows),20);self.assertEqual(rows,again)
            self.assertEqual(fetch.call_count,1);self.assertEqual(status.read_text(),'immutable-counter')
            self.assertTrue(all(r['source']=='FROZEN_COMMUNITY_WARMUP' for r in rows))
    def test_receipt_change_fails_seal(self):
        r={'date':'2026-09-16','contract_sha256':s.CONTRACT_SHA256,'structural_qa':'PASS','prospective_scored':False,'ret30_bps':1.,'eligible_observation_increment':0,'source_sha256':'a'*64}
        r['receipt_sha256']=s.digest(r);s.validate_receipt(r,r['date']);r['ret30_bps']=2.
        with self.assertRaisesRegex(RuntimeError,'SEAL'):s.validate_receipt(r,r['date'])

if __name__=='__main__':unittest.main()
