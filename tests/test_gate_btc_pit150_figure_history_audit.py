import copy
import json
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tools.gate_btc_pit150_figure_history_audit import audit, timestamp_ns

class FigureHistoryAuditTests(unittest.TestCase):
    def fixture(self, root):
        end=datetime(2026,10,14,tzinfo=timezone.utc)
        trades=[{"id":str(i),"price":2,"quantity":3,
                 "created":(end-timedelta(days=i)).strftime("%Y-%m-%dT12:00:00Z")} for i in range(200)]
        meta={"id":"HASH-USD","symbol":"HASH-USD","denom":"HASH","quoteDenom":"USD",
              "marketType":"CRYPTO","status":"OPEN","proTradeAvailable":True,"contractAddress":["nhash"]}
        header={"denom":"HASH","symbol":"HASH-USD","marketId":"HASH-USD"}
        self.write(root/"identity.json",meta)
        self.write(root/"page_000.json",{**header,"matches":trades})
        self.write(root/"page_001.json",{**header,"matches":trades[-1:]})
        self.write(root/"hourly.json",{**header,"matchHistoryData":[
            {"date":t["created"],"open":"2","high":"2","low":"2","close":"2","volume":"3"} for t in trades]})
    def write(self,path,value):
        path.write_text(json.dumps(value),encoding="utf-8")
    def mutate(self,root,name,fn):
        path=root/name;value=json.loads(path.read_text());fn(value);self.write(path,value)
    def test_complete_physical_history_uses_exact_quote_turnover(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root);result=audit(root,"2026-10-14")
            self.assertEqual(result["qualification"],"PASS_SOURCE_CONSISTENCY")
            self.assertEqual(len(result["daily_rows"]),200)
            self.assertEqual(result["daily_rows"][0]["volume_usd"],6)
            self.assertFalse(result["source_admission"])
            self.assertEqual(result["historical_scientific_credit"],0)
    def test_fund_wrapper_or_wrong_quote_is_rejected(self):
        for key,value in [("marketType","FUND"),("quoteDenom","YLDS"),("contractAddress",["wrapper"]),("proTradeAvailable",False)]:
            with tempfile.TemporaryDirectory() as temp:
                root=Path(temp);self.fixture(root)
                self.mutate(root,"identity.json",lambda p:p.update({key:value}))
                with self.assertRaises(ValueError):audit(root,"2026-10-14")
    def test_missing_page_and_unexhausted_page_are_rejected(self):
        for file in ["page_000.json","page_001.json"]:
            with tempfile.TemporaryDirectory() as temp:
                root=Path(temp);self.fixture(root);(root/file).unlink()
                with self.assertRaises(ValueError):audit(root,"2026-10-14")
    def test_immutable_id_conflict_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root)
            self.mutate(root,"page_001.json",lambda p:p["matches"][0].update(price=9))
            with self.assertRaises(ValueError):audit(root,"2026-10-14")
    def test_source_volume_disagreement_blocks_even_with_200_days(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root)
            self.mutate(root,"hourly.json",lambda p:p["matchHistoryData"][0].update(volume="4"))
            result=audit(root,"2026-10-14")
            self.assertEqual(result["unique_days"],200)
            self.assertEqual(result["qualification"],"BLOCKED_SOURCE_CONSISTENCY")
            self.assertEqual(result["cross_endpoint_differences"][0]["field"],"base_volume")
    def test_arbitrary_lexical_trade_id_never_selects_close(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root)
            self.mutate(root,"page_000.json",lambda p:p["matches"].insert(1,{**p["matches"][0],"id":"zzz","price":4}))
            # Keep legal max page size and restore physical second trade at earliest timestamp.
            p=json.loads((root/"page_000.json").read_text());last=p["matches"].pop()
            self.write(root/"page_000.json",p)
            header={k:v for k,v in p.items() if k!="matches"}
            self.write(root/"page_001.json",{**header,"matches":[p["matches"][-1],last]})
            self.mutate(root,"hourly.json",lambda p:p["matchHistoryData"][0].update(high="4",volume="6",close="2"))
            result=audit(root,"2026-10-14")
            self.assertEqual(result["qualification"],"PASS_SOURCE_CONSISTENCY")
            self.assertEqual(result["daily_rows"][-1]["close_usd"],2)
            self.assertEqual(result["daily_rows"][-1]["volume_usd"],18)
    def test_completed_day_and_nanosecond_boundaries(self):
        self.assertEqual(timestamp_ns("2026-10-14T23:59:59.999999999Z")+1,timestamp_ns("2026-10-15T00:00:00Z"))
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root)
            with self.assertRaises(ValueError):
                audit(root,"2026-10-14",now=datetime(2026,10,14,23,tzinfo=timezone.utc))
    def test_real_physical_capture_has_four_unresolved_volume_conflicts(self):
        archive=Path(__file__).resolve().parents[1]/"artifacts/gate_btc_2/pit150_cases_review_20261015/FIGURE_RAW.zip"
        with tempfile.TemporaryDirectory() as temp:
            with zipfile.ZipFile(archive) as z:z.extractall(temp)
            result=audit(Path(temp)/"HASH","2026-10-14")
            self.assertEqual(result["unique_trades"],5673)
            self.assertEqual(result["unique_days"],200)
            self.assertEqual(result["physical_hours"],2340)
            self.assertEqual(len(result["cross_endpoint_differences"]),4)
            self.assertEqual(result["qualification"],"BLOCKED_SOURCE_CONSISTENCY")

if __name__=="__main__":unittest.main()
