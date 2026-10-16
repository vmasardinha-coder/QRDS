import copy,hashlib,json,tempfile,unittest,zipfile
from datetime import datetime,timezone
from pathlib import Path
from tools.gate_btc_pit150_qualified_history import ROUTES,route_for_member,check_identity,check_alpha_exchange,normalize_history,collect_history
ROOT=Path(__file__).resolve().parents[1]/'artifacts/gate_btc_2/pit150_koge_alpha_20261016'
def raw(name):
    with zipfile.ZipFile(ROOT/'RAW.zip') as z:return z.read(name+'.json')
def load(name):return json.loads(raw(name))
class KogeAlphaTests(unittest.TestCase):
    def test_exact_identity_and_546_reported_days(self):
        route=ROUTES['KOGE'];check_identity(route,load('identity'));check_alpha_exchange(route,load('exchange'))
        rows=normalize_history('KOGE',route,load('candles'),'2026-10-14')
        self.assertEqual((len(rows),rows[0]['date'],rows[-1]['date']),(546,'2025-04-17','2026-10-14'))
        selected=rows[-200:]
        self.assertEqual(sum(x['volume_usd']==0 for x in selected),6)
        self.assertEqual(rows[-1]['volume_usd'],54.23665043)
    def test_no_past_or_wrong_coin_activation(self):
        self.assertIsNone(route_for_member('KOGE','bnb48-club-token','2026-10-15'))
        self.assertIsNone(route_for_member('KOGE','other','2026-10-16'))
        self.assertEqual(route_for_member('KOGE','bnb48-club-token','2026-10-16')['pair'],'ALPHA_22USDT')
    def test_wrong_contract_chain_alpha_and_duplicate_rejected(self):
        for key,value in [('contractAddress','0xwrong'),('chainId','1'),('alphaId','ALPHA_23'),('offline',True),('name','Different')]:
            p=load('identity');entry=next(x for x in p['data'] if x.get('symbol')=='KOGE');entry[key]=value
            with self.assertRaises(ValueError):check_identity(ROUTES['KOGE'],p)
        p=load('identity');p['data'].append(copy.deepcopy(next(x for x in p['data'] if x.get('symbol')=='KOGE')))
        with self.assertRaises(ValueError):check_identity(ROUTES['KOGE'],p)
    def test_pair_timezone_quote_status_and_ambiguity_rejected(self):
        for key,value in [('baseAsset','ALPHA_23'),('quoteAsset','BNB'),('status','DELISTED')]:
            p=load('exchange');next(x for x in p['data']['symbols'] if x['symbol']=='ALPHA_22USDT')[key]=value
            with self.assertRaises(ValueError):check_alpha_exchange(ROUTES['KOGE'],p)
        p=load('exchange');p['data']['timezone']='UTC+8'
        with self.assertRaises(ValueError):check_alpha_exchange(ROUTES['KOGE'],p)
        p=load('exchange');p['data']['symbols'].append(copy.deepcopy(next(x for x in p['data']['symbols'] if x['symbol']=='ALPHA_22USDT')))
        with self.assertRaises(ValueError):check_alpha_exchange(ROUTES['KOGE'],p)
    def test_missing_day_duplicate_ohlc_volume_schema_and_partial_day_rejected(self):
        for kind in ['gap','duplicate','ohlc','negative','nan','partial','schema','count']:
            p=load('candles');r=p['data'][-1]
            if kind=='gap':p['data'].pop(-2)
            if kind=='duplicate':p['data'].append(copy.deepcopy(r))
            if kind=='ohlc':r[3]='99999'
            if kind=='negative':r[7]='-1'
            if kind=='nan':r[7]='NaN'
            if kind=='partial':r[6]=str(int(r[6])-1)
            if kind=='schema':r.pop()
            if kind=='count':r[8]='0'
            with self.assertRaises(ValueError):normalize_history('KOGE',ROUTES['KOGE'],p,'2026-10-14')
    def test_transport_failure_rejected(self):
        for name,fn in [('identity',check_identity),('exchange',check_alpha_exchange)]:
            p=load(name);p['success']=False
            with self.assertRaises(ValueError):fn(ROUTES['KOGE'],p)
        p=load('candles');p['code']='error'
        with self.assertRaises(ValueError):normalize_history('KOGE',ROUTES['KOGE'],p,'2026-10-14')
    def test_mock_future_collection_preserves_three_responses(self):
        p=load('candles')
        for x in p['data']:x[0]=str(int(x[0])+2*86400000);x[6]=str(int(x[6])+2*86400000)
        values=[raw('identity'),raw('exchange'),json.dumps(p).encode()];urls=[]
        class Session:
            def get(self,url,timeout):
                urls.append(url)
                class Response:status_code=200
                response=Response();response.content=values.pop(0);return response
        with tempfile.TemporaryDirectory() as temp:
            rows,e=collect_history(Session(),'KOGE','bnb48-club-token','2026-10-16',temp,now=datetime(2026,10,17,tzinfo=timezone.utc))
            self.assertEqual(rows[-1]['date'],'2026-10-16');self.assertEqual(e['historical_scientific_credit'],0)
            self.assertFalse(e['collector_forward_fill'])
            self.assertEqual(e['volume_field'],'quote_volume_index_7')
            self.assertEqual(len(e['provider_reported_zero_volume_days_in_last200']),6)
            self.assertEqual((Path(temp)/'KOGE/exchange.json').read_bytes(),raw('exchange'))
            self.assertIn('ALPHA_22USDT',urls[-1])
        with self.assertRaises(ValueError):
            collect_history(Session(),'KOGE','bnb48-club-token','2026-10-16','unused',now=datetime(2026,10,16,tzinfo=timezone.utc))
    def test_frozen_evidence_hashes(self):
        proof=json.loads((ROOT/'PROOF.json').read_bytes())
        for name,expected in proof['raw_sha256'].items():
            self.assertEqual(hashlib.sha256(raw(name.removesuffix('.json'))).hexdigest(),expected)
if __name__=='__main__':unittest.main()
