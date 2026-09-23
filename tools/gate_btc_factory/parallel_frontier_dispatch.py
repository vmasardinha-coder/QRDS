#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from grammar_scout_handoff import build_handoff

BLOCKED_PREFIXES = ("WAITING_", "BLOCKED_", "DATA_GAP", "FAIL_CLOSED")
SAFETY = {
    "research_only": True, "shadow_only": True, "not_approved": True,
    "engine_feed": False, "orders": 0, "real_capital": 0,
    "no_retune": True, "no_backfill": True, "no_counter_reset": True,
    "h1_h31_untouched": True, "canonical_frontier_untouched": True,
    "economics_read": False,
}

def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def _handoff_compatible_scout(scout: dict) -> dict:
    out=copy.deepcopy(scout)
    for row in out.get("proposals",[]):
        if "may_change_existing_grammar" not in row and row.get("may_modify_incumbent") is False:
            row["may_change_existing_grammar"]=False
    return out

def load_scout_history(paths: list[str] | None, dirs: list[str] | None) -> list[dict]:
    scouts=[]; seen=set()
    for raw in paths or []:
        p=Path(raw)
        if p.exists():
            key=str(p.resolve())
            if key not in seen:
                scouts.append(load(p)); seen.add(key)
    for raw in dirs or []:
        d=Path(raw)
        if not d.exists(): continue
        for p in sorted(d.glob("*.json")):
            key=str(p.resolve())
            if key in seen: continue
            try: scouts.append(load(p)); seen.add(key)
            except Exception: continue
    return scouts

def _requests_from_scouts(scouts: list[dict], handoff_ledger_dir: Path) -> list[dict]:
    merged={}
    for scout in scouts:
        if scout.get("mode") != "IDEATION_ONLY_NO_ECONOMICS" or scout.get("history_used_for_selection") is not False:
            continue
        handoff=build_handoff(_handoff_compatible_scout(scout),handoff_ledger_dir)
        for request in handoff.get("requests",[]):
            sig=str(request.get("grammar_signature") or "")
            if not sig: raise ValueError("fail closed: request missing grammar signature")
            merged.setdefault(sig,request)
    return sorted(merged.values(),key=lambda r:(str(r.get("grammar_signature") or ""),str(r.get("channel_id") or "")))

def build_parallel(current: dict, scouts: dict | list[dict], handoff_ledger_dir: Path) -> dict:
    status=str(current.get("status") or ""); generation=str(current.get("generation") or "")
    if not status.startswith(BLOCKED_PREFIXES):
        return {"schema":"qrds.factory.parallel_frontier.v1","status":"NOOP_CANONICAL_FRONTIER_NOT_BLOCKED","canonical_generation":generation,"canonical_status":status,"selected":None,"safety":SAFETY}
    scout_list=scouts if isinstance(scouts,list) else [scouts]
    requests=_requests_from_scouts(scout_list,handoff_ledger_dir)
    if not requests:
        return {"schema":"qrds.factory.parallel_frontier.v1","status":"NOOP_NO_NOVEL_OUTCOME_BLIND_HANDOFF","canonical_generation":generation,"canonical_status":status,"selected":None,"scout_count":len(scout_list),"safety":SAFETY}
    selected=requests[0]
    if selected.get("economics_read") is not False: raise ValueError("fail closed: selected request read economics")
    if selected.get("may_allocate_existing_h_id") is not False: raise ValueError("fail closed: request may allocate existing H id")
    if selected.get("may_modify_existing_grammar") is not False: raise ValueError("fail closed: request may modify existing grammar")
    if selected.get("next_gate") != "SEPARATE_PREREGISTRATION_BEFORE_ANY_OUTCOME_READ": raise ValueError("fail closed: invalid next gate")
    sig=str(selected["grammar_signature"])
    return {
        "schema":"qrds.factory.parallel_frontier.v1",
        "status":"PARALLEL_FRONTIER_PREREGISTERED_AWAITING_SOURCE_QUALIFICATION",
        "namespace":f"PF::{sig[:16]}","canonical_generation":generation,"canonical_status":status,
        "canonical_frontier_mutated":False,
        "selection_policy":"FIRST_NOVEL_GRAMMAR_SIGNATURE_ASCENDING_OUTCOME_BLIND_ACROSS_APPEND_ONLY_SCOUT_HISTORY",
        "scout_count":len(scout_list),"selected":selected,"family_ids_allocated":[],
        "historical_credit":0,"retroactive_credit":0,"promotion_authority":False,
        "next_gate":"SOURCE_QUALIFICATION_THEN_SEPARATE_CHILD_PREREGISTRATION","safety":SAFETY,
    }

def self_test() -> None:
    import tempfile
    current={"generation":"H2730-H2739","status":"WAITING_OFFICIAL_TICK_SOURCE"}
    old={"mode":"IDEATION_ONLY_NO_ECONOMICS","history_used_for_selection":False,"proposals":[{"channel_id":"CRYPTO_A","status":"SCOUTED_NOT_PREREGISTERED","mechanism":"a","required_new_data":["a"],"official_free_source_candidates":["PUBLIC"],"economics_read":False,"may_modify_incumbent":False}]}
    newer={"mode":"IDEATION_ONLY_NO_ECONOMICS","history_used_for_selection":False,"proposals":[{"channel_id":"CRYPTO_A","status":"DUPLICATE_CHANNEL_SUPPRESSED","mechanism":"a","required_new_data":["a"],"official_free_source_candidates":["PUBLIC"],"economics_read":False,"may_modify_incumbent":False}]}
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); hist=root/"hist"; hist.mkdir()
        (hist/"1.json").write_text(json.dumps(old)); (hist/"2.json").write_text(json.dumps(newer))
        scouts=load_scout_history([], [str(hist)])
        out=build_parallel(current,scouts,root/"ledger")
        assert out["status"].startswith("PARALLEL_FRONTIER_")
        assert out["selected"]["channel_id"]=="CRYPTO_A"
        assert out["safety"]["economics_read"] is False
    print("PARALLEL_FRONTIER_SELF_TEST=PASS")

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--current"); ap.add_argument("--scout",action="append"); ap.add_argument("--scout-dir",action="append"); ap.add_argument("--handoff-ledger-dir"); ap.add_argument("--output"); ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test: self_test(); return 0
    if not all([a.current,a.handoff_ledger_dir,a.output]) or not (a.scout or a.scout_dir): ap.error("current, scout/scout-dir, handoff-ledger-dir and output are required")
    scouts=load_scout_history(a.scout,a.scout_dir)
    out=build_parallel(load(Path(a.current)),scouts,Path(a.handoff_ledger_dir))
    Path(a.output).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":out["status"],"namespace":out.get("namespace"),"selected":(out.get("selected") or {}).get("channel_id"),"scout_count":out.get("scout_count")}))
    return 0
if __name__=="__main__": raise SystemExit(main())
