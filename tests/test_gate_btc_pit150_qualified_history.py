import copy
import json
import tempfile
import unittest
from datetime import datetime,timezone,timedelta
from tools.gate_btc_pit150_qualified_history import ROUTES,route_for_member,check_identity,check_gate_contract,check_bitget_contract,normalize_history,collect_history

class QualifiedHistoryTests(unittest.TestCase):
    def candles(self, count=200):
        last=datetime(2026,10,13,tzinfo=timezone.utc)
        return [[str(int((last-timedelta(days=i)).timestamp())),"10","2","3","1","2"] for i in range(count)]

    def test_past_cutoffs_and_wrong_identity_never_activate(self):
        self.assertIsNone(route_for_member("DRV","derive","2026-10-12"))
        self.assertIsNone(route_for_member("DRV","wrong-token","2026-10-13"))
        self.assertIsNone(route_for_member("PRL","pearl-2","2026-10-13"))
        self.assertIsNotNone(route_for_member("DRV","derive","2026-10-13"))

    def test_future_partial_candle_is_excluded(self):
        rows=self.candles()+[[str(int(datetime(2026,10,14,tzinfo=timezone.utc).timestamp())),"10","2","3","1","2"]]
        out=normalize_history("DRV",ROUTES["DRV"],rows,"2026-10-13")
        self.assertEqual(len(out),200)
        self.assertEqual(out[-1]["date"],"2026-10-13")

    def test_short_duplicate_missing_and_stale_history_are_rejected(self):
        variants=[self.candles(199),self.candles()+[self.candles()[0]],self.candles(201)[:50]+self.candles(201)[51:],self.candles()[1:]]
        for rows in variants:
            with self.assertRaises(ValueError):normalize_history("DRV",ROUTES["DRV"],rows,"2026-10-13")

    def test_nonphysical_prices_volumes_and_nonUTC_buckets_rejected(self):
        for index,value in [(0,str(int(self.candles()[0][0])+3600)),(1,"-1"),(2,"NaN"),(3,"0.1"),(4,"5")]:
            rows=self.candles();rows[0][index]=value
            with self.assertRaises(ValueError):normalize_history("DRV",ROUTES["DRV"],rows,"2026-10-13")

    def test_same_ticker_wrong_contract_or_name_is_not_identity(self):
        route=ROUTES["BP"]
        meta={"symbols":[{"symbol":"BPUSDT","quoteAsset":"USDT","fullName":"Backpack","contractAddress":route["contract"],"isSpotTradingAllowed":True}]}
        check_identity(route,meta)
        for key,value in [("contractAddress","other-mint"),("fullName","Other BP"),("isSpotTradingAllowed",False)]:
            bad=copy.deepcopy(meta);bad["symbols"][0][key]=value
            with self.assertRaises(ValueError):check_identity(route,bad)

    def test_wrong_xt_contract_is_rejected(self):
        meta={"rc":0,"result":{"symbols":[{"symbol":"shfl_usdt","baseCurrency":"shfl","quoteCurrency":"usdt","state":"ONLINE","chainRelation":[{"contract":ROUTES["SHFL"]["contract"].upper()}]}]}}
        check_identity(ROUTES["SHFL"],meta)
        meta["result"]["symbols"][0]["chainRelation"][0]["contract"]="0xwrong"
        with self.assertRaises(ValueError):check_identity(ROUTES["SHFL"],meta)

    def test_previously_admitted_mexc_routes_bind_name_contract_and_coin_id(self):
        previous={"MNT","HTX","BGB","KAS","KCS","BDX","XDC","AKE","BSV","APEPE"}
        self.assertEqual(len(ROUTES),23)
        for symbol in previous:
            route=ROUTES[symbol]
            self.assertIsNotNone(route_for_member(symbol,route["coin_id"],"2026-10-13"))
            self.assertIsNone(route_for_member(symbol,"other-coin","2026-10-13"))
            meta={"symbols":[{"symbol":route["pair"],"quoteAsset":"USDT","fullName":route["name"],"contractAddress":route["contract"],"isSpotTradingAllowed":True}]}
            check_identity(route,meta)
            meta["symbols"][0]["fullName"]="different project"
            with self.assertRaises(ValueError):check_identity(route,meta)

    def test_explicit_issuer_name_aliases_are_not_generic_fuzzy_matching(self):
        self.assertEqual(ROUTES["KCS"]["coin_id"],"kucoin-shares")
        self.assertEqual(ROUTES["KCS"]["name"],"KuCoin Token")
        self.assertEqual(ROUTES["AKE"]["name"],"AKEDO")
        self.assertEqual(ROUTES["BSV"]["name"],"BitcoinSV")
        self.assertEqual(ROUTES["APEPE"]["name"],"APE and PEPE")

    def test_gate_followup_identities_are_exact_and_short_usdy_is_not_admitted(self):
        self.assertNotIn('USDY',ROUTES)
        for symbol in ['GT','GHO','PIEVERSE']:
            route=ROUTES[symbol]
            self.assertIsNotNone(route_for_member(symbol,route['coin_id'],'2026-10-13'))
            self.assertIsNone(route_for_member(symbol,'different-token','2026-10-13'))
            meta={'id':route['pair'],'base':symbol,'quote':'USDT','base_name':route['name'],'trade_status':'tradable'}
            check_identity(route,meta)
            for key,value in [('base','DRV'),('base_name','wrong issuer'),('id','other_USDT'),('trade_status','untradable')]:
                bad=dict(meta);bad[key]=value
                with self.assertRaises(ValueError):check_identity(route,bad)

    def test_quote_volume_uses_mexc_quote_field(self):
        rows=[[int(x[0])*1000,"2","3","1","2","900",int(x[0])*1000+86399999,"42"] for x in self.candles()]
        out=normalize_history("BP",ROUTES["BP"],rows,"2026-10-13")
        self.assertEqual(out[-1]["volume_usd"],42)

    def test_gate_new_tokens_require_exact_chain_and_contract(self):
        for symbol in ['AERO','SPX']:
            route=ROUTES[symbol]
            meta={'currency':symbol,'name':route['name'],'delisted':False,'trade_disabled':False,'chains':[{'name':route['contract_chain'],'addr':route['contract']}]}
            check_gate_contract(route,meta)
            for key,value in [('currency','OTHER'),('name','Other Project'),('delisted',True),('trade_disabled',True)]:
                bad=copy.deepcopy(meta);bad[key]=value
                with self.assertRaises(ValueError):check_gate_contract(route,bad)
            for key,value in [('name','OTHER_CHAIN'),('addr','0xwrong')]:
                bad=copy.deepcopy(meta);bad['chains'][0][key]=value
                with self.assertRaises(ValueError):check_gate_contract(route,bad)
            bad=copy.deepcopy(meta);bad['chains']*=2
            with self.assertRaises(ValueError):check_gate_contract(route,bad)

    def test_deribit_exact_product_and_complete_hourly_aggregation(self):
        route=ROUTES['USYC']
        meta={'jsonrpc':'2.0','testnet':False,'result':{'instrument_name':'USYC_USDC','instrument_id':377252,'base_currency_uuid':route['base_currency_uuid'],'kind':'spot','state':'open','is_active':True,'base_currency':'USYC','quote_currency':'USDC','counter_currency':'USDC'}}
        check_identity(route,meta)
        for key,value in [('instrument_id',999),('base_currency_uuid','other'),('kind','future'),('quote_currency','BTC'),('is_active',False)]:
            bad=copy.deepcopy(meta);bad['result'][key]=value
            with self.assertRaises(ValueError):check_identity(route,bad)
        end=datetime(2026,10,14,tzinfo=timezone.utc)
        ticks=[int((end-timedelta(hours=i)).timestamp()*1000) for i in range(4800,0,-1)]
        data={'ticks':ticks,'open':[2]*4800,'high':[3]*4800,'low':[1]*4800,'close':[2]*4800,'volume':[900]*4800,'cost':[42]*4800,'status':'ok'}
        payload={'jsonrpc':'2.0','testnet':False,'result':data}
        rows=normalize_history('USYC',route,payload,'2026-10-13')
        self.assertEqual(len(rows),200);self.assertEqual(rows[-1]['date'],'2026-10-13')
        self.assertEqual(rows[-1]['volume_usd'],24*42)
        for kind in ['gap','duplicate','offset','badprice','badcost','testnet']:
            bad=copy.deepcopy(payload)
            if kind=='gap':bad['result']['ticks'].pop()
            elif kind=='duplicate':bad['result']['ticks'][1]=bad['result']['ticks'][0]
            elif kind=='offset':bad['result']['ticks'][0]+=1000
            elif kind=='badprice':bad['result']['low'][0]=4
            elif kind=='badcost':bad['result']['cost'][0]=-1
            else:bad['testnet']=True
            with self.assertRaises(ValueError):normalize_history('USYC',route,bad,'2026-10-13')
        responses=[json.dumps(x).encode() for x in [meta,payload]]
        class Session:
            def get(self,url,timeout):
                class Response:status_code=200
                obj=Response();obj.content=responses.pop(0);return obj
        with tempfile.TemporaryDirectory() as root:
            out,e=collect_history(Session(),'USYC','hashnote-usyc','2026-10-13',root,now=end)
            self.assertEqual(len(out),200);self.assertEqual(e['hourly_rows'],4800)
            self.assertEqual(e['quote_currency'],'USDC')

    def test_bitget_exact_contract_utc_history_and_quote_turnover(self):
        route=ROUTES['BTW']
        pair={'code':'00000','data':[{'symbol':'BTWUSDT','baseCoin':'BTW','quoteCoin':'USDT','status':'online'}]}
        currency={'code':'00000','data':[{'coin':'BTW','chains':[{'chain':'BEP20','contractAddress':route['contract']}]}]}
        check_identity(route,pair);check_bitget_contract(route,currency)
        wrong=copy.deepcopy(currency);wrong['data'][0]['chains'][0]['contractAddress']='0xwrong'
        with self.assertRaises(ValueError):check_bitget_contract(route,wrong)
        payload={'code':'00000','data':[[int(x[0])*1000,'2','3','1','2','900','42','42'] for x in self.candles()]}
        self.assertEqual(normalize_history('BTW',route,payload,'2026-10-13')[-1]['volume_usd'],42)
        offset=copy.deepcopy(payload)
        for row in offset['data']:row[0]+=57600000
        with self.assertRaises(ValueError):normalize_history('BTW',route,offset,'2026-10-13')
        responses=[json.dumps(x).encode() for x in [pair,currency,payload]]
        urls=[]
        class Session:
            def get(self,url,timeout):
                urls.append(url)
                class Response:status_code=200
                obj=Response();obj.content=responses.pop(0);return obj
        with tempfile.TemporaryDirectory() as root:
            rows,e=collect_history(Session(),'BTW','bitway','2026-10-13',root,now=datetime(2026,10,14,tzinfo=timezone.utc))
            self.assertEqual(len(rows),200)
            self.assertEqual(len(e['currency_identity_sha256']),64)
            self.assertIn('granularity=1Dutc',urls[-1])
        bad=copy.deepcopy(pair);bad['data'][0]['status']='offline'
        with self.assertRaises(ValueError):check_identity(route,bad)

    def test_native_gram_and_case_sensitive_solana_identity(self):
        for symbol in ['GRAM','GRASS']:
            route=ROUTES[symbol]
            meta={'currency':symbol,'name':route['name'],'delisted':False,'trade_disabled':False,'chains':[{'name':route['contract_chain'],'addr':route['contract']}]}
            check_gate_contract(route,meta)
            meta['chains'][0]['addr']='wrong'
            with self.assertRaises(ValueError):check_gate_contract(route,meta)
        route=ROUTES['GRASS']
        meta={'currency':'GRASS','name':route['name'],'delisted':False,'trade_disabled':False,'chains':[{'name':'SOL','addr':route['contract'].lower()}]}
        with self.assertRaises(ValueError):check_gate_contract(route,meta)
        self.assertEqual(ROUTES['GRAM']['coin_id'],'the-open-network')
        self.assertTrue(ROUTES['GRAM']['rename_evidence'].endswith('/100181'))

    def test_gate_currency_provenance_survives_three_response_collection(self):
        from pathlib import Path
        route=ROUTES['AERO']
        pair={'id':route['pair'],'base':'AERO','quote':'USDT','base_name':route['name'],'trade_status':'tradable'}
        currency={'currency':'AERO','name':route['name'],'delisted':False,'trade_disabled':False,'chains':[{'name':route['contract_chain'],'addr':route['contract']}]}
        responses=[json.dumps(x).encode() for x in [pair,currency,self.candles()]]
        class Session:
            def get(self,url,timeout):
                class Response:status_code=200
                obj=Response();obj.content=responses.pop(0);return obj
        with tempfile.TemporaryDirectory() as root:
            rows,e=collect_history(Session(),'AERO',route['coin_id'],'2026-10-13',root,now=datetime(2026,10,14,tzinfo=timezone.utc))
            self.assertEqual(len(rows),200)
            self.assertEqual(json.loads((Path(root)/'AERO/currency.json').read_bytes()),currency)
            self.assertEqual(len(e['currency_identity_sha256']),64)

    def test_raw_identity_and_price_bytes_are_preserved(self):
        meta={"id":"DRV_USDT","base":"DRV","quote":"USDT","base_name":"Derive","trade_status":"tradable"}
        responses=[json.dumps(meta).encode(),json.dumps(self.candles()).encode()]
        class Session:
            def get(self,url,timeout):
                class Response:status_code=200
                obj=Response();obj.content=responses.pop(0);return obj
        with tempfile.TemporaryDirectory()as root:
            rows,e=collect_history(Session(),"DRV","derive","2026-10-13",root,now=datetime(2026,10,14,tzinfo=timezone.utc))
            from pathlib import Path
            self.assertEqual(json.loads((Path(root)/"DRV/identity.json").read_bytes()),meta)
            self.assertEqual(e["closed_rows"],200)
            self.assertEqual(e["historical_scientific_credit"],0)

    def test_unfinished_utc_cutoff_never_fetches(self):
        class Session:
            def get(self,*args,**kwargs):raise AssertionError("must not fetch unfinished day")
        with tempfile.TemporaryDirectory()as root:
            with self.assertRaises(ValueError):
                collect_history(Session(),"DRV","derive","2026-10-13",root,now=datetime(2026,10,13,20,tzinfo=timezone.utc))

    def test_collector_preserves_legacy_attempts_and_records_extension(self):
        import importlib.util,os
        import pandas as pd
        from pathlib import Path
        from unittest.mock import patch
        script=Path(__file__).resolve().parents[1]/"migration/canonical/v2a/scripts/00_run_all_v2a.py"
        spec=importlib.util.spec_from_file_location("qualified_collector_test",script)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        universe=pd.DataFrame([{"symbol":"DRV","id":"derive","standard_ticker":True,"is_stable":False,"is_blocked":False}])
        rows=normalize_history("DRV",ROUTES["DRV"],self.candles(),"2026-10-13")
        with tempfile.TemporaryDirectory()as tmp:
            with patch.dict(os.environ,{"GATE_BTC_DATA_CUTOFF":"2026-10-13"}),patch.object(module,"OUT",Path(tmp)),patch.object(module,"DATA_PROCESSED",Path(tmp)),patch.object(module.time,"sleep"),patch.object(module,"fetch_cdd_symbol",side_effect=RuntimeError("unavailable")),patch.object(module,"fetch_binance_klines",side_effect=RuntimeError("unavailable")),patch.object(module,"fetch_okx_candles",side_effect=RuntimeError("unavailable")),patch("tools.gate_btc_pit150_qualified_history.collect_history",return_value=(rows,{"source":"gate","coin_id":"derive"})):
                master,failures=module.fetch_candles_for_universe(None,universe)
                trace=json.loads((Path(tmp)/"source_attempts_v2a.json").read_text())
        self.assertEqual(set(master.symbol),{"DRV"})
        self.assertEqual(set(failures.symbol),{"BTC","ETH"})
        row=next(x for x in trace["rows"]if x["symbol"]=="DRV")
        self.assertEqual([x["source"]for x in row["attempts"]],["cdd","binance","okx"])
        self.assertEqual(row["selected_source"],"gate")
        self.assertEqual(trace["qualified_extension_selected_count"],1)
        self.assertTrue(trace["source_substitution_performed"])
        from tools.gate_btc_v2a_failure_diagnostic import build_diagnostic
        report=build_diagnostic([{"symbol":"BTC","id":"bitcoin"},{"symbol":"ETH","id":"ethereum"}],failures.to_dict("records"),{"attempted_symbols":3,"loaded_symbols":1,"failed_symbols":2,"qualified_source_extension":1})
        self.assertTrue(report["source_substitution_performed"])
        self.assertEqual(report["qualified_source_extension_selected_count"],1)

if __name__=="__main__":unittest.main()
