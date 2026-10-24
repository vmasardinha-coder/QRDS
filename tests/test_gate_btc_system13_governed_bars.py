import copy
import json
import tempfile
import unittest
from pathlib import Path
from tools import gate_btc_system13_governed_bars as g


class GovernedBars(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        proof=self.bound('proof.json', {'fixture': True})
        self.admission={'status':'QUALIFIED_FOR_SYSTEM13_OHLCV_IMPORT',
            'source_id':'FIXTURE_USD', 'market':'SPOT', 'quote_currency':'USD',
            'volume_unit':'BASE_ASSET', 'historical_reconstruction_allowed':False,
            'qualified_at_utc':'2026-10-20T00:00:00Z', 'adjustment_policy':'REVIEWED_SPOT_POLICY',
            'instrument_bindings':{'bitcoin':'BTC-USD'},
            **{k:proof for k in ('identity_evidence','tradability_evidence','adjustment_evidence')}}
        self.bar={'schema':'qrds.system13.native_daily_ohlcv.v1','source_id':'FIXTURE_USD',
            'coin_id':'bitcoin','venue_instrument':'BTC-USD',
            'open_at_utc':'2026-10-22T00:00:00Z','close_at_utc':'2026-10-23T00:00:00Z',
            'captured_at_utc':'2026-10-23T01:00:00Z',
            'open':100,'high':110,'low':90,'close':105,'volume':20,'factor':1,
            'volume_unit':'BASE_ASSET','quote_currency':'USD','adjustment_policy':'REVIEWED_SPOT_POLICY'}
        self.membership={'protocol_sha256':g.PROTOCOL_SHA256,'rows':[
            {'coin_id':'bitcoin','observed_at_utc':'2026-10-21T05:00:00Z',
             'eligible_by_observed_flags_and_quote':True}]}

    def bound(self,name,value):
        raw=json.dumps(value,sort_keys=True).encode();(self.root/name).write_bytes(raw)
        return {'path':name,'sha256':g.sha(raw)}

    def bundle(self):
        a=self.bound('admission.json',self.admission); b=self.bound('bar.json',self.bar)
        return {'schema':'qrds.system13.governed_bar_import.v1',
                'admission_path':a['path'],'admission_sha256':a['sha256'],
                'bars':[{'raw_path':b['path'],'raw_sha256':b['sha256']}]}

    def review(self):
        return g.inspect(self.root,self.bundle(),self.membership)

    def test_valid_row_keeps_insufficient_coverage_and_training_blocked(self):
        result=self.review(); self.assertEqual(result['validated_source_rows'],1)
        self.assertFalse(result['sessions'][0]['coverage_gate_pass'])
        for key in ('training_ready','holdout_read_allowed','system13_complete'):
            self.assertFalse(result[key])
        self.assertEqual(result['new_scientific_credit'],0)

    def test_reviewed_usdt_stays_usdt_without_conversion_or_training(self):
        self.admission['quote_currency']='USDT'
        self.admission['source_id']='FIXTURE_USDT'
        self.admission['instrument_bindings']['bitcoin']='BTCUSDT'
        self.bar.update(quote_currency='USDT',source_id='FIXTURE_USDT',venue_instrument='BTCUSDT')
        result=self.review()
        self.assertEqual(result['native_quote_currency'],'USDT')
        self.assertEqual(result['rows'][0]['quote_currency'],'USDT')
        self.assertEqual(result['rows'][0]['close'],105)
        self.assertFalse(result['quote_conversion_applied'])
        self.assertFalse(result['training_ready'])
        self.bar['quote_currency']='USD'
        with self.assertRaisesRegex(ValueError,'UNITS_OR_ADJUSTMENT'):self.review()

    def test_unreviewed_quote_currency_is_rejected(self):
        self.admission['quote_currency']='OTHER'
        self.bar['quote_currency']='OTHER'
        with self.assertRaisesRegex(ValueError,'ADMISSION_OR_UNITS'):self.review()

    def test_mutated_source_and_path_traversal_rejected(self):
        bundle=self.bundle();(self.root/'bar.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'HASH_MISMATCH'):
            g.inspect(self.root,bundle,self.membership)
        bundle['bars'][0]['raw_path']='../outside.json'
        with self.assertRaisesRegex(ValueError,'PATH_OUTSIDE'):
            g.inspect(self.root,bundle,self.membership)

    def test_quotes_dollar_volume_and_usdt_are_not_native_usd_bars(self):
        for field,value in [('schema','quote'),('volume_unit','USD'),('quote_currency','USDT')]:
            before=copy.deepcopy(self.bar); self.bar[field]=value
            with self.assertRaises(ValueError):self.review()
            self.bar=before

    def test_future_membership_and_newer_exclusion_are_not_bypassed(self):
        self.membership['rows'][0]['observed_at_utc']='2026-10-23T00:00:00Z'
        with self.assertRaisesRegex(ValueError,'MEMBERSHIP_OBSERVED'):self.review()
        self.membership['rows'][0]['observed_at_utc']='2026-10-20T00:00:00Z'
        self.membership['rows'].append({'coin_id':'bitcoin',
            'observed_at_utc':'2026-10-21T00:00:00Z','eligible_by_observed_flags_and_quote':False})
        with self.assertRaisesRegex(ValueError,'EXCLUDED_MEMBER'):self.review()

    def test_unclosed_backfilled_or_late_qualified_bar_fails(self):
        for value in ('2026-10-22T23:59:00Z','2026-10-24T00:00:00Z'):
            self.bar['captured_at_utc']=value
            with self.assertRaisesRegex(ValueError,'UNFINISHED_OR_LATE'):self.review()
        self.bar['captured_at_utc']='2026-10-23T01:00:00Z'
        self.admission['qualified_at_utc']='2026-10-22T01:00:00Z'
        with self.assertRaisesRegex(ValueError,'QUALIFIED_BEFORE'):self.review()

    def test_identity_and_ohlc_and_nonfinite_fail(self):
        for field,value in [('venue_instrument','OTHER-USD'),('high',99),('factor',0),('close',float('nan'))]:
            before=copy.deepcopy(self.bar);self.bar[field]=value
            with self.assertRaises(ValueError):self.review()
            self.bar=before

    def test_duplicate_bars_fail_and_absent_members_remain_in_denominator(self):
        bundle=self.bundle();bundle['bars']*=2
        with self.assertRaisesRegex(ValueError,'DUPLICATE_BAR'):
            g.inspect(self.root,bundle,self.membership)
        self.membership['rows'].append({'coin_id':'missing',
            'observed_at_utc':'2026-10-21T05:00:00Z','eligible_by_observed_flags_and_quote':True})
        result=self.review(); session=result['sessions'][0]
        self.assertEqual(session['coverage_fraction'],.5)
        self.assertEqual(session['missing_coin_ids'],['missing'])


if __name__=='__main__':unittest.main()
