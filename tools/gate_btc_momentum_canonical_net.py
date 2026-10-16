"""Forward paper cost binding; gross epochs and old net=N/D fields are immutable."""
from __future__ import annotations
import argparse, copy, hashlib, json, math, sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.gate_btc_momentum_cost_diagnostic import prices_for, project, rebalance

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/"migration/reporting/momentum_canonical_paper_cost_model_20261017.json"
MODEL_ID="paper_spot_10bps_20261017_v1"
SCOPES={"M1_M2_HOLD_20260928":"momentum_m1_m2_economics/epochs/hold_20260928",
        "M3_AFTER_GAP_2026_10_12":"momentum_m3_economics/epochs/after_gap_2026-10-12"}

def packed(x):return (json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def verify_model(c):
    if (c.get("model_id")!=MODEL_ID or c.get("first_activation_cutoff")!="2026-10-17"
        or c.get("one_way_total_cost_bps")!=10 or c.get("venue")!="ABSTRACT_PAPER_SPOT_NO_OBSERVED_ACCOUNT_TIER"
        or c.get("gross_mutation") is not False or c.get("source_epochs_joined") is not False
        or c.get("orders")!=0 or c.get("real_capital")!=0 or c.get("engine_feed") is not False):
        raise ValueError("FROZEN_COST_MODEL_CHANGED")
    return c

def load_verified(epoch,scope):
    original=read(epoch/"LEDGER.json"); ledger=copy.deepcopy(original)
    if scope=="M1_M2_HOLD_20260928":
        if original.get("epoch_id")!="hold_20260928":raise ValueError("WRONG_M1M2_EPOCH")
    elif scope=="M3_AFTER_GAP_2026_10_12":
        from tools.gate_btc_momentum_m3_economics import validate, verify_contract
        contract=read(epoch/"CONTRACT.json");verify_contract(contract)
        validate(original,read(epoch/"ACTIVATION.json"),contract)
        for row in ledger["rows"]:
            signal=epoch/"signals"/(row["cutoff"]+".json")
            if sha(signal.read_bytes())!=row["evidence"]["signal_file_sha256"]:
                raise ValueError("M3_SIGNAL_CHANGED")
            manifest=read(epoch/"source_prices"/row["cutoff"]/"MANIFEST.json")
            row["evidence"]["source_available_at_utc"]=manifest["available_at_utc"]
            row["holdings_after_close"]={"M3_TOP10":list(row["quantities"])}
            row["quantities_after_close"]={"M3_TOP10":row["quantities"]}
            row["nav"]={"M3_TOP10":row["nav"]}
    else:raise ValueError("UNSUPPORTED_NET_SCOPE")
    prices=[prices_for(row,epoch) for row in ledger["rows"]]
    # Includes the sealed gross NAV, BTC, cadence, held-quantity and source checks.
    project(ledger,prices,0)
    return ledger,prices

def calculate(ledger,prices,model):
    verify_model(model)
    if len(ledger["rows"])!=len(prices):raise ValueError("PRICE_ROW_COUNT")
    first=model["first_activation_cutoff"]; rate=model["one_way_total_cost_bps"]/10000
    selected=[(r,p) for r,p in zip(ledger["rows"],prices) if r["cutoff"]>=first]
    if not selected:return []
    if selected[0][0]["cutoff"]!=first:raise ValueError("MISSING_NET_ACTIVATION_NO_LATE_BACKFILL")
    names=sorted(selected[0][0]["nav"])+["BTC_HOLD"];q={};previous={};result=[]
    for i,(gross,marks) in enumerate(selected):
        if i and date.fromisoformat(gross["cutoff"])-date.fromisoformat(selected[i-1][0]["cutoff"])!=timedelta(days=1):
            raise ValueError("NET_GAP_NO_SILENT_BRIDGE")
        output={"cutoff":gross["cutoff"],"event":"ACTIVATION" if i==0 else gross["event"],
                "return_observations":i,"source_evidence":copy.deepcopy(gross.get("evidence",{})),
                "source_gross_return_observations":gross["return_observations"],"portfolios":{}}
        for name in names:
            if i==0:
                net=1/(1+rate);cost=1-net;traded=net
                if name=="BTC_HOLD":q[name]={"BTC":net/marks["BTC"]}
                else:
                    base=gross["nav"][name]
                    q[name]={a:amount*net/base for a,amount in gross["quantities_after_close"][name].items()}
            else:
                values={a:amount*marks[a] for a,amount in q[name].items()}
                if name!="BTC_HOLD" and gross["event"]=="REBALANCE":
                    target=gross["holdings_after_close"][name]
                    net,cost,traded=rebalance(values,target,0.0,rate)
                    q[name]={a:net/len(target)/marks[a] for a in target}
                else:net,cost,traded=sum(values.values()),0.0,0.0
            if not math.isfinite(net) or net<=0:raise ValueError("INVALID_NET_NAV")
            anchor=selected[0][0]
            gross_ratio=(gross["btc_nav"]/anchor["btc_nav"] if name=="BTC_HOLD"
                         else gross["nav"][name]/anchor["nav"][name])
            output["portfolios"][name]={"nav_net_model":net,
                "daily_return_net_model":None if not i else net/previous[name]-1,
                "return_from_unit_cash_net_model":net-1,"same_window_gross_return":gross_ratio-1,
                "cost_nav_units":cost,"traded_notional_nav_units":traded,
                "quantities_after_close":copy.deepcopy(q[name]),
                "hypothetical_cash_after_full_exit":net*(1-rate)}
            previous[name]=net
        result.append(output)
    return result

def immutable(path,obj):
    raw=packed(obj)
    if path.exists() and path.read_bytes()!=raw:raise ValueError("IMMUTABLE_NET_RECEIPT_CONFLICT")
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)

def run(runtime,out,model,now=None):
    verify_model(model);now=now or datetime.now(timezone.utc)
    if not now.tzinfo:raise ValueError("UTC_CLOCK_REQUIRED")
    if out.resolve().is_relative_to((runtime/"runtime/ledgers/momentum_m1_m2_economics").resolve()) or out.resolve().is_relative_to((runtime/"runtime/ledgers/momentum_m3_economics").resolve()):
        raise ValueError("NET_OUTPUT_CANNOT_OVERWRITE_GROSS")
    binding=sha(packed(model));base=out/MODEL_ID;immutable(base/"CONTRACT.json",model)
    statuses=[]
    for scope,relative in SCOPES.items():
        epoch=runtime/"runtime/ledgers"/relative
        status={"scope":scope,"model_id":MODEL_ID,"model_sha256":binding,
                "first_activation_cutoff":model["first_activation_cutoff"],
                "cost_status":"CANONICAL_ABSTRACT_PAPER_MODEL_NOT_OBSERVED_COSTS",
                "scientific_credit":0,"historical_net_credit":0,
                "engine_feed":False,"orders":0,"real_capital":0}
        if now.date()<=date.fromisoformat(model["first_activation_cutoff"]):
            status.update(status="WAITING_FIRST_FUTURE_COMPLETED_CLOSE",return_observations=0)
        else:
            ledger,prices=load_verified(epoch,scope)
            if any(date.fromisoformat(r["cutoff"])>=now.date() for r in ledger["rows"]):
                raise ValueError("SOURCE_CLOSE_NOT_COMPLETED")
            rows=calculate(ledger,prices,model)
            if not rows:raise ValueError("EXPECTED_FORWARD_GROSS_CLOSE_NOT_AVAILABLE")
            # No joining epochs, retroactive net rows, or mutable latest-only economic truth.
            previous_paths=sorted((base/scope/"observations").glob("*.json"))
            for old in previous_paths:
                matching=next((r for r in rows if r["cutoff"]==old.stem),None)
                if matching is None:raise ValueError("NET_SOURCE_HISTORY_RETRACTED")
            for row in rows:
                immutable(base/scope/"observations"/(row["cutoff"]+".json"),
                          {"model_sha256":binding,"scope":scope,**row})
            status.update(status="ACTIVE_CANONICAL_PAPER_NET_MODEL",data_as_of=rows[-1]["cutoff"],
                          return_observations=len(rows)-1,latest=rows[-1],
                          gross_source_ledger_sha256=sha((epoch/"LEDGER.json").read_bytes()))
        (base/scope).mkdir(parents=True,exist_ok=True)
        (base/scope/"STATUS.json").write_bytes(packed(status));statuses.append(status)
    return statuses

def main():
    p=argparse.ArgumentParser();p.add_argument("--runtime",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    print(json.dumps(run(a.runtime,a.output,read(CONTRACT)),sort_keys=True))
if __name__=="__main__":main()
