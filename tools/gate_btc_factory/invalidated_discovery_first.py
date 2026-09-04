#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.gate_btc_factory.autonomous_family_evaluator import load_data, eval_family
from tools.gate_btc_factory.invalidated_family_requalification_runner import family_contracts

SAFETY = {
    "research_only": True,
    "shadow_only": True,
    "not_approved": True,
    "engine_feed": False,
    "orders": 0,
    "real_capital": 0,
    "no_retune": True,
    "no_backfill": True,
    "no_counter_reset": True,
    "fail_closed": True,
    "h1_economics_read": False,
}

DISCOVERY_START = "2025-01-01"
DISCOVERY_END = "2025-12-31"
REPLICATION_START = "2026-01-01"
REPLICATION_END = "2026-08-09"


def load(path: Path) -> dict[str, Any]:
    obj=json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(obj, dict): raise RuntimeError(f"EXPECTED_OBJECT:{path}")
    return obj


def dump(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True)+"\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def subset(sessions: dict[str, Any], start: str, end: str) -> dict[str, Any]:
    return {k:v for k,v in sessions.items() if start <= k <= end}


def structurally_eligible_for_discovery(sessions: dict[str, Any], contract: dict[str, Any]) -> tuple[bool, str]:
    if not sessions:
        return False, "NO_DISCOVERY_SESSIONS"
    dates=sorted(sessions)
    halves={f"{d[:4]}H{1 if int(d[5:7]) <= 6 else 2}" for d in dates}
    if len(halves) < 2:
        return False, "LESS_THAN_TWO_CALENDAR_HALVES"
    lookback=int(contract.get("standardization_lookback_sessions",20))
    usable=max(0,len(dates)-lookback)
    if usable < 60:
        return False, f"MAX_SIGNAL_CAPACITY_BELOW_MIN_TRADES:{usable}"
    return True, "DISCOVERY_STRUCTURAL_CAPACITY_PASS"


def discovery_result(fid: str, contract: dict[str, Any], sessions: dict[str, Any], namespace: str, gate_id: str) -> dict[str, Any]:
    eligible, reason=structurally_eligible_for_discovery(sessions, contract)
    base={
        "schema":"qrds.factory.invalidated_discovery_first_result.v1",
        "namespace":namespace,
        "original_family_id":fid,
        "source_gate_id":gate_id,
        "discovery_window":{"start":DISCOVERY_START,"end":DISCOVERY_END},
        "replication_window_reserved":{"start":REPLICATION_START,"end":REPLICATION_END},
        "historical_result_rewritten":False,
        "historical_observations_credited":0,
        "same_historical_window_rerun":False,
        "safety":dict(SAFETY),
    }
    if not eligible:
        return {**base,"status":"INCONCLUSIVE_DISCOVERY_STRUCTURALLY_INSUFFICIENT","scientific_rejection":False,"survives_discovery":False,"structural_reason":reason}
    disc=eval_family(sessions,contract)
    if disc.get("survives") is True:
        return {**base,"status":"DISCOVERY_SURVIVOR_WAITING_INDEPENDENT_REPLICATION","scientific_rejection":False,"survives_discovery":True,"discovery":disc,"structural_reason":reason}
    return {**base,"status":"SCIENTIFIC_REJECTION_DISCOVERY","scientific_rejection":True,"survives_discovery":False,"discovery":disc,"structural_reason":reason}


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--root-cause",type=Path,required=True)
    ap.add_argument("--results-dir",type=Path,required=True)
    ap.add_argument("--queue",type=Path,required=True)
    ap.add_argument("--dataset",type=Path,required=True)
    ap.add_argument("--dataset-sha256",required=True)
    ap.add_argument("--runtime-dir",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ns=ap.parse_args()

    root=load(ns.root_cause); q=load(ns.queue)
    if root.get("root_cause_classification") != "SOURCE_DATA_GAP": raise RuntimeError("ROOT_CAUSE_NOT_SOURCE_DATA_GAP")
    ids=[str(x) for x in (root.get("affected_scope") or {}).get("family_ids") or []]
    if len(ids)!=768 or int((root.get("affected_scope") or {}).get("family_count",0))!=768: raise RuntimeError("AFFECTED_SCOPE_NOT_768")
    if sha256(ns.dataset) != ns.dataset_sha256: raise RuntimeError("DATASET_HASH_MISMATCH")
    sessions=load_data(ns.dataset)
    disc_sessions=subset(sessions,DISCOVERY_START,DISCOVERY_END)
    contracts=family_contracts(ns.results_dir)
    if any(fid not in contracts for fid in ids): raise RuntimeError("MISSING_FROZEN_CONTRACT")
    if len(disc_sessions) < 100: raise RuntimeError(f"DISCOVERY_DATA_TOO_SMALL:{len(disc_sessions)}")

    rows_by_id={str(x.get("original_family_id")):x for x in q.get("families") or []}
    results=[]
    for i,fid in enumerate(ids):
        row=rows_by_id[fid]
        namespace=f"RQ_DISCOVERY_2025_V1::{fid}"
        gate_id=f"WIN_M5_DISCOVERY_2025_BATCH_{i//64+1:02d}"
        res=discovery_result(fid,copy.deepcopy(contracts[fid]),disc_sessions,namespace,gate_id)
        result_path=ns.runtime_dir/"results"/f"{namespace.replace('::','__')}.json"
        prereg_path=ns.runtime_dir/"preregistrations"/f"{namespace.replace('::','__')}.json"
        prereg={
            "schema":"qrds.factory.invalidated_discovery_first_prereg.v1",
            "namespace":namespace,
            "original_family_id":fid,
            "grammar_contract":copy.deepcopy(contracts[fid]),
            "grammar_contract_mode":"EXACT_FROZEN_ORIGINAL",
            "source_gate_id":gate_id,
            "dataset_sha256":ns.dataset_sha256,
            "discovery_window":{"start":DISCOVERY_START,"end":DISCOVERY_END},
            "replication_window_reserved":{"start":REPLICATION_START,"end":REPLICATION_END},
            "economics_read_before_freeze":False,
            "historical_observations_credited":0,
            "same_historical_window_rerun":False,
            "safety":dict(SAFETY),
        }
        dump(prereg_path,prereg); dump(result_path,res)
        row["new_namespace"]=namespace
        row["attempts"]=int(row.get("attempts",0))+1
        row["source_gate_id"]=gate_id
        row["source_gate_status"]="DISCOVERY_2025_HASH_BOUND_UNSEEN"
        row["result_path"]=str(result_path)
        if res["status"]=="SCIENTIFIC_REJECTION_DISCOVERY":
            row["status"]="SCIENTIFIC_REJECTION"
        elif res["status"]=="DISCOVERY_SURVIVOR_WAITING_INDEPENDENT_REPLICATION":
            row["status"]="WAITING_INDEPENDENT_REPLICATION_2026"
        else:
            row["status"]="INCONCLUSIVE_INSUFFICIENT_ELIGIBLE_UNSEEN_DATA"
        results.append(res)

    q["completed_family_count"]=sum(1 for x in q["families"] if x.get("status") in {"SCIENTIFIC_REJECTION","VALID_SURVIVOR_READY_FOR_SEPARATE_PROSPECTIVE"})
    q["discovery_rejection_count"]=sum(1 for x in q["families"] if x.get("status")=="SCIENTIFIC_REJECTION")
    q["waiting_replication_count"]=sum(1 for x in q["families"] if x.get("status")=="WAITING_INDEPENDENT_REPLICATION_2026")
    q["inconclusive_count"]=sum(1 for x in q["families"] if str(x.get("status","")).startswith("INCONCLUSIVE"))
    q["waiting_source_count"]=sum(1 for x in q["families"] if x.get("status")=="WAITING_SOURCE_QUALIFICATION")
    q["discovery_first_namespace"]="RQ_DISCOVERY_2025_V1"
    q["discovery_first_dataset_sha256"]=ns.dataset_sha256
    q["updated_at_utc"]=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    dump(ns.output,q)
    print(json.dumps({"affected":len(ids),"discovery_sessions":len(disc_sessions),"rejected":q["discovery_rejection_count"],"waiting_replication":q["waiting_replication_count"],"inconclusive":q["inconclusive_count"],"orders":0,"real_capital":0},sort_keys=True))
    return 0

if __name__=="__main__": raise SystemExit(main())
