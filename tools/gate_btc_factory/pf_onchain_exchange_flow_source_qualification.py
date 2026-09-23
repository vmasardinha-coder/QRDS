#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import requests

ENDPOINT="https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
METRICS=["FlowInBNBNtv","FlowOutBNBNtv"]

def now(): return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")

def qualify(get=requests.get) -> dict:
    params={"assets":"btc","metrics":",".join(METRICS),"frequency":"1d","limit_per_asset":1,"pretty":"true"}
    try:
        r=get(ENDPOINT,params=params,timeout=20)
    except Exception as exc:
        result={"status":"FAIL_CLOSED_SOURCE_UNVERIFIED","http_status":None,"reason":f"{type(exc).__name__}:{exc}"}
    else:
        code=int(getattr(r,"status_code",200))
        if code in (401,403):
            result={"status":"BLOCKED_AUTHORIZATION_OR_PRODUCT_TIER_REQUIRED","http_status":code,"reason":"COIN_METRICS_EXCHANGE_FLOW_NOT_AVAILABLE_ANONYMOUSLY"}
        elif code != 200:
            result={"status":"FAIL_CLOSED_SOURCE_UNVERIFIED","http_status":code,"reason":"UNEXPECTED_HTTP_STATUS"}
        else:
            try: payload=r.json()
            except Exception:
                result={"status":"FAIL_CLOSED_SOURCE_UNVERIFIED","http_status":code,"reason":"INVALID_JSON"}
            else:
                rows=payload.get("data") or []
                if rows and all(m in rows[-1] and rows[-1].get(m) is not None for m in METRICS):
                    result={"status":"QUALIFIED_COMMUNITY_PUBLIC_SOURCE","http_status":code,"reason":"REQUESTED_EXCHANGE_FLOW_METRICS_RETURNED_WITHOUT_API_KEY","latest_time":rows[-1].get("time")}
                else:
                    msg=json.dumps(payload,sort_keys=True)[:1000]
                    result={"status":"BLOCKED_REQUIRED_METRIC_NOT_PUBLICLY_AVAILABLE","http_status":code,"reason":"REQUESTED_METRICS_ABSENT_OR_NULL","response_excerpt":msg}
    return {
        "schema":"gate_btc_2.pf_source_qualification_runtime.v1",
        "generated_at_utc":now(),
        "namespace":"PF::07712a5ee7505e45",
        "grammar_signature":"07712a5ee7505e458bf426cebe935762a46d5e3a12f4b970d13db3c6bb34e95d",
        "channel_id":"CRYPTO_ONCHAIN_EXCHANGE_FLOW",
        "provider":"COIN_METRICS_COMMUNITY_API",
        "api_key_supplied":False,
        "metrics":METRICS,
        "qualification":result,
        "homegrown_exchange_labels_used":False,
        "raw_public_blockchain_treated_as_equivalent":False,
        "economic_outcomes_read":False,
        "historical_backfill_started":False,
        "next_gate":"SEPARATE_SIGNAL_PRODUCER_PREREGISTRATION_BEFORE_ANY_OUTCOME_READ" if result["status"]=="QUALIFIED_COMMUNITY_PUBLIC_SOURCE" else "RETAIN_BLOCKER_UNTIL_ADMISSIBLE_PREREGISTERED_LABELED_EXCHANGE_FLOW_SOURCE_EXISTS",
        "safety":{"research_only":True,"shadow_only":True,"engine_feed":False,"orders":0,"real_capital":0,"no_retune":True,"no_backfill":True,"h1_h31_untouched":True,"canonical_580_untouched":True}
    }

def self_test():
    class R:
        def __init__(self,status,data): self.status_code=status; self._data=data
        def json(self): return self._data
    blocked=qualify(lambda *a,**k:R(403,{"error":"forbidden"}))
    assert blocked["qualification"]["status"]=="BLOCKED_AUTHORIZATION_OR_PRODUCT_TIER_REQUIRED"
    ok=qualify(lambda *a,**k:R(200,{"data":[{"time":"2026-09-22T00:00:00Z","FlowInBNBNtv":"1","FlowOutBNBNtv":"2"}]}))
    assert ok["qualification"]["status"]=="QUALIFIED_COMMUNITY_PUBLIC_SOURCE"
    assert ok["economic_outcomes_read"] is False and ok["historical_backfill_started"] is False
    print("PF_ONCHAIN_EXCHANGE_FLOW_SOURCE_QUALIFICATION_SELF_TEST=PASS")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--output"); ap.add_argument("--self-test",action="store_true"); a=ap.parse_args()
    if a.self_test: self_test(); return 0
    if not a.output: ap.error("--output required")
    d=qualify(); Path(a.output).write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":d["qualification"]["status"],"http_status":d["qualification"].get("http_status"),"next_gate":d["next_gate"]},sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
