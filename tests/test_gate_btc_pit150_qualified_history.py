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
        self.assertEqual(len(ROUTES),32)
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
        self.assertIsNone(route_for_member('USDY','ondo-us-dollar-yield','2026-10-14'))
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
        for symbol in ['AERO','SPX','CRVUSD']:
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

    def test_usdy_bybit_prospective_cutoff_identity_and_physical_qa(self):
        route=ROUTES["USDY"]
        self.assertIsNotNone(route_for_member("USDY",route["coin_id"],"2026-10-15"))
        self.assertIsNone(route_for_member("USDY","another-token","2026-10-15"))
        self.assertIsNone(route_for_member("USDY",route["coin_id"],"2026-10-14"))
        meta={"retCode":0,"result":{"category":"spot","list":[{"symbol":"USDYUSDT","symbolId":555,"baseCoin":"USDY","quoteCoin":"USDT","status":"Trading"}]}}
        check_identity(route,meta)
        for key,value in [("symbolId",556),("baseCoin","OTHER"),("quoteCoin","USDC"),("status","Closed")]:
            bad=copy.deepcopy(meta);bad["result"]["list"][0][key]=value
            with self.assertRaises(ValueError):check_identity(route,bad)
        last=datetime(2026,10,15,tzinfo=timezone.utc)
        bars=[[str(int((last-timedelta(days=i)).timestamp()*1000)),"2","3","1","2","900","42"] for i in range(200)]
        payload={"retCode":0,"result":{"category":"spot","symbol":"USDYUSDT","list":bars}}
        rows=normalize_history("USDY",route,payload,"2026-10-15")
        self.assertEqual(rows[-1]["volume_usd"],42)
        self.assertEqual(len(rows),200)
        for kind in ["short","duplicate","gap","wrong_market","wrong_pair","transport","offset","negative_turnover","bad_price"]:
            bad=copy.deepcopy(payload)
            if kind=="short":bad["result"]["list"].pop()
            elif kind=="duplicate":bad["result"]["list"].append(bars[0])
            elif kind=="gap":bad["result"]["list"][50][0]=str(int(bars[-1][0])-86400000)
            elif kind=="wrong_market":bad["result"]["category"]="linear"
            elif kind=="wrong_pair":bad["result"]["symbol"]="OTHERUSDT"
            elif kind=="transport":bad["retCode"]=10001
            elif kind=="offset":bad["result"]["list"][0][0]=str(int(bars[0][0])+1)
            elif kind=="negative_turnover":bad["result"]["list"][0][6]="-1"
            else:bad["result"]["list"][0][3]="5"
            with self.assertRaises(ValueError):normalize_history("USDY",route,bad,"2026-10-15")
        responses=[json.dumps(x).encode() for x in [meta,payload]]
        class Session:
            def get(self,url,timeout):
                class Response:status_code=200
                obj=Response();obj.content=responses.pop(0);return obj
        with tempfile.TemporaryDirectory() as root:
            rows,e=collect_history(Session(),"USDY",route["coin_id"],"2026-10-15",root,now=datetime(2026,10,16,tzinfo=timezone.utc))
            self.assertEqual(e["effective_cutoff"],"2026-10-15")
            self.assertEqual(e["volume_field"],"turnover")
            self.assertEqual(len(rows),200)

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


class QualifiedEpochTraceTests(unittest.TestCase):
    def test_future_epoch_is_distinct_from_wrong_coin_identity(self):
        import importlib.util,os,pandas as pd
        from pathlib import Path
        from unittest.mock import patch
        script=Path(__file__).resolve().parents[1]/"migration/canonical/v2a/scripts/00_run_all_v2a.py"
        spec=importlib.util.spec_from_file_location("epoch_collector_test",script)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        for wrong in (False,True):
            universe=pd.DataFrame([{"symbol":symbol,"id":"wrong" if wrong else ROUTES[symbol]["coin_id"],
                "standard_ticker":True,"is_stable":False,"is_blocked":False} for symbol in ("HASH","A7A5","REUSD")])
            with self.subTest(wrong_identity=wrong),tempfile.TemporaryDirectory() as tmp:
                with patch.dict(os.environ,{"GATE_BTC_DATA_CUTOFF":"2026-10-16"}),patch.object(module,"OUT",Path(tmp)),patch.object(module,"DATA_PROCESSED",Path(tmp)),patch.object(module.time,"sleep"),patch.object(module,"fetch_cdd_symbol",side_effect=RuntimeError("unavailable")),patch.object(module,"fetch_binance_klines",side_effect=RuntimeError("unavailable")),patch.object(module,"fetch_okx_candles",side_effect=RuntimeError("unavailable")):
                    master,failures=module.fetch_candles_for_universe(None,universe)
                trace=json.loads((Path(tmp)/"source_attempts_v2a.json").read_bytes())
            self.assertEqual(trace["qualified_extension_selected_count"],0)
            for row in trace["rows"]:
                if row["symbol"] not in ("HASH","A7A5","REUSD"):continue
                attempt=row["qualified_extension_attempt"]
                if wrong:
                    self.assertEqual(attempt["status"],"ERROR")
                    self.assertIn("coin_id",attempt["message"])
                else:
                    self.assertEqual(attempt["status"],"NOT_EFFECTIVE")
                    self.assertEqual(attempt["effective_cutoff"],"2026-10-17")


class BybitOfficialHostTests(unittest.TestCase):
    def data(self):
        meta={"retCode":0,"result":{"category":"spot","list":[{"symbol":"USDYUSDT","symbolId":555,"baseCoin":"USDY","quoteCoin":"USDT","status":"Trading"}]}}
        last=datetime(2026,10,15,tzinfo=timezone.utc)
        bars=[[str(int((last-timedelta(days=i)).timestamp()*1000)),"2","3","1","2","900","42"] for i in range(200)]
        return meta,{"retCode":0,"result":{"category":"spot","symbol":"USDYUSDT","list":bars}}

    def session(self, responses):
        class Session:
            def __init__(self):self.urls=[]
            def get(self,url,timeout):
                self.urls.append(url)
                status,payload=responses[len(self.urls)-1]
                class Response:pass
                r=Response();r.status_code=status;r.content=json.dumps(payload).encode();return r
        return Session()

    def collect(self,session,root):
        return collect_history(session,"USDY","ondo-us-dollar-yield","2026-10-15",root,
                               now=datetime(2026,10,16,tzinfo=timezone.utc))

    def test_identity_403_uses_only_official_secondary_host(self):
        meta,bars=self.data();s=self.session([(403,{}),(200,meta),(200,bars)])
        with tempfile.TemporaryDirectory() as root:
            rows,e=self.collect(s,root)
            self.assertEqual(len(rows),200)
            self.assertEqual(e["public_api_host"],"https://api.bytick.com")
            self.assertFalse(e["cross_host_payload_mixing"])
            self.assertTrue(all(u.startswith("https://api.bytick.com/") for u in s.urls[1:]))

    def test_candle_403_repeats_identity_on_secondary_host(self):
        meta,bars=self.data();s=self.session([(200,meta),(403,{}),(200,meta),(200,bars)])
        with tempfile.TemporaryDirectory() as root:
            rows,e=self.collect(s,root)
            self.assertEqual(len(rows),200)
            self.assertEqual(len(s.urls),4)
            self.assertIn("instruments-info",s.urls[2])
            self.assertEqual(e["historical_scientific_credit"],0)

    def test_wrong_identity_is_not_hidden_by_host_retry(self):
        meta,bars=self.data();meta["result"]["list"][0]["baseCoin"]="OTHER"
        s=self.session([(200,meta),(200,bars)])
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):self.collect(s,root)
        self.assertEqual(len(s.urls),1)

    def test_both_hosts_blocked_never_qualify(self):
        from pathlib import Path
        s=self.session([(403,{}),(403,{})])
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError,"public hosts unavailable"):self.collect(s,root)
            self.assertFalse((Path(root)/"USDY/qualification.json").exists())
        self.assertEqual(len(s.urls),2)

    def test_secondary_short_history_is_still_refused(self):
        meta,bars=self.data();bars["result"]["list"].pop()
        s=self.session([(403,{}),(200,meta),(200,bars)])
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):self.collect(s,root)



class BybitPublicCaptureTests(unittest.TestCase):
    def fixture(self,cutoff="2026-10-15"):
        import hashlib
        meta,bars=BybitOfficialHostTests().data()
        if cutoff=="2026-10-16":
            for b in bars["result"]["list"]:b[0]=str(int(b[0])+86400000)
        raw={k:json.dumps(v).encode() for k,v in {"identity":meta,"candles":bars}.items()}
        day=(datetime.strptime(cutoff,"%Y-%m-%d")+timedelta(days=1)).date().isoformat()
        seal={"schema":"gate_btc.bybit_public_capture.v1","symbol":"USDY","coin_id":"ondo-us-dollar-yield",
              "pair":"USDYUSDT","cutoff":cutoff,"public_api_host":"https://api.bybit.com",
              "fetched_at_utc":day+"T11:00:00+00:00","orders":0,"real_capital":0,
              "sha256":{k+".json":hashlib.sha256(v).hexdigest() for k,v in raw.items()}}
        head=[{"sha":"a"*40,"commit":{"committer":{"date":day+"T12:00:00Z"}}}]
        return raw,seal,head

    def session(self,raw,seal,head,block_official=False):
        class Session:
            def __init__(self):self.urls=[]
            def get(self,url,timeout):
                self.urls.append(url)
                class Response:pass
                r=Response();r.status_code=200
                if url.startswith(("https://api.bybit.com/","https://api.bytick.com/")) and block_official:
                    r.status_code=403;r.content=b"blocked";return r
                if "api.github.com" in url:r.content=json.dumps(head).encode()
                elif url.endswith("/seal.json"):r.content=json.dumps(seal).encode()
                elif url.endswith("/identity.json"):r.content=raw["identity"]
                elif url.endswith("/candles.json"):r.content=raw["candles"]
                else:raise AssertionError(url)
                return r
        return Session()

    def test_public_capture_hashes_qa_and_pinned_revision(self):
        from tools.gate_btc_pit150_qualified_history import load_bybit_public_capture
        raw,seal,head=self.fixture();s=self.session(raw,seal,head)
        with tempfile.TemporaryDirectory() as root:
            rows,e=load_bybit_public_capture(s,ROUTES["USDY"],"USDY","2026-10-15",root,
                                            now=datetime(2026,10,16,13,tzinfo=timezone.utc))
        self.assertEqual(len(rows),200)
        self.assertEqual(e["capture_revision"],"a"*40)
        self.assertEqual(e["historical_scientific_credit"],0)
        self.assertTrue(all("/"+("a"*40)+"/" in url for url in s.urls[1:]))

    def test_corrupt_identity_wrong_day_future_and_backdated_seals_fail(self):
        from tools.gate_btc_pit150_qualified_history import load_bybit_public_capture
        for kind in ["hash","coin","cutoff","future_fetch","early_publication","unapproved_host"]:
            raw,seal,head=self.fixture()
            if kind=="hash":raw["candles"]+=b" "
            elif kind=="coin":seal["coin_id"]="other"
            elif kind=="cutoff":seal["cutoff"]="2026-10-14"
            elif kind=="future_fetch":seal["fetched_at_utc"]="2026-10-17T00:00:00Z"
            elif kind=="early_publication":head[0]["commit"]["committer"]["date"]="2026-10-15T23:59:00Z"
            else:seal["public_api_host"]="https://untrusted.example"
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as root:
                with self.assertRaises(ValueError):
                    load_bybit_public_capture(self.session(raw,seal,head),ROUTES["USDY"],"USDY","2026-10-15",root,
                                              now=datetime(2026,10,16,13,tzinfo=timezone.utc))

    def test_production_fallback_activates_only_future_cutoff(self):
        raw,seal,head=self.fixture("2026-10-16")
        s=self.session(raw,seal,head,block_official=True)
        with tempfile.TemporaryDirectory() as root:
            rows,e=collect_history(s,"USDY","ondo-us-dollar-yield","2026-10-16",root,
                                   now=datetime(2026,10,17,13,tzinfo=timezone.utc))
        self.assertEqual(len(rows),200)
        self.assertEqual(rows[-1]["date"],"2026-10-16")
        self.assertEqual(e["delivery"],"PUBLIC_EXCHANGE_CAPTURE_PINNED_GITHUB_COMMIT")


class BybitReadTokenTests(unittest.TestCase):
    def test_read_token_is_sent_only_to_github_api(self):
        import os
        from unittest.mock import patch
        from tools.gate_btc_pit150_qualified_history import load_bybit_public_capture
        raw,seal,head=BybitPublicCaptureTests().fixture()
        public=BybitPublicCaptureTests().session(raw,seal,head)
        calls=[]
        class Session:
            def get(self,url,timeout,**kwargs):
                calls.append((url,kwargs))
                if "api.github.com" not in url:
                    if kwargs:raise AssertionError("credential leaked to payload host")
                return public.get(url,timeout)
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,{"GATE_BTC_PUBLIC_CAPTURE_READ_TOKEN":"test-read-token"}):
            rows,e=load_bybit_public_capture(Session(),ROUTES["USDY"],"USDY","2026-10-15",root,
                now=datetime(2026,10,16,13,tzinfo=timezone.utc))
            for path in __import__("pathlib").Path(root).rglob("*"):
                if path.is_file():self.assertNotIn(b"test-read-token",path.read_bytes())
        self.assertEqual(calls[0][1]["headers"]["Authorization"],"Bearer test-read-token")
        self.assertTrue(all(not kwargs for url,kwargs in calls[1:]))
        self.assertEqual(len(rows),200)



class BybitCapturePublisherTests(unittest.TestCase):
    def test_existing_day_is_never_recollected(self):
        from tools import gate_btc_pit150_usdy_capture as producer
        from unittest.mock import patch
        import sys
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(sys,"argv",["capture","--root",tmp,"--cutoff","2026-10-15"]), \
                 patch.object(producer,"github",return_value={"sha":"b"*40}), \
                 patch.object(producer,"collect_history",side_effect=AssertionError("must not recollect")):
                producer.main()

    def test_publish_uses_server_timestamp_and_nonforce_ref(self):
        from tools import gate_btc_pit150_usdy_capture as producer
        from unittest.mock import patch
        calls=[];answers=iter([{"object":{"sha":"a"*40}},{"tree":{"sha":"b"*40}},
                               {"sha":"c"*40},{"sha":"d"*40,"committer":{"date":"2026-10-16T12:00:00Z"}},{}])
        def api(gh,path,method="GET",payload=None):
            calls.append((path,method,payload));return next(answers)
        with patch.object(producer,"github",side_effect=api):
            producer.publish("gh","2026-10-15",{"seal.json":b"{}","identity.json":b"{}","candles.json":b"{}"})
        commit=calls[3][2]
        self.assertNotIn("author",commit);self.assertNotIn("committer",commit)
        self.assertEqual(calls[-1][2],{"sha":"d"*40,"force":False})
        self.assertTrue(all(x["path"].startswith("captures/2026-10-15/") for x in calls[2][2]["tree"]))


if __name__=="__main__":unittest.main()



class AeroProviderNameAmendmentTests(unittest.TestCase):
    def market(self):
        return {"id": "AERO_USDT", "base": "AERO", "quote": "USDT",
                "base_name": "Aero", "trade_status": "tradable"}

    def currency(self):
        return {"currency": "AERO", "name": "Aero", "delisted": False,
                "trade_disabled": False, "chain": "BASEEVM",
                "chains": [{"name": "BASEEVM", "addr": ROUTES["AERO"]["contract"]}]}

    def test_amendment_is_future_cutoff_only_and_does_not_mutate_route(self):
        before = copy.deepcopy(ROUTES["AERO"])
        old = route_for_member("AERO", "aerodrome-finance", "2026-10-26")
        new = route_for_member("AERO", "aerodrome-finance", "2026-10-27")
        self.assertEqual(old["name"], "Aerodrome")
        with self.assertRaises(ValueError):
            check_identity(old, self.market())
        check_identity(new, self.market())
        check_gate_contract(new, self.currency())
        self.assertEqual(new["contract"], old["contract"])
        self.assertEqual(ROUTES["AERO"], before)
        self.assertIsNone(route_for_member("AERO", "another-token", "2026-10-27"))

    def test_new_display_name_cannot_bypass_chain_contract_or_currency(self):
        route = route_for_member("AERO", "aerodrome-finance", "2026-10-27")
        for kind in ["chain", "contract", "duplicate", "currency", "disabled"]:
            bad = self.currency()
            if kind == "chain": bad["chains"][0]["name"] = "ETH"
            if kind == "contract": bad["chains"][0]["addr"] = "0xwrong"
            if kind == "duplicate": bad["chains"].append(dict(bad["chains"][0]))
            if kind == "currency": bad["currency"] = "OTHER"
            if kind == "disabled": bad["trade_disabled"] = True
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                check_gate_contract(route, bad)

    def test_other_gate_names_are_not_relaxed(self):
        route = dict(ROUTES["AERO"], pair="OTHER_USDT", name="Original")
        with self.assertRaises(ValueError):
            check_identity(route, dict(self.market(), id="OTHER_USDT", base="OTHER"))
