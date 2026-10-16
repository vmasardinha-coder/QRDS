#!/usr/bin/env python3
"""Ex-post self-financing cost sensitivity, isolated from canonical gross economics.

Costs are user-supplied hypotheses, not observed fees or a prospective prereg.
All scenarios are reported. No trading, backfill, scientific credit or ledger writes.
"""
import argparse
import csv
import gzip
import io
import zipfile
import hashlib
import json
import math
from datetime import date, datetime, timedelta
from pathlib import Path


def rebalance(values, targets, cash, rate):
    """Solve post-cost equal weights including both sold and bought notional."""
    if (not math.isfinite(cash) or cash < 0
            or any(not math.isfinite(v) or v < 0 for v in values.values())):
        raise ValueError("INVALID_SPOT_HOLDINGS_OR_CASH")
    total = sum(values.values()) + cash
    if total <= 0:
        raise ValueError("NONPOSITIVE_PORTFOLIO_VALUE")
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
    # Bind the manifest to both retained source archives and the exact CSV used
    # by the gross engine. A manifest hash alone cannot prove archive integrity.
    for name,key in [("required_prices.zip","prices_zip_sha256"),
                     ("RAW_SOURCES.json.gz","raw_archive_sha256")]:
        if hashlib.sha256((path.parent/name).read_bytes()).hexdigest() != manifest[key]:
            raise ValueError("SOURCE_ARCHIVE_CORRUPT")
    archive = json.loads(gzip.decompress((path.parent/"RAW_SOURCES.json.gz").read_bytes()))
    records = archive.get("sources", [])
    if not records or not any(r.get("http_status") == 200 for r in records):
        raise ValueError("MISSING_PHYSICAL_SOURCE_RESPONSES")
    for record in records:
        if hashlib.sha256(record["raw_utf8"].encode()).hexdigest() != record["raw_sha256"]:
            raise ValueError("RAW_SOURCE_RESPONSE_CHANGED")
    prices = {}
    for item in manifest["prices"]:
        value = float(item["close_usd"])
        if item["date"] != row["cutoff"] or item["symbol"] in prices or not math.isfinite(value) or value <= 0:
            raise ValueError("INVALID_OR_CONFLICTING_PRICE")
        prices[item["symbol"]] = value
    if (sorted(prices) != manifest["required_assets"]
            or manifest["price_count"] != len(prices)):
        raise ValueError("MANIFEST_ASSET_COVERAGE_MISMATCH")
    with zipfile.ZipFile(path.parent/"required_prices.zip") as source:
        expected = "data/processed/qos_v2a_master_daily.csv"
        if source.namelist() != [expected]:
            raise ValueError("AMBIGUOUS_PRICE_ARCHIVE")
        csv_rows = list(csv.DictReader(io.StringIO(source.read(expected).decode("utf-8-sig"))))
    csv_prices = {}
    manifest_sources = {r["symbol"]:r["source"] for r in manifest["prices"]}
    for item in csv_rows:
        symbol = item["symbol"]
        if (symbol in csv_prices or item["date"] != row["cutoff"]
                or item["source"] != manifest_sources.get(symbol)):
            raise ValueError("PRICE_ARCHIVE_IDENTITY_MISMATCH")
        csv_prices[symbol] = float(item["close_usd"])
    if csv_prices != prices:
        raise ValueError("PRICE_ARCHIVE_MANIFEST_DISAGREEMENT")
    return prices


def verify_gross_row(row, prices, previous_q, initial_btc_price, expected_names):
    if set(row["holdings_after_close"]) != set(expected_names) or set(row["nav"]) != set(expected_names):
        raise ValueError("GROSS_STRATEGY_IDENTITY_CHANGED")
    for name in expected_names:
        target = row["holdings_after_close"][name]
        quantities = row["quantities_after_close"][name]
        if len(target) != 10 or len(set(target)) != 10 or set(quantities) != set(target):
            raise ValueError("GROSS_QUANTITY_IDENTITY_MISMATCH")
        if any(not math.isfinite(q) or q <= 0 for q in quantities.values()):
            raise ValueError("INVALID_GROSS_QUANTITY")
        marked = sum(q*prices[a] for a,q in quantities.items())
        if not math.isclose(marked,row["nav"][name],rel_tol=1e-10,abs_tol=1e-12):
            raise ValueError("GROSS_QUANTITY_NAV_MISMATCH")
        if row["event"] in {"ACTIVATION","REBALANCE"}:
            if any(not math.isclose(quantities[a]*prices[a],marked/10,rel_tol=1e-10,abs_tol=1e-12) for a in target):
                raise ValueError("GROSS_REBALANCE_NOT_EQUAL_WEIGHT")
        elif previous_q is not None and quantities != previous_q[name]:
            raise ValueError("GROSS_QUANTITIES_CHANGED_ON_HOLD")
    if not math.isclose(prices["BTC"]/initial_btc_price,row["btc_nav"],rel_tol=1e-10,abs_tol=1e-12):
        raise ValueError("GROSS_BTC_RECONCILIATION_FAILED")


def project(ledger, price_rows, one_way_cost_bps):
    if not math.isfinite(one_way_cost_bps) or not 0 <= one_way_cost_bps < 10000:
        raise ValueError("INVALID_ONE_WAY_COST")
    rows = ledger["rows"]
    if not rows or rows[0]["event"] != "ACTIVATION" or len(price_rows) != len(rows):
        raise ValueError("MISSING_ACTIVATION_OR_PRICE_HISTORY")
    strategy_names = sorted(rows[0]["holdings_after_close"])
    if not strategy_names or "BTC_HOLD" in strategy_names:
        raise ValueError("INVALID_STRATEGY_IDENTITY")
    names = strategy_names + ["BTC_HOLD"]
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
        required = {"BTC"} | set(a for target in row["holdings_after_close"].values() for a in target)
        if gross_q is not None:
            required |= set(a for quantities in gross_q.values() for a in quantities)
        if not required <= set(prices) or any(not math.isfinite(prices[a]) or prices[a] <= 0 for a in required):
            raise ValueError("INVALID_OR_MISSING_MARK_PRICE")
        verify_gross_row(row,prices,gross_q,price_rows[0]["BTC"],strategy_names)
        if not i and any(not math.isclose(row["nav"][n],1.0,rel_tol=1e-12) for n in strategy_names):
            raise ValueError("NONUNIT_GROSS_ACTIVATION")
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
    summary = {}
    for name in names:
        gross = rows[-1]["btc_nav"] if name == "BTC_HOLD" else rows[-1]["nav"][name]
        terminal_cost = previous[name]*rate
        summary[name] = {"nav_model_net":previous[name],"return_model_net":previous[name]-1,
                         "gross_return":gross-1,"gross_to_net_drag":gross-previous[name],
                         "cost_nav_units_total":sum(r["portfolios"][name]["cost_nav_units"] for r in result),
                         "hypothetical_terminal_exit_cost_nav_units":terminal_cost,
                         "hypothetical_cash_after_exit":previous[name]-terminal_cost,
                         "hypothetical_return_after_exit":previous[name]-terminal_cost-1,
                         "excess_vs_btc_model_net_percentage_points":100*(previous[name]-previous["BTC_HOLD"])}
    return {"one_way_cost_bps":one_way_cost_bps, "rows":result, "summary":summary}


def build(epoch, grid):
    ledger_path = epoch / "LEDGER.json"
    raw = ledger_path.read_bytes(); ledger = json.loads(raw)
    if ledger.get("epoch_id") != "hold_20260928":
        raise ValueError("UNSUPPORTED_EPOCH_NO_SILENT_ADAPTER")
    prices = [prices_for(row,epoch) for row in ledger["rows"]]
    return {"schema":"gate_btc.momentum_cost_diagnostic.v2", "status":"EX_POST_MODEL_SENSITIVITY_ONLY",
            "source_gross_ledger_sha256":hashlib.sha256(raw).hexdigest(), "epoch_id":ledger["epoch_id"],
            "data_as_of":ledger["rows"][-1]["cutoff"], "source_return_observations":len(ledger["rows"])-1,
            "cost_basis":"INPUT_HYPOTHESIS_FEE_PLUS_SLIPPAGE_PER_BUY_OR_SELL_NOTIONAL_NOT_OBSERVED",
            "activation_cost_included":True,"terminal_liquidation_cost_included":False,
            "funding_and_borrow":"NOT_MODELED_SPOT_UNLEVERED_DIAGNOSTIC_ASSUMPTION_ONLY",
            "fx":"NOT_MODELED_USD_PRICE_NUMERAIRE_NOT_REALIZED_BRL",
            "source_archive_bytes_verified":True,
            "price_archive_manifest_crosschecked":True,"gross_btc_and_fixed_quantities_verified":True,
            "terminal_exit_view":"SEPARATE_HYPOTHETICAL_CASH_VIEW_NOT_INCLUDED_IN_NAV_MODEL_NET","canonical_gross_history_changed":False,
            "prospective_net_credit":0,"scientific_credit":0,"promotion_authority":False,
            "engine_feed":False,"orders":0,"real_capital":0,
            "scenarios":[project(ledger,prices,float(bps)) for bps in grid]}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--epoch',type=Path,required=True)
    ap.add_argument('--one-way-cost-bps',type=float,nargs='+',required=True)
    dest=ap.add_mutually_exclusive_group(required=True)
    dest.add_argument('--output',type=Path)
    dest.add_argument('--output-root',type=Path)
    a=ap.parse_args()
    # Output must be outside canonical evidence, including its parent/descendants.
    destination=a.output or a.output_root
    if destination.resolve().is_relative_to(a.epoch.resolve().parents[1]):
        raise ValueError('DIAGNOSTIC_OUTPUT_CANNOT_OVERWRITE_CANONICAL_EPOCH')
    try:
        result=build(a.epoch,a.one_way_cost_bps)
    except (ValueError,KeyError,OSError,zipfile.BadZipFile,EOFError) as exc:
        result={'status':'BLOCKED_MISSING_OR_INVALID_BOUND_GROSS_EVIDENCE','reason':str(exc),'scientific_credit':0,'prospective_net_credit':0,'orders':0,'real_capital':0,'engine_feed':False}
    if a.output_root:
        ledger_path=a.epoch/'LEDGER.json'
        source_sha=hashlib.sha256(ledger_path.read_bytes()).hexdigest() if ledger_path.exists() else 'NO_LEDGER'
        a.output=a.output_root/'v2'/result.get('data_as_of','BLOCKED')/source_sha/'REPORT.json'
    a.output.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    if a.output.exists() and a.output.read_bytes() != raw:
        raise ValueError('IMMUTABLE_COST_DIAGNOSTIC_CONFLICT')
    a.output.write_bytes(raw)
    print(json.dumps({k:v for k,v in result.items() if k!='scenarios'}))
    return 0 if result['status']=='EX_POST_MODEL_SENSITIVITY_ONLY' else 2


if __name__=='__main__':
    raise SystemExit(main())
