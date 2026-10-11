import contextlib,importlib.util,io,json,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
class MEXCCutoffTests(unittest.TestCase):
    def test_provider_future_rows_are_excluded_and_raw_receipt_preserved(self):
        for symbol in ("bgb","bdx","xdc"):
            with self.subTest(symbol=symbol),tempfile.TemporaryDirectory() as tmp:
                path=Path(__file__).resolve().parents[1]/"tools"/f"gate_btc_2_v2a_{symbol}_mexc_qualification_runner.py"
                spec=importlib.util.spec_from_file_location("mexc_"+symbol,path)
                mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
                ts=lambda day:int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp()*1000)
                raw=json.dumps([[ts(day),"1","2","0.5","1.5","3",0,"4"] for day in ("2026-10-09","2026-10-10","2026-10-11")]).encode()
                with patch.object(mod,"request_bytes",return_value=raw),patch("sys.argv",["runner","--end","2026-10-10","--output",tmp]),contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(mod.main(),0)
                summary=json.loads((Path(tmp)/"SUMMARY.json").read_text())
                self.assertEqual(summary["latest_day"],"2026-10-10")
                self.assertEqual(summary["physical_rows_ok"],2)
                self.assertEqual(summary["boundary_rows_excluded"],1)
                self.assertEqual((Path(tmp)/"RAW_000.json").read_bytes(),raw)
                self.assertFalse(summary["engine_feed"])
    def test_future_only_response_fails_closed(self):
        for symbol in ("bgb","bdx","xdc"):
            with self.subTest(symbol=symbol),tempfile.TemporaryDirectory() as tmp:
                path=Path(__file__).resolve().parents[1]/"tools"/f"gate_btc_2_v2a_{symbol}_mexc_qualification_runner.py"
                spec=importlib.util.spec_from_file_location("mexc_"+symbol,path)
                mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
                raw=json.dumps([[1791676800000,"1","2","0.5","1.5","3",0,"4"]]).encode()
                with patch.object(mod,"request_bytes",return_value=raw),patch("sys.argv",["runner","--end","2026-10-10","--output",tmp]),contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(mod.main(),2)
                summary=json.loads((Path(tmp)/"SUMMARY.json").read_text())
                self.assertFalse(summary["qa_pass"])
                self.assertEqual(summary["physical_rows_ok"],0)
if __name__=="__main__":unittest.main()
