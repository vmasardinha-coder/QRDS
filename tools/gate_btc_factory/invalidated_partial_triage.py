#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from autonomous_family_generator import expanded_universe, START_FAMILY

ALLOWED_WAIT = "WAITING_SOURCE_QUALIFICATION"

def contract_for_family(fid: str):
    if not fid.startswith("H") or not fid[1:].isdigit():
        return None
    idx = int(fid[1:]) - START_FAMILY
    u = expanded_universe()
    if idx < 0 or idx >= len(u):
        return None
    feature, direction, window, threshold, lookback = u[idx]
    return {
        "feature": feature,
        "direction": direction,
        "decision_window_minutes": window,
        "abs_z_threshold": threshold,
        "standardization_lookback_sessions": lookback,
    }

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--queue", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--output", required=True)
    args=ap.parse_args()
    q=json.loads(Path(args.queue).read_text())
    e=json.loads(Path(args.evidence).read_text())
    disc=int(e.get("valid_sessions_discovery",0) or 0)
    rows=[]
    seen={}
    for item in q.get("families",[]):
        if item.get("status") != ALLOWED_WAIT:
            continue
        fid=str(item.get("original_family_id",""))
        c=contract_for_family(fid)
        if c is None:
            rows.append({"family_id":fid,"triage_status":"STRUCTURAL_CONTRACT_ERROR","scientific_credit":0})
            continue
        key=(c["feature"],c["direction"],c["decision_window_minutes"],c["abs_z_threshold"],c["standardization_lookback_sessions"])
        if key in seen:
            rows.append({"family_id":fid,"triage_status":"STRUCTURAL_DUPLICATE","duplicate_of":seen[key],"contract":c,"scientific_credit":0})
            continue
        seen[key]=fid
        lookback=c["standardization_lookback_sessions"]
        if disc <= lookback:
            st="NOT_TRIAGEABLE_PARTIAL_CAPACITY"
            reason=f"discovery_sessions_{disc}_not_greater_than_required_lookback_{lookback}"
        else:
            st="PARTIAL_TRIAGE_ELIGIBLE_NO_SCIENTIFIC_CREDIT"
            reason="partial_source_can_compute_causal_feature_but_cannot_reject_or_promote_scientifically"
        rows.append({"family_id":fid,"triage_status":st,"reason":reason,"contract":c,"scientific_credit":0})

    counts={}
    lookbacks={}
    for r in rows:
        counts[r["triage_status"]]=counts.get(r["triage_status"],0)+1
        lb=(r.get("contract") or {}).get("standardization_lookback_sessions")
        if lb is not None:
            lookbacks[str(lb)]=lookbacks.get(str(lb),0)+1

    out={
      "schema":"qrds.factory.invalidated_partial_triage_result.v1",
      "strict_v2_unchanged":True,
      "source_admission_pass":False,
      "economics_feedback_allowed":False,
      "promotion_allowed":False,
      "scientific_rejection_from_partial_performance_allowed":False,
      "partial_evidence":{"discovery_sessions":disc,"replication_sessions":e.get("valid_sessions_replication"),"total_sessions":e.get("valid_sessions_total")},
      "waiting_family_count":len(rows),
      "counts":counts,
      "lookback_distribution":lookbacks,
      "families":rows,
      "conclusion":"PARTIAL_DATA_MAY_ONLY_TRIAGE_WHERE_CAUSAL_LOOKBACK_IS_COMPUTABLE; ALL OTHER FAMILIES REMAIN STRICT_V2_WAITING"
    }
    Path(args.output).write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({k:out[k] for k in ("waiting_family_count","counts","lookback_distribution","conclusion")},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
