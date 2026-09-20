#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SCHEMA = "qrds.factory.grammar_semantic_prereg.v1"
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
REQUIRED = {"feature", "window", "lookback", "target"}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bundle(paths: list[Path]) -> dict:
    if not paths:
        raise ValueError("FAIL_CLOSED: no semantic prereg inputs")
    families = []
    seen_ids: set[str] = set()
    seen_sigs: set[str] = set()
    sources = []
    for path in paths:
        d = _load(path)
        if d.get("schema") != SCHEMA:
            raise ValueError(f"FAIL_CLOSED: unexpected semantic schema: {path}")
        if d.get("frozen_before_source_cost") is not True or d.get("outcome_blind") is not True:
            raise ValueError(f"FAIL_CLOSED: semantic prereg not outcome-blind/frozen: {path}")
        if d.get("economics_read") is not False or d.get("historical_testing_started") is not False:
            raise ValueError(f"FAIL_CLOSED: semantic prereg opened economics/history: {path}")
        if d.get("safety") != SAFETY:
            raise ValueError(f"FAIL_CLOSED: semantic safety mismatch: {path}")
        sources.append({"path": str(path), "sha256": _sha(path), "scope": d.get("scope")})
        for row in d.get("families", []):
            fid = row.get("family_id")
            sig = row.get("grammar_signature")
            sem = row.get("frozen_semantics")
            if not fid or not sig or fid in seen_ids or sig in seen_sigs:
                raise ValueError("FAIL_CLOSED: duplicate/missing semantic identity across bundles")
            if not isinstance(sem, dict) or set(sem) != REQUIRED or any(not sem[k] for k in REQUIRED):
                raise ValueError(f"FAIL_CLOSED: incomplete frozen semantics: {fid}")
            seen_ids.add(fid)
            seen_sigs.add(sig)
            families.append(row)
    return {
        "schema": SCHEMA,
        "authorization": "CUMULATIVE_IMMUTABLE_SEMANTIC_BUNDLE",
        "scope": "XAWINWDO_GRAMMAR_SCOUT_CUMULATIVE_SEMANTIC_BUNDLE",
        "frozen_before_source_cost": True,
        "outcome_blind": True,
        "economics_read": False,
        "historical_testing_started": False,
        "selection_policy": "PRESERVE_SOURCE_ARTIFACTS_EXACTLY_NO_RETUNE",
        "source_artifacts": sources,
        "families": families,
        "prohibitions": [
            "NO_OUTCOME_READ", "NO_ECONOMICS_READ", "NO_RETUNE", "NO_BACKFILL",
            "NO_THRESHOLD_GRID", "NO_WINDOW_GRID", "NO_LOOKBACK_GRID", "NO_TARGET_GRID",
            "NO_PERFORMANCE_BASED_SOURCE_SELECTION", "NO_COUNTER_RESET"
        ],
        "safety": SAFETY,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", action="append", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    out = bundle([Path(x) for x in args.input])
    Path(args.output).write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"source_count": len(out["source_artifacts"]), "family_count": len(out["families"])}, sort_keys=True))


if __name__ == "__main__":
    main()
