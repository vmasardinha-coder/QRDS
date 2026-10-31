import copy,json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
import numpy as np
import pandas as pd
from tools import gate_btc_v16_research_shadow as s
from tools import gate_btc_v16_research_live as live


class ShadowTests(unittest.TestCase):
    def sample(self):
        rng=np.random.default_rng(713)
        days=pd.date_range("2024-11-01",periods=730)
        return pd.concat([pd.DataFrame({"date":days,"symbol":symbol,
            "close":100*np.exp(np.cumsum(rng.normal(.0001,.025,len(days)))),
            "volume_usd":100000000.}) for symbol in ["BTCUSDT"]+[f"A{i}USDT" for i in range(24)]],ignore_index=True)

    def test_feature_arithmetic_matches_frozen_v16_builder(self):
        from tools import gate_btc_v16b_feature_panel as original
        daily=self.sample();day="2026-10-20";symbols=sorted(daily.symbol.unique())
        actual=s.feature_panel(daily,[day],symbols)
        with tempfile.TemporaryDirectory() as d:
            dp=Path(d)/"daily.csv";up=Path(d)/"universe.csv";daily.to_csv(dp,index=False)
            pd.DataFrame([{"signal_date":day,"symbol":x,
                "evidence_class":original.HISTORICAL_MODEL_ONLY,
                "snapshot_effective_date":day,"retrieved_at_utc":"2026-10-31T00:00:00Z",
                "source_ref":"SYNTHETIC_UNIT_FIXTURE_ONLY","snapshot_sha256":"a"*64} for x in symbols]).to_csv(up,index=False)
            expected,_=original.build_panel(dp,up)
        np.testing.assert_allclose(actual[s.FEATURES].to_numpy(),expected[s.FEATURES].to_numpy(),rtol=1e-10,atol=1e-10)

    def test_historical_seed_can_train_without_prospective_week_credit(self):
        daily=self.sample();dates=pd.date_range("2025-04-03","2026-10-22",freq="W-THU")
        panel=s.feature_panel(daily,dates,sorted(daily.symbol.unique()))
        current=s.feature_panel(daily,["2026-10-29"],sorted(daily.symbol.unique()))
        out=s.rank(pd.concat([panel,current],ignore_index=True),"2026-10-29","2026-10-29",[])
        self.assertGreaterEqual(out["qualified_training_weeks"],52)
        self.assertEqual(out["canonical_credit"],0)
        self.assertEqual(out["exposure"],1.)
        self.assertEqual(len(out["long_ranking"]),25)

    def entry(self):
        p=dict(entry_date="2026-11-06",exit_date="2026-11-13",exposure=1.,
               weights={"B|AAAUSDT":.5,"O|BBB-USDT-SWAP":-.5})
        prices={"B|AAAUSDT":100.,"O|BBB-USDT-SWAP":100.,"B|BTCUSDT":100.}
        return s.mark(s.initial_state(),"2026-11-06",prices,0.,p)

    def test_first_window_and_no_inherited_observations(self):
        self.assertEqual(s.first_signal("2026-10-31"),"2026-11-05")
        self.assertEqual(s.initial_state()["observations"],0)
        self.assertNotIn("v16b1",s.ROOT)

    def test_entry_cost_is_self_financed_and_not_a_fake_daily_return(self):
        state,row=self.entry()
        self.assertAlmostEqual(state["nav"],1/1.0015,12)
        self.assertAlmostEqual(row["cost"],1-state["nav"],12)
        self.assertEqual(state["observations"],0)
        self.assertFalse(row["eligible_daily_observation"])
        self.assertAlmostEqual(sum(abs(p["quantity"]*p["entry_price"]) for p in state["positions"].values()),state["nav"])

    def test_independent_long_short_and_benchmark_accounting(self):
        old,_=self.entry();e=old["nav"]
        new,row=s.mark(old,"2026-11-07",{"B|AAAUSDT":110.,"O|BBB-USDT-SWAP":90.,"B|BTCUSDT":110.},.002)
        self.assertAlmostEqual(row["price_pnl"],e*.1)
        self.assertAlmostEqual(new["nav"],e*1.1+.002)
        self.assertAlmostEqual(row["btc_return"],.1)
        self.assertAlmostEqual(row["excess_vs_btc_pp"],(e*1.1+.002-1.1)*100)
        self.assertEqual(new["observations"],1)

    def test_multiday_mark_does_not_manufacture_daily_sample(self):
        old,_=self.entry()
        new,row=s.mark(old,"2026-11-09",{"B|AAAUSDT":100.,"O|BBB-USDT-SWAP":100.,"B|BTCUSDT":100.},0.)
        self.assertEqual(row["interval_days"],3);self.assertEqual(new["observations"],0)

    def test_unchanged_rebalance_has_no_round_trip_fee(self):
        equity,qty,cost=s.rebalance(1.,{"x":.005,"y":-.005},{"x":.5,"y":-.5},{"x":100.,"y":100.})
        self.assertAlmostEqual(cost,0.);self.assertEqual(equity,1.)
        self.assertEqual(qty,{"x":.005,"y":-.005})

    def test_exit_closes_quantity_and_measures_one_week_not_seven_samples(self):
        old,_=self.entry();e=old["nav"]
        new,row=s.mark(old,"2026-11-13",{"B|AAAUSDT":120.,"O|BBB-USDT-SWAP":80.,"B|BTCUSDT":100.},0.)
        self.assertFalse(new["positions"]);self.assertEqual(new["observations"],0)
        self.assertEqual(len(new["closed_cycles"]),1)
        self.assertAlmostEqual(new["closed_cycles"][0]["unscaled_gross_return"],.2)
        self.assertAlmostEqual(row["cost"],.0015*e)

    def test_rejections_leave_input_unchanged(self):
        old,_=self.entry();saved=copy.deepcopy(old)
        for day,prices,fund in [("2026-11-06",{},0.),("2026-11-07",{},0.),
                               ("2026-11-07",{"B|AAAUSDT":100.,"O|BBB-USDT-SWAP":100.},float("nan"))]:
            with self.assertRaises((ValueError,KeyError)):s.mark(old,day,prices,fund)
            self.assertEqual(old,saved)

    def test_hash_chain_detects_restatement(self):
        with tempfile.TemporaryDirectory() as d:
            state,row=self.entry();s.append_event(d,state,row,[])
            self.assertEqual(len(s.load_events(d)),1)
            p=Path(d)/"EVENTS.jsonl";x=json.loads(p.read_text());x["row"]["nav"]=999
            p.write_text(json.dumps(x)+"\n")
            with self.assertRaises(ValueError):s.load_events(d)

    def test_training_counts_qualified_mature_weeks_not_calendar_dates(self):
        cols=["signal_date","symbol","feature_ok","fwd_ret"]+s.FEATURES
        with self.assertRaisesRegex(ValueError,"52 qualified"):
            s.rank(pd.DataFrame(columns=cols),"2026-11-05","2026-11-05",[])

    def test_live_identity_mapping_rejects_alias_and_duplicate_symbols(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"cmc.json";p.write_text(json.dumps({"data":[
                {"id":1,"symbol":"BTC","slug":"bitcoin","rank":1},
                {"id":2,"symbol":"SYC","slug":"s","rank":2},
                {"id":3,"symbol":"DUP","slug":"d1","rank":3},
                {"id":4,"symbol":"DUP","slug":"d2","rank":4}]}))
            rows=[{"symbol":x+"USDT","baseAsset":x,"quoteAsset":"USDT","status":"TRADING"} for x in ["BTC","SYCOIN","DUP"]]
            mapped,excluded=live.mapping(p,{"symbols":rows})
            self.assertEqual(set(mapped),{"BTCUSDT"});self.assertEqual(len(excluded),3)

    def test_no_economic_nav_is_reported_before_entry(self):
        with tempfile.TemporaryDirectory() as d:
            s.render(d,{"status":"ARMED_WAIT_FIRST_FUTURE_SIGNAL","nav":None})
            self.assertIn('"nav": null',(Path(d)/"STATUS.json").read_text())
            self.assertIn("sem crédito",(Path(d)/"REPORT.html").read_text())

    def test_official_funding_sign_quantity_and_settlement_mark(self):
        with tempfile.TemporaryDirectory() as d:
            c=live.Public(d)
            def get(host,path,**kw):
                if "funding-rate" in path:return {"data":[{"fundingTime":"2000","realizedRate":".001"},{"fundingTime":"1000","realizedRate":".9"}]}
                return {"data":[["2000","110","110","110","110","1"]]}
            c.get=get
            self.assertAlmostEqual(c.funding("O|AAA-USDT-SWAP",1000,2000,-10),1.1)

    def test_missing_funding_is_not_assumed_zero(self):
        with tempfile.TemporaryDirectory() as d:
            c=live.Public(d);c.get=lambda *a,**k:{"data":[]}
            with self.assertRaisesRegex(ValueError,"coverage missing"):c.funding("O|AAA-USDT-SWAP",1000,2000,-10)


if __name__=="__main__":unittest.main()
