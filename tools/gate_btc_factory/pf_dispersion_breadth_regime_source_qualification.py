#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import requests

INSTRUMENTS="https://www.okx.com/api/v5/public/instruments"
CANDLES="https://www.okx.com/api/v5/market/candles"
REQUIRED_META=("instId","instType","baseCcy","quoteCcy","listTime","expTime","state")


def utc_now(): return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")

def _json(get,url,params):
    r=get(url,params=params,timeout=20); r.raise_for_status(); d=r.json()
    if d.get("code") not in (None,"0"): raise RuntimeError(f"OKX_ERROR:{d.get('code')}:{d.get('msg')}")
    return d

def _eligible(row,now_ms):
    if any(k not in row for k in REQUIRED_META): return False
    if row.get("instType")!="SPOT" or row.get("quoteCcy")!="USDT" or row.get("state")!="live": return False
    try: list_time=int(row.get("listTime") or 0)
    except (TypeError,ValueError): return False
    if list_time<=0 or list_time>now_ms: return False
    exp=row.get("expTime")
    if exp not in (None,""):
        try:
            if int(exp)<=now_ms: return False
        except (TypeError,ValueError): return False
    return True

def _has_confirmed_1h(rows):
    return any(isinstance(r,list) and len(r)>=9 and str(r[8])=="1" for r in rows)

def qualify(get=requests.get, now_ms=None):
    now_ms=int(now_ms if now_ms is not None else time.time()*1000)
    source={"provider":"OKX_PUBLIC_API","status":"FAIL_CLOSED_SOURCE_UNVERIFIED"}
    try:
        rows=_json(get,INSTRUMENTS,{"instType":"SPOT"}).get("data") or []
        if not rows: raise ValueError("EMPTY_SPOT_INSTRUMENT_SNAPSHOT")
        missing_meta=sum(1 for r in rows if any(k not in r for k in REQUIRED_META))
        if missing_meta: raise ValueError(f"REQUIRED_METADATA_FIELDS_MISSING:{missing_meta}")
        eligible=sorted((r for r in rows if _eligible(r,now_ms)),key=lambda r:r["instId"])
        if len(eligible)<50: raise ValueError(f"INSUFFICIENT_LIVE_USDT_SPOT_UNIVERSE:{len(eligible)}")
        probes=eligible[:5]
        probe_results=[]
        for r in probes:
            candles=_json(get,CANDLES,{"instId":r["instId"],"bar":"1H","limit":5}).get("data") or []
            ok=_has_confirmed_1h(candles)
            probe_results.append({"instId":r["instId"],"confirmed_1h_observed":ok})
            if not ok: raise ValueError(f"NO_CONFIRMED_1H_CANDLE:{r['instId']}")
        exp_populated=sum(1 for r in rows if r.get("expTime") not in (None,""))
        source={
            "provider":"OKX_PUBLIC_API","status":"QUALIFIED_PUBLIC_SOURCE","authentication_required":False,
            "snapshot_time_ms":now_ms,"raw_spot_instrument_count":len(rows),"eligible_live_usdt_spot_count":len(eligible),
            "required_metadata_fields_present":True,"list_time_field_observed":True,"state_field_observed":True,"exp_time_field_observed":True,
            "exp_time_populated_count":exp_populated,"deterministic_probe_results":probe_results,
            "prospective_genesis_supported":True,"prospective_membership_change_detection_supported":True
        }
    except (ValueError,TypeError,KeyError) as exc:
        source={"provider":"OKX_PUBLIC_API","status":"BLOCKED_REQUIRED_CAUSAL_UNIVERSE_CAPABILITY_MISSING","reason":f"{type(exc).__name__}:{exc}"}
    except Exception as exc:
        source={"provider":"OKX_PUBLIC_API","status":"FAIL_CLOSED_SOURCE_UNVERIFIED","reason":f"{type(exc).__name__}:{exc}"}
    ok=source["status"]=="QUALIFIED_PUBLIC_SOURCE"
    return {
        "schema":"gate_btc_2.pf_source_qualification_runtime.v1","generated_at_utc":utc_now(),
        "namespace":"PF::757b8b0385a1b53b","grammar_signature":"757b8b0385a1b53beb6ad406a69450403a52d05a222d8312d7920fc6019debfa",
        "channel_id":"CRYPTO_DISPERSION_BREADTH_REGIME","status":"SOURCE_QUALIFIED_AWAITING_SEPARATE_BREADTH_PRODUCER_PREREGISTRATION" if ok else source["status"],
        "source":source,
        "universe_policy":{"genesis_immutable":True,"new_listings_after_genesis_enter_universe":False,"missing_or_delisted_members_replaced":False,"historical_membership_reconstruction":False,"missing_policy":"UNAVAILABLE_AND_COUNT_NOT_ZERO_FILL"},
        "xagent_independence":{"eligible_after_separate_producer_preregistration":ok,"evidence_class":"SPOT_CROSS_SECTIONAL_BREADTH","distinct_from":["SPOT_PARTICIPATION_TAKER_FLOW","DERIVATIVES_TERM_STRUCTURE_CARRY"]},
        "economic_outcomes_read":False,"signal_formula_defined":False,"direction_defined":False,"thresholds_defined":False,"historical_backfill_started":False,
        "next_gate":"SEPARATE_BREADTH_SIGNAL_PRODUCER_PREREGISTRATION_BEFORE_ANY_OUTCOME_READ" if ok else "RETAIN_BLOCKER_OR_ADVANCE_WITHOUT_CREDIT",
        "safety":{"research_only":True,"shadow_only":True,"engine_feed":False,"orders":0,"real_capital":0,"no_retune":True,"no_backfill":True,"h1_h31_untouched":True,"canonical_580_untouched":True}
    }

def self_test():
    class R:
        def __init__(self,d): self.d=d
        def raise_for_status(self): pass
        def json(self): return self.d
    now=1800000000000
    universe=[]
    for i in range(60):
        universe.append({"instId":f"C{i:03d}-USDT","instType":"SPOT","baseCcy":f"C{i:03d}","quoteCcy":"USDT","listTime":str(now-1000),"expTime":"","state":"live"})
    def fake(url,params=None,timeout=20):
        if url==INSTRUMENTS: return R({"code":"0","data":universe})
        if url==CANDLES: return R({"code":"0","data":[[str(now-3600000),"1","1","1","1","1","1","1","1"]]})
        raise AssertionError(url)
    d=qualify(fake,now)
    assert d["status"]=="SOURCE_QUALIFIED_AWAITING_SEPARATE_BREADTH_PRODUCER_PREREGISTRATION"
    assert d["source"]["eligible_live_usdt_spot_count"]==60
    assert d["xagent_independence"]["eligible_after_separate_producer_preregistration"] is True
    assert d["economic_outcomes_read"] is False
    print("PF_BREADTH_REGIME_SOURCE_SELF_TEST=PASS")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--output"); ap.add_argument("--self-test",action="store_true"); a=ap.parse_args()
    if a.self_test: self_test(); return 0
    if not a.output: ap.error("--output required")
    d=qualify(); Path(a.output).write_text(json.dumps(d,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":d["status"],"source":d["source"]["status"],"eligible_count":d["source"].get("eligible_live_usdt_spot_count"),"xagent_eligible":d["xagent_independence"]["eligible_after_separate_producer_preregistration"]}))
    return 0
if __name__=="__main__": raise SystemExit(main())
