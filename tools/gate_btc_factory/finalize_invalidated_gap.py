#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

STATUS = "DEFINITIVE_EXTERNAL_DATA_GAP_REVISITABLE"


def load(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(obj, dict):
        raise RuntimeError(f"EXPECTED_OBJECT:{path}")
    return obj


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", type=Path, required=True)
    ap.add_argument("--search", type=Path, required=True)
    ap.add_argument("--policy", type=Path, required=True)
    ns = ap.parse_args()

    q = load(ns.queue)
    s = load(ns.search)
    p = load(ns.policy)
    assert p["terminal_status"] == STATUS
    assert s["root_cause_classification"] == "SOURCE_DATA_GAP"
    assert int(s["affected_family_count"]) == int(q["affected_family_count"])

    gate = s.get("source_gate") or {}
    mt5 = ((s.get("search") or {}).get("mt5_read_only_source_evidence") or {})
    free = (s.get("search") or {}).get("independent_free_github_candidates") or []
    blocking = set(s.get("blocking_requirements") or [])
    required = {
        "EXACT_WIN_SOURCE_IDENTITY",
        "M5_SCHEMA_AND_SESSION_TIMEZONE",
        "MINIMUM_HISTORY_COVERAGE",
        "PUBLICATION_SEMANTICS",
        "REVISION_SEMANTICS",
        "POINT_IN_TIME_VALIDITY",
        "INDEPENDENT_UNSEEN_EVALUATION_WINDOWS",
        "HASH_BOUND_DATASET",
    }

    any_public_qualified = any(
        x.get("identity_qa_pass") is True
        and x.get("schema_qa_pass") is True
        and x.get("publication_semantics_proven") is True
        and x.get("revision_semantics_proven") is True
        and x.get("point_in_time_valid") is True
        for x in free if isinstance(x, dict)
    )
    can_close = (
        s.get("status") == "ACTIVE_SEARCHING_QUALIFICATION"
        and gate.get("present") is False
        and gate.get("valid") is False
        and mt5.get("source_admission_pass") is False
        and not any_public_qualified
        and required.issubset(blocking)
    )

    if can_close:
        for row in q.get("families") or []:
            if row.get("status") == "WAITING_SOURCE_QUALIFICATION":
                row["status"] = STATUS
                row["source_gate_status"] = "DEFINITIVE_GAP_AFTER_FREE_OFFICIAL_SOURCE_EXHAUSTION"
        q["definitive_external_data_gap_count"] = sum(1 for x in q["families"] if x.get("status") == STATUS)
        q["completed_family_count"] = sum(
            1 for x in q["families"]
            if x.get("status") in {STATUS, "SCIENTIFIC_REJECTION", "VALID_SURVIVOR_READY_FOR_SEPARATE_PROSPECTIVE"}
        )
        q["waiting_source_count"] = sum(1 for x in q["families"] if x.get("status") == "WAITING_SOURCE_QUALIFICATION")
        q["legacy_passive_backlog_closed"] = q["completed_family_count"] == q["affected_family_count"]
        q["reactivation_policy"] = "AUTO_REOPEN_IF_ANY_VALID_GLOBAL_OR_SCOPED_SOURCE_GATE_GREEN"
        q["definitive_gap_evidence_generated_at_utc"] = s.get("generated_at_utc")
        q["updated_at_utc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        ns.queue.write_text(json.dumps(q, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"DEFINITIVE_GAP_CLOSED={q['definitive_external_data_gap_count']}")
        print(f"LEGACY_BACKLOG_CLOSED={str(q['legacy_passive_backlog_closed']).lower()}")
    else:
        print("DEFINITIVE_GAP_CLOSED=0")
        print("LEGACY_BACKLOG_CLOSED=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
