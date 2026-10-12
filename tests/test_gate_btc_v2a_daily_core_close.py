import importlib.util,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
SCRIPT=Path(__file__).resolve().parents[1]/"migration/canonical/v2a/scripts/00_run_all_v2a.py"
class DailyCoreCloseTests(unittest.TestCase):
    def load(self):
        spec=importlib.util.spec_from_file_location("v2a_core_close",SCRIPT);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
    def frame(self,symbol,source,end="2025-07-19"):
        return pd.DataFrame({"date":pd.date_range(end=end,periods=200),"symbol":[symbol]*200,"source":[source]*200,"close_usd":[100.0]*200,"volume_usd":[1.0]*200})
    def collect(self,m,tmp):
        universe=pd.DataFrame(columns=["symbol","standard_ticker","is_stable","is_blocked"]).astype({"standard_ticker":bool,"is_stable":bool,"is_blocked":bool})
        with patch.object(m,"OUT",Path(tmp)),patch.object(m,"DATA_PROCESSED",Path(tmp)),patch.object(m.time,"sleep"),patch.dict(os.environ,{"GATE_BTC_DATA_CUTOFF":"2025-07-19"}):
            return m.fetch_candles_for_universe(None,universe)
    def test_stale_long_cdd_history_falls_through_to_existing_binance(self):
        m=self.load()
        with tempfile.TemporaryDirectory() as tmp,patch.object(m,"fetch_cdd_symbol",side_effect=lambda _,s:self.frame(s,"cdd","2025-07-18")),patch.object(m,"fetch_binance_klines",side_effect=lambda _,s:self.frame(s,"binance")),patch.object(m,"fetch_okx_candles",side_effect=AssertionError("must not call OKX")):
            master,failures=self.collect(m,tmp)
            self.assertTrue(failures.empty)
            self.assertEqual(set(master.source),{"binance"})
            trace=json.loads((Path(tmp)/"source_attempts_v2a.json").read_text())
            for row in trace["rows"]:
                self.assertEqual([a["source"] for a in row["attempts"]],["cdd","binance"])
                self.assertEqual(row["attempts"][0]["status"],"ERROR")
                self.assertEqual(row["selected_source"],"binance")
    def test_all_stale_routes_fail_closed_and_preserve_three_attempts(self):
        m=self.load()
        with tempfile.TemporaryDirectory() as tmp,patch.object(m,"fetch_cdd_symbol",side_effect=lambda _,s:self.frame(s,"cdd","2025-07-18")),patch.object(m,"fetch_binance_klines",side_effect=lambda _,s:self.frame(s,"binance","2025-07-18")),patch.object(m,"fetch_okx_candles",side_effect=lambda _,s:self.frame(s,"okx","2025-07-18")):
            master,failures=self.collect(m,tmp)
            self.assertTrue(master.empty);self.assertEqual(len(failures),2)
            trace=json.loads((Path(tmp)/"source_attempts_v2a.json").read_text())
            self.assertTrue(all(len(row["attempts"])==3 and row["selected_source"] is None for row in trace["rows"]))
    def test_duplicate_and_invalid_core_endpoints_rejected(self):
        m=self.load()
        with patch.dict(os.environ,{"GATE_BTC_DATA_CUTOFF":"2025-07-19"}):
            frame=self.frame("BTC","binance")
            for value in (0,float("nan"),float("inf")):
                invalid=frame.copy();invalid.loc[invalid.index[-1],"close_usd"]=value
                with self.assertRaises(RuntimeError):m.validate_daily_core_candidate(invalid,"BTC")
            duplicate=pd.concat([frame,frame.tail(1)])
            with self.assertRaises(RuntimeError):m.validate_daily_core_candidate(duplicate,"BTC")
if __name__=="__main__":unittest.main()
