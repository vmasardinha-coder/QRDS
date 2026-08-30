#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REASONS={"SOURCE_NOT_PUBLISHED","SOURCE_FAILURE","STRUCTURAL_FAIL","NON_TRADING_DAY","DUPLICATE","OTHER","STRUCTURAL_PASS"}


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def classify_gap(g: dict) -> str:
    text=" ".join(str(g.get(k,"")) for k in ("classification","reason","status","detail","failure_reason")).upper()
    if "NOT_PUBLISHED" in text or "NOT PUBLISHED" in text or "404" in text: return "SOURCE_NOT_PUBLISHED"
    if "NON_TRADING" in text or "NON-TRADING" in text: return "NON_TRADING_DAY"
    if "STRUCTURAL" in text or "SCHEMA" in text or "QA" in text: return "STRUCTURAL_FAIL"
    if "SOURCE" in text or "HTTP" in text or "DOWNLOAD" in text or "RETRY" in text: return "SOURCE_FAILURE"
    return "OTHER"


def build(anchor: dict, existing: dict|None, date: str, mode: str, reason: str, run_id: str):
    a=anchor["canonical_evidence"]
    base_q=int(a["qualified"])
    anchor_date=str(a["last_candidate_date"])
    prior=existing or {}
    q=max(base_q,int(prior.get("qualified",base_q)))
    events=list(prior.get("post_anchor_events",[]))
    by_date={str(e["date"]):e for e in events}
    counted=False
    final_reason=reason
    if date <= anchor_date:
        final_reason="DUPLICATE"
    elif date in by_date:
        prior_e=by_date[date]
        if prior_e.get("candidate_status") != ("STRUCTURAL_PASS" if mode=="qualified" else mode.upper()):
            raise RuntimeError(f"conflicting canonical H1 evidence for {date}")
        final_reason="DUPLICATE"
    elif mode=="qualified":
        if q >= 20: raise RuntimeError("H1 already at 20/20; collection must be frozen")
        q += 1
        counted=True
        final_reason="STRUCTURAL_PASS"
    if final_reason not in REASONS: final_reason="OTHER"
    if date > anchor_date and date not in by_date:
        events.append({
            "date":date,
            "candidate_status":"STRUCTURAL_PASS" if mode=="qualified" else mode.upper(),
            "counted":counted,
            "counter_after":q,
            "reason":final_reason,
            "source_run_id":str(run_id),
        })
    events.sort(key=lambda e:e["date"])
    return {
        "schema":"qrds.h1.canonical_runtime.v1",
        "status":f"H1_{q}_OF_20_CANONICAL",
        "qualified":q,
        "remaining":20-q,
        "anchor_qualified":base_q,
        "anchor_last_qualified_session":anchor_date,
        "last_qualified_session":max([anchor_date]+[e["date"] for e in events if e.get("counted")]),
        "economics_locked":True,
        "economics_unlock_requires_integrity_green":True,
        "collector_should_continue":q<20,
        "checkpoint_trigger_reached":q==20,
        "post_anchor_events":events,
        "separate_runtime_structural_count_must_not_be_added":True,
        "read_only_historical_ledger":True,
        "no_counter_rewrite":True,
        "no_backfill_as_prospective":True,
        "no_retune":True,
        "orders":0,
        "real_capital":0,
        "updated_at_utc":datetime.now(timezone.utc).isoformat(),
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--anchor",type=Path,required=True)
    ap.add_argument("--existing",type=Path)
    ap.add_argument("--artifact-root",type=Path,required=True)
    ap.add_argument("--mode",choices=["qualified","gap"],required=True)
    ap.add_argument("--date",required=True)
    ap.add_argument("--run-id",required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    a=load(args.anchor)
    existing=load(args.existing) if args.existing and args.existing.exists() else None
    if args.mode=="qualified": reason="STRUCTURAL_PASS"
    else:
        gaps=list(args.artifact_root.rglob("H1_OPERATIONAL_GAP.json"))
        reason=classify_gap(load(gaps[0])) if len(gaps)==1 else "OTHER"
    out=build(a,existing,args.date,args.mode,reason,args.run_id)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(f"H1_CANONICAL_COUNTER={out['qualified']}/20")
    print(f"H1_REMAINING={out['remaining']}")
    print("ECONOMICS_LOCKED=true")

if __name__=="__main__": main()
