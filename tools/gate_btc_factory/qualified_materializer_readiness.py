#!/usr/bin/env python3
"""Read-only reconciliation of Factory materializers and prospective receipts."""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime
from pathlib import Path

FOCUS_ID = "XAGRAMMAR_728DC88D691B"
FOCUS_ACTIVATION = "2026-10-06T00:00:00Z"
SUPPORTED = {
    "XAGRAMMAR_62943307741A": {"required_sources": ["B3", "CVM"], "materializer": "GRAMMAR_007_CVM_FUND_FLOW_B3"},
    FOCUS_ID: {"required_sources": ["B3", "BCB"], "materializer": "GRAMMAR_007_BCB_FOCUS_B3"},
}

def prospective_state(prereg=None, capture=None):
    if prereg is None:
        if capture is not None:
            raise ValueError("prospective capture requires its preregistration")
        return {}
    if (prereg.get("schema") != "qrds.factory.grammar_007.focus_prospective_prereg.v1"
            or prereg.get("family_id") != FOCUS_ID
            or prereg.get("activation_utc") != FOCUS_ACTIVATION
            or prereg.get("source") != "BCB_OLINDA_EXPECTATIVAS"):
        raise ValueError("prospective preregistration identity mismatch")
    for key in ["scientific_credit", "prospective_credit"]:
        if prereg.get(key) != 0:
            raise ValueError("prospective preregistration credit changed")
    if prereg.get("promotion_authority") is not False:
        raise ValueError("prospective promotion is forbidden")
    result = {"prospective_preregistration_present": True, "capture_verified": False}
    if capture is None:
        return result
    body = {k: v for k, v in capture.items() if k != "capture_sha256"}
    digest = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if digest != capture.get("capture_sha256"):
        raise ValueError("prospective capture hash mismatch")
    if (capture.get("schema") != "qrds.factory.grammar_007.focus_prospective_capture.v1"
            or capture.get("family_id") != FOCUS_ID
            or capture.get("activation_utc") != FOCUS_ACTIVATION
            or capture.get("collection_started") is not True):
        raise ValueError("prospective capture identity mismatch")
    for key in ["scientific_credit", "prospective_credit"]:
        if capture.get(key) != 0:
            raise ValueError("prospective capture credit changed")
    for key in ["promotion_authority", "outcomes_read", "economics_read"]:
        if capture.get(key) is not False:
            raise ValueError("prospective capture isolation changed")
    for key, value in prereg["safety"].items():
        if capture.get("safety", {}).get(key) != value:
            raise ValueError("prospective capture safety mismatch")
    observed = capture.get("observations")
    if not isinstance(observed, list) or capture.get("observation_count") != len(observed):
        raise ValueError("prospective observation count mismatch")
    expected = "PROSPECTIVE_OBSERVATIONS_CAPTURED" if observed else "NO_NEW_ELIGIBLE_PUBLICATION"
    if capture.get("status") != expected:
        raise ValueError("prospective capture status mismatch")
    when = datetime.fromisoformat(capture["captured_at_utc"].replace("Z", "+00:00"))
    activation = datetime.fromisoformat(FOCUS_ACTIVATION.replace("Z", "+00:00"))
    if when.tzinfo is None or when < activation:
        raise ValueError("prospective capture precedes activation")
    return {**result, "capture_verified": True, "prospective_capture_status": capture["status"],
            "prospective_capture_at_utc": capture["captured_at_utc"],
            "prospective_observations_reported": len(observed), "capture_sha256": digest}

def build(intake: dict, evidence: dict | None = None, prereg=None, capture=None) -> dict:
    evidence = evidence or {}
    ev = evidence.get("families", {})
    prospective = prospective_state(prereg, capture)
    rows = []
    for f in intake.get("families", []):
        fid = f["family_id"]
        spec = SUPPORTED.get(fid)
        if spec is None:
            raise RuntimeError("UNRECOGNIZED_QUALIFIED_FAMILY:" + fid)
        got = sorted(f.get("qualified_sources", []))
        if got != sorted(spec["required_sources"]):
            raise RuntimeError("QUALIFIED_SOURCE_MISMATCH:" + fid)
        e = ev.get(fid, {})
        count = int(e.get("row_count", 0) or 0)
        ready = fid == FOCUS_ID and e.get("status") == "FEATURES_MATERIALIZED_OUTCOME_BLIND" and count > 0
        terminal = fid == "XAGRAMMAR_62943307741A" and e.get("status") == "SOURCE_BLOCKED_NO_VERSIONED_PIT_VALUES"
        row = {"family_id": fid, "materializer_id": spec["materializer"], "qualified_sources": got,
               "implementation_status": "MATERIALIZER_PROVEN_OUTCOME_BLIND" if ready else ("TERMINAL_SOURCE_BLOCKED_PIT_VALUES" if terminal else "SOURCE_MATERIALIZER_REQUIRED"),
               "physical_capture_proven": bool(ready or terminal), "pit_feature_materialization_proven": bool(ready),
               "materialized_feature_rows": count, "source_blocker": e.get("blocker"),
               "collection_started": False, "scientific_credit": 0,
               "next_action": "SEPARATE_PROSPECTIVE_COLLECTION_PREREG_REQUIRED" if ready else ("SOURCE_REQUALIFICATION_ONLY_IF_VERSIONED_PIT_VALUES_FOUND" if terminal else "IMPLEMENT_OFFICIAL_SOURCE_CAPTURE_AND_PIT_TESTS")}
        if ready and prospective:
            row.update(prospective)
            row["collection_started"] = prospective["capture_verified"]
            row["next_action"] = ("WAIT_NEXT_ELIGIBLE_OFFICIAL_PUBLICATION" if prospective["capture_verified"]
                                  else "START_PREREGISTERED_PROSPECTIVE_COLLECTION")
        rows.append(row)
    return {"schema": "qrds.factory.qualified_materializer_readiness.v2", "families": rows,
            "ready_count": sum(x["implementation_status"] == "MATERIALIZER_PROVEN_OUTCOME_BLIND" for x in rows),
            "terminal_source_blocked_count": sum(x["implementation_status"] == "TERMINAL_SOURCE_BLOCKED_PIT_VALUES" for x in rows),
            "blocked_count": sum(x["implementation_status"] != "MATERIALIZER_PROVEN_OUTCOME_BLIND" for x in rows),
            "safety": {"RESEARCH_ONLY": True, "SHADOW_ONLY": True, "ENGINE_FEED": False, "ORDERS": 0, "REAL_CAPITAL": 0,
                       "NO_BACKFILL": True, "NO_RETUNE": True, "FAIL_CLOSED": True}}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--intake", required=True)
    p.add_argument("--evidence")
    p.add_argument("--prospective-prereg")
    p.add_argument("--prospective-capture")
    p.add_argument("--output", required=True)
    a = p.parse_args()
    prereg_path = Path(a.prospective_prereg) if a.prospective_prereg else Path(__file__).resolve().parents[2] / "artifacts/gate_btc_2/GRAMMAR_007_FOCUS_PROSPECTIVE_PREREG_20261006.json"
    capture_path = Path(a.prospective_capture) if a.prospective_capture else Path(a.intake).parent / "grammar_007_focus_prospective/LATEST.json"
    def read_optional(path):
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    ev = read_optional(Path(a.evidence)) if a.evidence else None
    out = build(json.loads(Path(a.intake).read_text(encoding="utf-8")), ev, read_optional(prereg_path), read_optional(capture_path))
    Path(a.output).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"ready": out["ready_count"], "blocked": out["blocked_count"], "terminal": out["terminal_source_blocked_count"]}))

if __name__ == "__main__":
    main()
