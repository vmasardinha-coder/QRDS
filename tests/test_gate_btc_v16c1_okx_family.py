from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path); assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

entry=load("v16c1_entry",Path("tools/gate_btc_v16c1_okx_entry.py"))
result=load("v16c1_result",Path("tools/gate_btc_v16c1_okx_result.py"))
chain=load("v16c1_chain",Path("tools/gate_btc_v16c1_chain.py"))

class V16C1Tests(unittest.TestCase):
    def test_freeze_exists_before_code_and_safety_is_immutable(self):
        p=json.loads((ROOT/"artifacts/gate_btc/v16b/GATE_BTC_V16C1_OKX_FAMILY_FREEZE_20260909.json").read_text())
        self.assertEqual(p["status"],"FROZEN_EX_ANTE")
        self.assertEqual(p["effective_from_first_eligible_signal_date"],"2026-09-17")
        self.assertEqual(p["lineage"]["canonical_cycle_count_starts_at"],0)
        self.assertTrue(p["lineage"]["original_v16c_remains_frozen_and_blocked"])
        self.assertEqual(p["structural_hypothesis_unchanged"]["beta_estimator"],"60-day trailing daily return beta versus BTC using only completed data available by SIGNAL close")
        self.assertTrue(p["safety"]["RESEARCH_ONLY"]); self.assertTrue(p["safety"]["SHADOW_ONLY"])
        self.assertFalse(p["safety"]["ENGINE_FEED"]); self.assertEqual(p["safety"]["ORDERS"],0); self.assertEqual(p["safety"]["REAL_CAPITAL"],0)

    def test_affine_solver_is_deterministic_net_zero_beta_zero_and_strict_signs(self):
        longs=[f"L{i}" for i in range(10)]; shorts=[f"S{i}" for i in range(10)]
        betas={a:0.45+0.10*i for i,a in enumerate(longs)}
        betas.update({a:0.55+0.10*i for i,a in enumerate(shorts)})
        a=entry.solve_beta_neutral(longs,shorts,betas); b=entry.solve_beta_neutral(longs,shorts,betas)
        self.assertEqual(a,b)
        self.assertTrue(all(a[x]>0 for x in longs)); self.assertTrue(all(a[x]<0 for x in shorts))
        self.assertAlmostEqual(sum(a.values()),0.0,places=10)
        self.assertAlmostEqual(sum(abs(v) for v in a.values()),1.0,places=10)
        self.assertLessEqual(abs(sum(a[x]*betas[x] for x in a)),0.05)

    def test_affine_solver_fails_closed_when_beta_constraint_is_infeasible_without_sign_break(self):
        longs=[f"L{i}" for i in range(10)]; shorts=[f"S{i}" for i in range(10)]
        betas={a:5.0+i for i,a in enumerate(longs)}; betas.update({a:0.01+0.001*i for i,a in enumerate(shorts)})
        with self.assertRaisesRegex(ValueError,"strict sign|full rank"):
            entry.solve_beta_neutral(longs,shorts,betas)

    def _daily(self)->pd.DataFrame:
        dates=pd.date_range("2026-06-01","2026-09-17",freq="D")
        rng=np.random.default_rng(20260909)
        btc_r=rng.normal(0.0004,0.012,len(dates))
        rows=[]
        btc_px=100*np.exp(np.cumsum(btc_r))
        for d,p in zip(dates,btc_px): rows.append({"date":d,"symbol":"BTCUSDT","close":p})
        for j in range(20):
            beta=0.55+0.035*j; r=beta*btc_r+rng.normal(0,0.008,len(dates)); px=100*np.exp(np.cumsum(r)); sym=f"A{j}USDT"
            for d,p in zip(dates,px): rows.append({"date":d,"symbol":sym,"close":p})
        return pd.DataFrame(rows)

    def test_future_prices_cannot_change_signal_date_betas(self):
        d=self._daily(); assets=[f"A{i}USDT" for i in range(20)]
        b1=entry._betas(d,assets,"2026-09-10")
        changed=d.copy(); changed.loc[changed["date"]>pd.Timestamp("2026-09-10"),"close"]*=37.0
        b2=entry._betas(changed,assets,"2026-09-10")
        self.assertEqual(b1,b2)

    def test_result_uses_exact_sealed_weights_for_pnl_and_funding(self):
        longs=[f"L{i}" for i in range(10)]; shorts=[f"S{i}" for i in range(10)]
        weights={a:0.04+0.002*i for i,a in enumerate(longs)}
        scale=0.5/sum(weights.values()); weights={a:v*scale for a,v in weights.items()}
        sw={a:-(0.04+0.002*i) for i,a in enumerate(shorts)}; scale2=0.5/sum(abs(v) for v in sw.values()); sw={a:v*scale2 for a,v in sw.items()}; weights.update(sw)
        entry_event={"event_type":"V16C1_ENTRY_SEAL","candidate_id":"GATE_BTC_V16C1_OKX_CORE","status":"OK","signal_date_utc":"2026-09-17","entry_date_utc":"2026-09-18","seal_sha256":"a"*64,"longs_10":longs,"shorts_10":shorts,"weights":weights,"portfolio_beta":0.0,"net_notional":0.0,"gross_exposure":1.0,"turnover_estimate":1.0,"entry_instruments":{**{a:f"BINANCE_SPOT|{a}" for a in longs},**{a:f"OKX_SWAP|{a}-USDT-SWAP" for a in shorts}}}
        ph="b"*64
        prices={"assets":{a:{"instrument":entry_event["entry_instruments"][a],"entry_price":100.0,"exit_price":110.0,"source_hash":ph} for a in longs+shorts}}
        funding={"shorts":{a:{"instrument":entry_event["entry_instruments"][a],"source_hash":"c"*64,"events":[{"funding_time":"2026-09-19T00:00:00Z","realized_rate":0.001,"mark_price":100.0,"mark_price_source_hash":"d"*64}]} for a in shorts}}
        btc={"instrument":"BINANCE_SPOT|BTCUSDT","entry_price":100.0,"exit_price":105.0,"source_hash":"e"*64}
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); pp=td/"p.json"; fp=td/"f.json"; bp=td/"b.json"
            pp.write_text(json.dumps(prices)); fp.write_text(json.dumps(funding)); bp.write_text(json.dumps(btc))
            out=result.build(entry_event,pp,fp,bp,"f"*64)
        by={x["asset"]:x for x in out["per_asset_pnl"]}
        self.assertAlmostEqual(by[longs[0]]["weight"],weights[longs[0]],places=12)
        expected_funding=abs(weights[shorts[0]])/100.0*100.0*0.001
        self.assertAlmostEqual(out["short_funding"][shorts[0]],expected_funding,places=12)

    def test_chain_rejects_result_weight_mutation(self):
        longs=[f"L{i}" for i in range(10)]; shorts=[f"S{i}" for i in range(10)]; holdings=longs+shorts
        weights={a:0.05 for a in longs}; weights.update({a:-0.05 for a in shorts})
        betas={a:1.0 for a in holdings}
        entry_event={"event_type":"V16C1_ENTRY_SEAL","candidate_id":"GATE_BTC_V16C1_OKX_CORE","status":"OK","blocker_reason":None,"signal_date_utc":"2026-09-17","entry_date_utc":"2026-09-18","seal_sha256":"1"*64,"longs_10":longs,"shorts_10":shorts,"weights":weights,"beta60":betas,"portfolio_beta":0.0,"net_notional":0.0,"gross_exposure":1.0,"turnover_estimate":1.0,"entry_instruments":{a:(f"BINANCE_SPOT|{a}" if a in longs else f"OKX_SWAP|{a}") for a in holdings}}
        details=[]
        for a in holdings:
            details.append({"asset":a,"side":"LONG" if a in longs else "SHORT","instrument":entry_event["entry_instruments"][a],"entry_price":100.0,"exit_price":100.0,"raw_return":0.0,"weight":weights[a],"weighted_pnl":0.0,"price_source_hash":"2"*64})
        row={"signal_date_utc":"2026-09-17","entry_date_utc":"2026-09-18","exit_date_utc":"2026-09-25","candidate_id":"GATE_BTC_V16C1_OKX_CORE","entry_seal_sha256":"1"*64,"execution_ledger_hash":"3"*64,"weights":dict(weights),"sealed_portfolio_beta":0.0,"sealed_net_notional":0.0,"sealed_gross_exposure":1.0,"price_source_hashes":{},"per_asset_pnl":details,"transaction_cost":0.0015,"short_funding":{a:0.0 for a in shorts},"funding_evidence_hash":"4"*64,"gross_long_pnl":0.0,"gross_short_pnl":0.0,"net_pnl":-0.0015,"btc_benchmark_return":0.0,"btc_entry_price":100.0,"btc_exit_price":100.0,"btc_source_hash":"5"*64,"source_coverage":{},"status":"OK","blocker_reason":None}
        row["weights"][longs[0]]+=0.001
        with self.assertRaisesRegex(ValueError,"weights differ"):
            chain.validate_result_row(row,entry_event,datetime(2026,9,26,1,tzinfo=timezone.utc))

if __name__=="__main__": unittest.main()
