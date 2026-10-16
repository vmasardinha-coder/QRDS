import copy,json,tempfile,unittest,zipfile
from datetime import datetime,timezone
from pathlib import Path
from tools import gate_btc_a7a5_swap_history as a
from tools.gate_btc_pit150_qualified_history import route_for_member,collect_history
ROOT=Path(__file__).resolve().parents[1]/"artifacts/gate_btc_2/pit150_a7a5_canonical_swaps_20261016"
def load(name):
    with zipfile.ZipFile(ROOT/"FROZEN_INPUTS.zip") as z:return json.loads(z.read(name))
def response(obj,status=200):
    class Response:pass
    r=Response();r.status_code=status;r.content=json.dumps(obj).encode();return r
class Session:
    def __init__(self):
        self.n=0;self.rpc=load("CANONICAL_CLOSES.json");self.bad=None
    def get(self,url,timeout):
        if "/tokens/" in url:return response(load("TOKEN0.json" if url.endswith(a.BASE) else "TOKEN1.json"))
        obj=load("page_"+str(self.n).zfill(3)+".json");self.n+=1
        if self.bad=="cursor":obj["next_page_params"]={"same":"cursor"}
        return response(obj)
    def post(self,url,json,timeout):
        method=json["method"];params=json["params"]
        if method=="eth_chainId":value="0x2" if self.bad=="chain" else "0x1"
        elif method=="eth_call":value="0x"+"0"*24+(a.BASE if params[0]["data"]=="0x0dfe1681" else a.QUOTE)[2:]
        elif method=="eth_getBlockByNumber":
            value=copy.deepcopy(self.rpc["blocks"][str(int(params[0],16))])
            if self.bad=="block":value["hash"]="0xwrong"
        else:
            value=copy.deepcopy(next(v for v in self.rpc["logs"].values() if v[0]["blockHash"]==params[0]["blockHash"]))
            if self.bad=="logs":value[-1]["data"]="0x"+"0"*256
        return response({"jsonrpc":"2.0","id":1,"result":value})
class SwapHistoryTests(unittest.TestCase):
    def test_prior_admitted_exact_pool_identity_is_bound(self):
        self.assertEqual(a.frozen_pool_identity()["source_symbol"],"eth:"+a.POOL)
        from unittest.mock import patch
        with patch.object(a,"POOL","0xwrong"):
            with self.assertRaisesRegex(ValueError,"FROZEN_A7A5_POOL"):a.frozen_pool_identity()
    def test_physical_200_days_uses_canonical_index_order_and_quote_flow(self):
        rows,last=a.aggregate(load("ALL_EVENTS.json"),"2026-10-14")
        self.assertEqual((len(rows),rows[0]["date"],rows[-1]["date"]),(200,"2026-03-29","2026-10-14"))
        july=next(x for x in rows if x["date"]=="2026-07-10")
        self.assertAlmostEqual(july["volume_usd"],1286.091495)
        self.assertEqual(len(last),200)
        october=next(x for x in rows if x["date"]=="2026-10-13")
        self.assertAlmostEqual(october["close_usd"],0.011541167986648614)
    def test_duplicate_gap_bad_pool_topic_schema_and_amounts_fail(self):
        original=load("ALL_EVENTS.json")
        for kind in ("duplicate","gap","pool","topic","data","flow","timezone"):
            events=copy.deepcopy(original);x=next(x for x in events if x["block_timestamp"].startswith("2026-10-13"))
            if kind=="duplicate":events.append(copy.deepcopy(x))
            if kind=="gap":events=[y for y in events if not y["block_timestamp"].startswith("2026-10-13")]
            if kind=="pool":x["address"]["hash"]="0xwrong"
            if kind=="topic":x["topics"][0]="0xwrong"
            if kind=="data":x["data"]="0xbad"
            if kind=="flow":x["data"]="0x"+"0"*256
            if kind=="timezone":x["block_timestamp"]="2026-10-13T12:00:00+01:00"
            with self.assertRaises(ValueError,msg=kind):a.aggregate(events,"2026-10-14")
    def test_full_physical_replay_verifies_200_canonical_blocks_and_logs(self):
        with tempfile.TemporaryDirectory() as d:
            rows,e=a.collect(Session(),"2026-10-14",d,datetime(2026,10,16,tzinfo=timezone.utc))
            self.assertEqual(len(rows),200);self.assertEqual(e["canonical_closing_blocks_and_logs_verified"],200)
            self.assertEqual(e["historical_scientific_credit"],0);self.assertFalse(e["collector_forward_fill"])
            self.assertGreater(len(e["raw_manifest"]),500)
            self.assertTrue((Path(d)/"A7A5/qualification.json").exists())
    def test_changed_chain_block_or_log_rejected(self):
        for kind in ("chain","block","logs","cursor"):
            s=Session();s.bad=kind
            with tempfile.TemporaryDirectory() as d:
                with self.assertRaises(ValueError,msg=kind):a.collect(s,"2026-10-14",d,datetime(2026,10,16,tzinfo=timezone.utc))
    def test_current_day_is_not_a_completed_cutoff(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"INCOMPLETE_UTC"):a.collect(Session(),"2026-10-16",d,datetime(2026,10,16,tzinfo=timezone.utc))
    def test_future_route_only_no_wrong_coin_or_retroactive_admission(self):
        self.assertIsNone(route_for_member("A7A5","a7a5","2026-10-16"))
        self.assertIsNone(route_for_member("A7A5","other","2026-10-17"))
        self.assertEqual(route_for_member("A7A5","a7a5","2026-10-17")["pool"],a.POOL)
    def test_future_router_delegates_only_to_the_frozen_source(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d,patch.object(a,"collect",return_value=([],{"ok":True})) as collect:
            self.assertEqual(collect_history(Session(),"A7A5","a7a5","2026-10-17",d,datetime(2026,10,18,tzinfo=timezone.utc)),([],{"ok":True}))
            collect.assert_called_once()
if __name__=="__main__":unittest.main()
