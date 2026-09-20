#!/usr/bin/env python3
"""Materialize frozen Factory 006 source/cost adjudications as qualifier packets.

This tool never reads outcomes/economics and never changes semantics. It validates the
adjudication against the canonical intake identity and semantic freeze SHA, then writes
one immutable evidence packet per family for the existing qualifier.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

SAFETY = {
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
    "NOT_APPROVED": True,
    "ENGINE_FEED": False,
    "ORDERS": 0,
    "REAL_CAPITAL": 0,
    "NO_RETUNE": True,
    "NO_BACKFILL": True,
    "NO_COUNTER_RESET": True,
    "FAIL_CLOSED": True,
    "H1_H31_UNTOUCHED": True,
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def materialize(intake: dict, adjudication: dict, out_dir: Path) -> dict:
    if adjudication.get("schema") != "qrds.factory.grammar_source_cost_adjudication.v1":
        raise ValueError("FAIL_CLOSED: unexpected adjudication schema")
    if adjudication.get("outcomes_read") is not False or adjudication.get("economics_read") is not False:
        raise ValueError("FAIL_CLOSED: adjudication opened outcomes/economics")
    if adjudication.get("retune") is not False:
        raise ValueError("FAIL_CLOSED: adjudication retune forbidden")
    safety = adjudication.get("safety")
    if not isinstance(safety, dict) or any(safety.get(k) != v for k, v in SAFETY.items()):
        raise ValueError("FAIL_CLOSED: adjudication safety mismatch")

    intake_rows = {x["family_id"]: x for x in intake.get("families", [])}
    adj_rows = adjudication.get("families", [])
    if len(adj_rows) != len(intake_rows):
        raise ValueError("FAIL_CLOSED: adjudication/intake family count mismatch")
    seen = set()
    packets = []
    semantic_sha = adjudication.get("semantic_prereg_sha256")
    if not semantic_sha:
        raise ValueError("FAIL_CLOSED: missing semantic freeze sha")

    for row in adj_rows:
        fid = row.get("family_id")
        if not fid or fid in seen or fid not in intake_rows:
            raise ValueError("FAIL_CLOSED: missing/duplicate/orphan adjudication family")
        seen.add(fid)
        source = intake_rows[fid]
        if source.get("semantic_preregistration_complete") is not True:
            raise ValueError(f"FAIL_CLOSED: family semantics not complete: {fid}")
        if source.get("semantic_prereg_sha256") != semantic_sha:
            raise ValueError(f"FAIL_CLOSED: semantic freeze sha mismatch: {fid}")
        if row.get("grammar_signature") != source.get("grammar_signature"):
            raise ValueError(f"FAIL_CLOSED: grammar signature mismatch: {fid}")
        allowed = set(source.get("official_free_source_candidates", []))
        chosen = row.get("qualified_sources", [])
        if not chosen or any(x not in allowed for x in chosen):
            raise ValueError(f"FAIL_CLOSED: non-preregistered adjudication source: {fid}")
        if row.get("outcomes_read") is not False or row.get("economics_read") is not False:
            raise ValueError(f"FAIL_CLOSED: premature read in family adjudication: {fid}")
        if row.get("decision") != "REJECT_SOURCE_COST_FAIL_CLOSED":
            raise ValueError(f"FAIL_CLOSED: adjudication decision must match recorded failed checks: {fid}")
        checks = row.get("source_checks", {})
        required = ["official_public_free", "required_data_covered", "pit_timestamps", "granularity_sufficient", "calendar_causal", "reproducible_auditable"]
        if all(checks.get(k) is True for k in required):
            raise ValueError(f"FAIL_CLOSED: rejection has no failed source check: {fid}")
        packet = {
            "schema": "qrds.factory.grammar_source_cost_family_evidence.v1",
            "family_id": fid,
            "grammar_signature": row["grammar_signature"],
            "semantic_prereg_sha256": semantic_sha,
            "qualified_sources": chosen,
            "source_checks": checks,
            "cost_checks": row.get("cost_checks", {}),
            "outcomes_read": False,
            "economics_read": False,
            "adjudication_decision": row["decision"],
            "adjudication_reason": row.get("reason"),
            "evidence_authorities": adjudication.get("evidence_authorities", []),
            "safety": SAFETY,
        }
        packets.append(packet)

    if seen != set(intake_rows):
        raise ValueError("FAIL_CLOSED: incomplete family adjudication")
    out_dir.mkdir(parents=True, exist_ok=True)
    for packet in packets:
        (out_dir / f"{packet['family_id']}.json").write_text(
            json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return {"materialized_count": len(packets), "family_ids": sorted(seen), "safety": SAFETY}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--intake", required=True)
    ap.add_argument("--adjudication", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()
    result = materialize(load(Path(args.intake)), load(Path(args.adjudication)), Path(args.output_dir))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
