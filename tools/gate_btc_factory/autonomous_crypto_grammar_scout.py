#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
import requests

SCHEMA="qrds.factory.crypto_grammar_scout.v1"
OPENALEX="https://api.openalex.org/works"
CHANNELS=[
  {
    "channel_id":"CRYPTO_SPOT_PERP_BASIS_FUNDING",
    "queries":["crypto spot perpetual basis funding predictive return","perpetual futures funding basis crypto"],
    "mechanism":"Spot/perpetual basis and funding dislocations may contain causal information about positioning and subsequent cross-sectional returns.",
    "required_new_data":["spot OHLCV","perpetual OHLCV","funding history","instrument metadata"],
    "official_free_source_candidates":["Binance public market data","OKX public market data"]
  },
  {
    "channel_id":"CRYPTO_CROSS_VENUE_PRICE_DISCOVERY",
    "queries":["cryptocurrency cross exchange price discovery lead lag","bitcoin cross exchange information leadership"],
    "mechanism":"Price discovery may rotate across venues; lagged cross-venue dislocations can define falsifiable lead-lag hypotheses.",
    "required_new_data":["multi-venue synchronized OHLCV","venue clocks","symbol mappings"],
    "official_free_source_candidates":["Binance","OKX","Coinbase"]
  },
  {
    "channel_id":"CRYPTO_DISPERSION_BREADTH_REGIME",
    "queries":["crypto cross sectional dispersion breadth momentum regime","cryptocurrency dispersion breadth market regime"],
    "mechanism":"Cross-sectional breadth and dispersion may condition the payoff of momentum, reversal, and allocation rules without retuning incumbents.",
    "required_new_data":["broad spot universe OHLCV","stable universe membership","delisting metadata"],
    "official_free_source_candidates":["Binance","OKX"]
  },
  {
    "channel_id":"CRYPTO_VOL_LIQUIDATION_STRESS",
    "queries":["crypto liquidation volatility regime returns","bitcoin liquidation cascades volatility predictive"],
    "mechanism":"Observable volatility and liquidation-stress states may define preregistered protection or tactical challenger families.",
    "required_new_data":["OHLCV","open interest","public liquidation or stress proxy","funding"],
    "official_free_source_candidates":["Binance","OKX"]
  },
  {
    "channel_id":"CRYPTO_TERM_STRUCTURE_CARRY",
    "queries":["crypto futures term structure carry momentum","bitcoin futures basis term structure"],
    "mechanism":"Differences across dated futures and perpetual funding may define carry/term-structure challengers separate from existing Delta/QOS/Momentum incumbents.",
    "required_new_data":["dated futures prices","perpetual prices","funding","expiry metadata"],
    "official_free_source_candidates":["Binance","OKX"]
  }
]

def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")

def search(q, per_page=5):
    r=requests.get(OPENALEX,params={"search":q,"per-page":per_page,"select":"id,doi,title,publication_year,primary_location"},timeout=20,headers={"User-Agent":"QRDS-crypto-grammar-scout/1.0"})
    r.raise_for_status()
    out=[]
    for w in r.json().get("results",[]):
        src=(((w.get("primary_location") or {}).get("source") or {}).get("display_name"))
        out.append({"openalex_id":w.get("id"),"doi":w.get("doi"),"title":w.get("title"),"publication_year":w.get("publication_year"),"source":src})
    return out

def existing_ids(existing_dir:Path|None):
    ids=set()
    if not existing_dir or not existing_dir.exists(): return ids
    for p in existing_dir.glob("*.json"):
        try:d=json.loads(p.read_text())
        except Exception:continue
        for x in d.get("proposals",[]): 
            if x.get("channel_id"): ids.add(str(x["channel_id"]))
    return ids

def scout(existing_dir=None, fetcher=search):
    existing=existing_ids(existing_dir)
    proposals=[]
    for ch in CHANNELS:
        rows=[]; errors=[]
        for q in ch["queries"]:
            try: rows.extend(fetcher(q))
            except Exception as exc: errors.append(f"{type(exc).__name__}:{exc}")
        uniq=[]; seen=set()
        for r in rows:
            key=r.get("doi") or r.get("openalex_id") or r.get("title")
            if not key or key in seen: continue
            seen.add(key); uniq.append(r)
        if ch["channel_id"] in existing:
            status="DUPLICATE_CHANNEL_SUPPRESSED"
        elif not uniq:
            status="INSUFFICIENT_EXTERNAL_EVIDENCE_FAIL_CLOSED"
        else:
            status="SCOUTED_NOT_PREREGISTERED"
        pid=hashlib.sha256((ch["channel_id"]+"|"+"|".join(sorted(str(x.get("doi") or x.get("openalex_id") or "") for x in uniq))).encode()).hexdigest()[:16]
        proposals.append({
          "proposal_id":pid,"channel_id":ch["channel_id"],"status":status,
          "mechanism":ch["mechanism"],"required_new_data":ch["required_new_data"],
          "official_free_source_candidates":ch["official_free_source_candidates"],
          "literature_evidence":uniq[:12],"research_errors":errors,
          "history_used_for_selection":False,"requires_separate_preregistration":True,
          "requires_forward_or_independent_unseen_data":True,
          "economics_read":False,"may_allocate_family_id":False,
          "may_modify_incumbent":False,"may_test_threshold_grid":False
        })
    return {
      "schema":SCHEMA,"generated_at_utc":now(),"mode":"IDEATION_ONLY_NO_ECONOMICS",
      "scope":"CRYPTO_NEW_MECHANISMS_ISOLATED_FROM_EXISTING_INCUMBENTS",
      "incumbents_read_only":["DELTA","QOS","MOMENTUM","GATEWAY","V16"],
      "history_used_for_selection":False,
      "evaluation_data_policy":"FORWARD_OR_INDEPENDENT_UNSEEN_ONLY_AFTER_SEPARATE_PREREGISTRATION",
      "proposals":proposals,
      "safety":{"research_only":True,"shadow_only":True,"not_approved":True,"engine_feed":False,"orders":0,"real_capital":0,"no_retune":True,"no_backfill":True,"no_counter_reset":True,"fail_closed":True}
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--existing-dir")
    ap.add_argument("--output",required=True)
    a=ap.parse_args()
    d=scout(Path(a.existing_dir) if a.existing_dir else None)
    Path(a.output).write_text(json.dumps(d,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"proposal_count":len(d["proposals"]),"statuses":{s:sum(x["status"]==s for x in d["proposals"]) for s in sorted({x["status"] for x in d["proposals"]})}},ensure_ascii=False))

if __name__=="__main__": main()
