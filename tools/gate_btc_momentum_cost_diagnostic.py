#!/usr/bin/env python3
"""Ex-post self-financing cost sensitivity, isolated from canonical gross economics.

Costs are user-supplied hypotheses, not observed fees or a prospective prereg.
All scenarios are reported. No trading, backfill, scientific credit or ledger writes.
"""
import argparse
import hashlib
import json
import math
from datetime import date, timedelta
from pathlib import Path


def rebalance(values, targets, cash, rate):
    """Solve post-cost equal weights including both sold and bought notional."""
    total = sum(values.values()) + cash
    if not targets or len(set(targets)) != len(targets) or not 0 <= rate < 1:
        raise ValueError("INVALID_COST_OR_TARGET_IDENTITY")
    assets = set(values) | set(targets)
    def turnover(nav):
        return sum(abs((nav/len(targets) if a in targets else 0)-values.get(a,0)) for a in assets)
    lo, hi = 0.0, total
    for _ in range(80):
        mid = (lo+hi)/2
        if mid + rate*turnover(mid) > total:
            hi = mid
        else:
            lo = mid
    net = (lo+hi)/2
    traded = turnover(net)
    cost = rate*traded
    if not math.isclose(net+cost,total,rel_tol=1e-12,abs_tol=1e-12):
        raise ValueError("NON_SELF_FINANCING_REBALANCE")
    return net, cost, traded


def prices_for(row, epoch):
    path = epoch / "source_prices" / row["cutoff"] / "MANIFEST.json"
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != row["evidence"]["price_manifest_sha256"]:
        raise ValueError("SEALED_PRICE_MANIFEST_CHANGED")
    manifest = json.loads(raw)
    if manifest.get("cutoff") != row["cutoff"]:
        raise ValueError("MANIFEST_CUTOFF_MISMATCH")
    if manifest.get("available_at_utc") != row["evidence"]["source_available_at_utc"]:
        raise ValueError("MANIFEST_AVAILABILITY_RECEIPT_MISMATCH")
    prices = {}
    for item in manifest["prices"]:
        value = float(item["close_usd"])
        if item["date"] != row["cutoff"] or item["symbol"] in prices or not math.isfinite(value) or value <= 0:
            raise ValueError("INVALID_OR_CONFLICTING_PRICE")
        prices[item["symbol"]] = value
    return prices


def project(ledger, price_rows, one_way_cost_bps):
    if not math.isfinite(one_way_cost_bps) or not 0 <= one_way_cost_bps < 10000:
        raise ValueError("INVALID_ONE_WAY_COST")
    rows = ledger["rows"]
    if not rows or rows[0]["event"] != "ACTIVATION" or len(price_rows) != len(rows):
        raise ValueError("MISSING_ACTIVATION_OR_PRICE_HISTORY")
    names = sorted(rows[0]["holdings_after_close"]) + ["BTC_HOLD"]
    quantities = {n:{} for n in names}
    previous = {n:1.0 for n in names}
    gross_q = None
    result = []
    rate = one_way_cost_bps / 10000
    for i,(row,prices) in enumerate(zip(rows,price_rows)):
        if row["return_observations"] != i or (i and date.fromisoformat(row["cutoff"])-date.fromisoformat(rows[i-1]["cutoff"]) != timedelta(days=1)):
            raise ValueError("NON_CONTIGUOUS_GROSS_HISTORY")
        expected = "ACTIVATION" if i==0 else "REBALANCE" if i%7==0 else "HOLD"
        if row["event"] != expected:
            raise ValueError("FROZEN_REBALANCE_CADENCE_MISMATCH")
        if i:
            for name, q in gross_q.items():
                marked = sum(amount*prices[a] for a,amount in q.items())
                if not math.isclose(marked,row["nav"][name],rel_tol=1e-10,abs_tol=1e-12):
                    raise ValueError("GROSS_PRICE_NAV_RECONCILIATION_FAILED")
        output = {"cutoff":row["cutoff"], "event":row["event"], "portfolios":{}}
        for name in names:
            target = ["BTC"] if name=="BTC_HOLD" else row["holdings_after_close"][name]
            if name!="BTC_HOLD" and len(target)!=10:
                raise ValueError("TOP10_IDENTITY_REQUIRED")
            values = {a:amount*prices[a] for a,amount in quantities[name].items()}
            marked = sum(values.values()) if i else 1.0
            execute = i==0 or (name!="BTC_HOLD" and row["event"]=="REBALANCE")
            if execute:
                nav,cost,traded = rebalance(values,target,1.0 if i==0 else 0.0,rate)
                quantities[name] = {a:nav/len(target)/prices[a] for a in target}
            else:
                nav,cost,traded = marked,0.0,0.0
            output["portfolios"][name] = {"nav_model_net":nav,"daily_return_model_net":nav/previous[name]-1,
                                         "cost_nav_units":cost,"traded_notional_nav_units":traded}
            previous[name] = nav
        gross_q = row["quantities_after_close"]
        result.append(output)
    return {"one_way_cost_bps":one_way_cost_bps, "rows":result,
            "summary":{n:{"nav_model_net":previous[n],"return_model_net":previous[n]-1,
                          "cost_nav_units_total":sum(r["portfolios"][n]["cost_nav_units"] for r in result)} for n in names}}


def build(epoch, grid):
    ledger_path = epoch / "LEDGER.json"
    raw = ledger_path.read_bytes(); ledger = json.loads(raw)
    if ledger.get("epoch_id") != "hold_20260928":
        raise ValueError("UNSUPPORTED_EPOCH_NO_SILENT_ADAPTER")
    prices = [prices_for(row,epoch) for row in ledger["rows"]]
    return {"schema":"gate_btc.momentum_cost_diagnostic.v1", "status":"EX_POST_MODEL_SENSITIVITY_ONLY",
            "source_gross_ledger_sha256":hashlib.sha256(raw).hexdigest(), "epoch_id":ledger["epoch_id"],
            "data_as_of":ledger["rows"][-1]["cutoff"], "source_return_observations":len(ledger["rows"])-1,
            "cost_basis":"INPUT_HYPOTHESIS_FEE_PLUS_SLIPPAGE_PER_BUY_OR_SELL_NOTIONAL_NOT_OBSERVED",
            "activation_cost_included":True,"terminal_liquidation_cost_included":False,
            "funding_and_borrow":"NOT_MODELED_SPOT_UNLEVERED_DIAGNOSTIC_ASSUMPTION_ONLY",
            "fx":"NOT_MODELED_USD_PRICE_NUMERAIRE_NOT_REALIZED_BRL",
            "source_archive_bytes_verified":False,"canonical_gross_history_changed":False,
            "prospective_net_credit":0,"scientific_credit":0,"promotion_authority":False,
            "engine_feed":False,"orders":0,"real_capital":0,
            "scenarios":[project(ledger,prices,float(bps)) for bps in grid]}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--epoch',type=Path,required=True)
    ap.add_argument('--one-way-cost-bps',type=float,nargs='+',required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    # Output must be outside canonical evidence, including its parent/descendants.
    if a.output.resolve().is_relative_to(a.epoch.resolve().parents[1]):
        raise ValueError('DIAGNOSTIC_OUTPUT_CANNOT_OVERWRITE_CANONICAL_EPOCH')
    try:
        result=build(a.epoch,a.one_way_cost_bps)
    except (ValueError,KeyError,OSError) as exc:
        result={'status':'BLOCKED_MISSING_OR_INVALID_BOUND_GROSS_EVIDENCE','reason':str(exc),'scientific_credit':0,'prospective_net_credit':0,'orders':0,'real_capital':0,'engine_feed':False}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='scenarios'}))
    return 0 if result['status']=='EX_POST_MODEL_SENSITIVITY_ONLY' else 2


if __name__=='__main__':
    raise SystemExit(main())
