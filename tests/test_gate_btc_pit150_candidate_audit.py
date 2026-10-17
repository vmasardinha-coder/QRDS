"""Candidate evidence QA must never become an admission or invented physical bar."""
import copy,hashlib,json,unittest
from datetime import datetime,timedelta,timezone
from tools.gate_btc_pit150_candidate_audit import AuditError,audit_grx,audit_native_pool

UTC=timezone.utc
def bar(stamp,vol=1,amount=2):
    return {"id":stamp,"ds":(datetime.fromtimestamp(stamp,UTC)+timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S"),
            "open":2,"high":2,"low":2,"close":2,"vol":vol,"amount":amount}

def fixture():
    start=int(datetime(2026,3,31,tzinfo=UTC).timestamp());end=start+200*86400
    def pages(step,vol,amount,period):
        data=[bar(t,vol,amount) for t in range(start,end,step)]
        chunks=[data[max(0,k-300):k] for k in range(len(data),0,-300)]
        result=[];previous=None
        for chunk in chunks:
            p={"channel":"market_grxusdt_kline_"+period,"pageSize":300}
            if previous is not None:p["endIdx"]=previous-1
            result.append({"request":{"event":"req","params":p},"response":{"event_rep":"rep","channel":p["channel"],"data":chunk}})
            previous=chunk[0]["id"]
        return result
    native={"event_rep":"rep","channel":"market_grxusdt_kline_1day",
            "data":[bar(t,24,48) for t in range(start+16*3600,end-86400,86400)]}
    return {"hourly":pages(3600,1,2,"60min"),"halfhour":pages(1800,.5,1,"30min"),
            "native_day":native,"market":{"code":"0","data":[{"symbol":"grxusdt","base_coin":"GRX","count_coin":"USDT"}]},
            "coin":{"id":"grx-chain","symbol":"GRX","name":"GRX Chain"},
            "identity":{"native_currency":"GRX","chain_id":1110,"source_url":"https://www.grovex.io/grx-chain","source_sha256":"a"*64},
            "cutoff":"2026-10-16","now":datetime(2026,10,17,12,tzinfo=UTC)}

class GrxAuditTests(unittest.TestCase):
    def test_complete_matching_native_evidence_is_candidate_qa_only(self):
        r=audit_grx(**fixture())
        self.assertTrue(r["candidate_qa_pass"])
        self.assertEqual(r["hour_complete_utc_days"],200)
        self.assertFalse(r["production_admission_changed"])
        self.assertFalse(r["source_registered"])
        self.assertEqual(r["historical_scientific_credit"],0)

    def test_one_missing_hour_is_not_filled(self):
        f=fixture();f["hourly"][0]["response"]["data"].pop(-2)
        r=audit_grx(**f)
        self.assertEqual(r["hour_complete_utc_days"],199)
        self.assertEqual(r["missing_hour_bars"],1)
        self.assertFalse(r["candidate_qa_pass"])

    def test_native_quote_turnover_is_not_close_times_base_volume(self):
        f=fixture()
        # Different execution prices may make turnover differ from final close times quantity.
        for p in f["hourly"]:
            for b in p["response"]["data"]:b.update(low=1,high=3,amount=1.5)
        for p in f["halfhour"]:
            for b in p["response"]["data"]:b.update(low=1,high=3,amount=.75)
        for b in f["native_day"]["data"]:b.update(low=1,high=3,amount=36)
        r=audit_grx(**f)
        self.assertTrue(r["candidate_qa_pass"])

    def test_mismatched_native_turnover_is_rejected(self):
        f=fixture();b=f["halfhour"][0]["response"]["data"][-1];b.update(low=1,amount=.75)
        self.assertIn("INTRADAY_RESOLUTIONS_DISAGREE",audit_grx(**f)["blocking_reasons"])

    def test_zero_execution_day_does_not_become_observed_trade_day(self):
        f=fixture();target=int(datetime(2026,10,16,tzinfo=UTC).timestamp())
        for field in ("hourly","halfhour"):
            for p in f[field]:
                for b in p["response"]["data"]:
                    if target<=b["id"]<target+86400:b.update(vol=0,amount=0)
        r=audit_grx(**f)
        self.assertEqual(r["hour_positive_execution_utc_days"],199)
        self.assertFalse(r["candidate_qa_pass"])

    def test_future_completed_cutoff_rejected(self):
        f=fixture();f["now"]=datetime(2026,10,16,23,tzinfo=UTC)
        with self.assertRaises(AuditError):audit_grx(**f)

    def test_wrong_coin_or_wrapped_asset_is_rejected(self):
        for field,change in (("coin",{"id":"greonex"}),("coin",{"symbol":"WGRX"}),("identity",{"native_currency":"WGRX"})):
            f=fixture();f[field].update(change)
            with self.assertRaises(AuditError):audit_grx(**f)

    def test_wrong_market_quote_is_rejected(self):
        f=fixture();f["market"]["data"][0]["count_coin"]="BTC"
        with self.assertRaises(AuditError):audit_grx(**f)

    def test_clock_label_drift_rejected(self):
        f=fixture();f["hourly"][0]["response"]["data"][0]["ds"]="2026-01-01 00:00:00"
        with self.assertRaises(AuditError):audit_grx(**f)

    def test_duplicate_bars_do_not_inflate_history(self):
        f=fixture();p=f["hourly"][0]["response"]["data"];p.insert(0,copy.deepcopy(p[0]))
        with self.assertRaises(AuditError):audit_grx(**f)

    def test_wrong_source_channel_rejected(self):
        f=fixture();f["hourly"][0]["response"]["channel"]="market_safegrxusdt_kline_60min"
        with self.assertRaises(AuditError):audit_grx(**f)

    def test_quote_volume_outside_native_ohlc_rejected(self):
        f=fixture();f["hourly"][0]["response"]["data"][0]["amount"]=100
        with self.assertRaises(AuditError):audit_grx(**f)

    def test_unbacked_native_daily_claim_is_not_sufficient(self):
        f=fixture();f["native_day"]["data"]=[]
        self.assertIn("INSUFFICIENT_NATIVE_DAY_CROSSCHECKS",audit_grx(**f)["blocking_reasons"])

def pool_fixture():
    pool="0x"+"1"*40;tokens=["0x"+"2"*40,"0x"+"3"*40]
    stamp=int(datetime(2026,7,1,tzinfo=UTC).timestamp());raw={};manifest=[]
    def add(name,method,params,value):
        b=(json.dumps({"id":1,"jsonrpc":"2.0","result":value})+"\n").encode()
        raw[name]=b;manifest.append({"file":name,"method":method,"params":params,"sha256":hashlib.sha256(b).hexdigest()})
    add("chain.json","eth_chainId",[],"0xa4b1")
    for n,t in ((99,stamp-1),(100,stamp),(101,stamp+86399),(102,stamp+86400)):
        add(str(n)+".json","eth_getBlockByNumber",[hex(n),False],{"number":hex(n),"timestamp":hex(t)})
    add("logs.json","eth_getLogs",[{"address":pool,"fromBlock":hex(100),"toBlock":hex(101)}],[])
    for i,token in enumerate(tokens):raw["token"+str(i)+".json"]=json.dumps({"id":1,"result":"0x"+"0"*24+token[2:]}).encode()
    result={"chain_id":"0xa4b1","pool":pool,"candidate_only_not_admission":True,"orders":0,"manifest":manifest,
            "days":[{"day":"2026-07-01","first_block":100,"end_block_exclusive":102,"all_native_pool_logs":0}]}
    return {"result":result,"raw":raw,"expected_chain":"0xa4b1","expected_pool":pool,
            "expected_tokens":tokens,"identity_files":["token0.json","token1.json"]}

class NativeGapTests(unittest.TestCase):
    def test_bounded_empty_pool_day_rejects_candidate_without_global_claim(self):
        r=audit_native_pool(**pool_fixture())
        self.assertEqual(r["verified_empty_utc_days"],["2026-07-01"])
        self.assertFalse(r["candidate_qa_pass"])
        self.assertFalse(r["full_200_day_qualification_performed"])
        self.assertFalse(r["global_asset_absence_claim"])

    def test_changed_rpc_bytes_are_rejected(self):
        f=pool_fixture();f["raw"]["logs.json"]=b"{}"
        with self.assertRaises(AuditError):audit_native_pool(**f)

    def test_missing_query_part_is_not_an_empty_day(self):
        f=pool_fixture();f["result"]["manifest"]=[x for x in f["result"]["manifest"] if x["method"]!="eth_getLogs"]
        with self.assertRaises(AuditError):audit_native_pool(**f)

    def test_missing_boundary_header_rejected(self):
        f=pool_fixture();f["result"]["manifest"]=[x for x in f["result"]["manifest"] if x["file"]!="99.json"]
        with self.assertRaises(AuditError):audit_native_pool(**f)

    def test_wrong_chain_or_token_identity_rejected(self):
        for change in ("chain","token"):
            f=pool_fixture()
            if change=="chain":f["expected_chain"]="0x1"
            else:f["expected_tokens"][0]="0x"+"4"*40
            with self.assertRaises(AuditError):audit_native_pool(**f)

if __name__=="__main__":unittest.main()
