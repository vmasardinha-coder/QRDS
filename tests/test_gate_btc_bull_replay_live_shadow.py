import csv
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools import gate_btc_bull_replay_live_shadow as live

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "migration" / "reporting" / "bull_replay_contract.json"


def zmake(path, asof, eqdates, delta_dates, cost_day=None):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("outputs/v2a_run_manifest.json", json.dumps({"data_as_of": asof}))
        z.writestr("outputs/delta_v11_run_manifest.json", json.dumps({"data_as_of": asof}))
        prices = [{"date": str(live.d(asof)-live.timedelta(days=i)), "symbol": symbol, "close_usd": "100"} for symbol in ("BTC","ETH") for i in (1,0)]
        price_buf=io.StringIO(); price_writer=csv.DictWriter(price_buf,fieldnames=prices[0]); price_writer.writeheader(); price_writer.writerows(prices)
        z.writestr("data/processed/qos_v2a_master_daily.csv",price_buf.getvalue())
        rows = []
        for strategy in live.REQUIRED_V2A:
            base = 100.0 + len(strategy)
            for i, day in enumerate(eqdates):
                rows.append({"date": day, "strategy": strategy, "equity_brl": base * (1.01 ** i), "drawdown": 0})
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=rows[0])
        writer.writeheader(); writer.writerows(rows)
        z.writestr("outputs/qos_v2a_equity_curves.csv", buf.getvalue())
        trades = []
        if cost_day:
            for strategy in live.REQUIRED_V2A:
                trades.append({"signal_date":"2026-07-31","execution_date":cost_day,"strategy":strategy,"regime":"X","bought":"","sold":"","weights":"{}","traded_notional":"0.2","one_way_turnover":"0.1","cost_fraction":"0.0005"})
        buf = io.StringIO(); fields=["signal_date","execution_date","strategy","regime","bought","sold","weights","traded_notional","one_way_turnover","cost_fraction"]
        writer=csv.DictWriter(buf,fieldnames=fields); writer.writeheader(); writer.writerows(trades)
        z.writestr("outputs/qos_v2a_buy_sell_log.csv",buf.getvalue())
        delta=[]
        for strategy in live.REQUIRED_DELTA:
            equity=1.0
            for i,day in enumerate(delta_dates):
                gross=0.02 if i else 0.0; net=0.015 if i else 0.0; equity*=1+net
                delta.append({"strategy":strategy,"date":day,"gross_return":gross,"trading_cost_return":gross-net,"funding_return":0,"net_return":net,"equity":equity,"turnover":0,"gross_long":0,"gross_short_abs":0,"net_exposure":0,"kill_switch_active":"False"})
        buf=io.StringIO(); writer=csv.DictWriter(buf,fieldnames=delta[0]); writer.writeheader(); writer.writerows(delta)
        z.writestr("outputs/delta_daily_returns.csv",buf.getvalue())


class LiveShadowTests(unittest.TestCase):
    def test_raw_benchmark_closes_fail_closed(self):
        rows=[{"date":day,"symbol":symbol,"close_usd":"100"} for day in ("2026-10-09","2026-10-10") for symbol in ("BTC","ETH")]
        live.validate_core_closes(rows,"2026-10-10")
        for bad in (rows[:-1], rows+[dict(rows[0])], [dict(r,close_usd="nan") for r in rows], [dict(r,close_usd="0") for r in rows]):
            with self.assertRaises(live.LiveShadowError):
                live.validate_core_closes(bad,"2026-10-10")

    def test_missing_core_close_cannot_create_runtime_or_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp); v=tmp/"v.zip"; delta=tmp/"d.zip"; runtime=tmp/"runtime"
            zmake(v,"2026-08-14",["2026-08-13","2026-08-14"],["2026-08-13","2026-08-14"])
            zmake(delta,"2026-08-14",["2026-08-13","2026-08-14"],["2026-08-13","2026-08-14"])
            with zipfile.ZipFile(v) as z: entries={n:z.read(n) for n in z.namelist()}
            entries["data/processed/qos_v2a_master_daily.csv"]=b"date,symbol,close_usd\n2026-08-13,BTC,100\n"
            with zipfile.ZipFile(v,"w") as z:
                for n,raw in entries.items(): z.writestr(n,raw)
            with self.assertRaises(live.LiveShadowError):
                live.process(CONTRACT,v,delta,runtime,"bad")
            self.assertFalse(runtime.exists())

    def test_contract(self):
        self.assertEqual(live.load_contract(CONTRACT)["schema"], "gate_btc.bull_replay_live_shadow.v1")

    def test_anchor_and_first_observation(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp); v2a=tmp/"v2a.zip"; delta=tmp/"delta.zip"; runtime=tmp/"runtime"
            zmake(v2a,"2026-08-13",["2026-08-12","2026-08-13"],["2026-08-13"]); zmake(delta,"2026-08-13",["2026-08-12","2026-08-13"],["2026-08-13"])
            self.assertEqual(live.process(CONTRACT,v2a,delta,runtime,"1")["status"],"ARMED_WAITING_FIRST_RETURN")
            zmake(v2a,"2026-08-14",["2026-08-13","2026-08-14"],["2026-08-13","2026-08-14"],cost_day="2026-08-14"); zmake(delta,"2026-08-14",["2026-08-13","2026-08-14"],["2026-08-13","2026-08-14"],cost_day="2026-08-14")
            result=live.process(CONTRACT,v2a,delta,runtime,"2"); self.assertEqual(result["observed_days"],1)
            with (runtime/"DAILY_LEDGER.csv").open(encoding="utf-8") as handle: rows=list(csv.DictReader(handle))
            self.assertEqual(len(rows),9); self.assertAlmostEqual(float(rows[0]["net_return"]),0.01,10); self.assertGreater(float(rows[0]["gross_return"]),0.01)

    def test_gap_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp); v2a=tmp/"v2a.zip"; delta=tmp/"delta.zip"; runtime=tmp/"runtime"
            zmake(v2a,"2026-08-13",["2026-08-13"],["2026-08-13"]); zmake(delta,"2026-08-13",["2026-08-13"],["2026-08-13"]); live.process(CONTRACT,v2a,delta,runtime,"1")
            zmake(v2a,"2026-08-15",["2026-08-14","2026-08-15"],["2026-08-14","2026-08-15"]); zmake(delta,"2026-08-15",["2026-08-14","2026-08-15"],["2026-08-14","2026-08-15"])
            with self.assertRaises(live.LiveShadowError): live.process(CONTRACT,v2a,delta,runtime,"3")


if __name__ == "__main__": unittest.main()
