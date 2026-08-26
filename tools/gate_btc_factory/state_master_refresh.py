#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tools/gate_btc_research_factory_status.json"
FACTORY_LATEST = ROOT / "tools/gate_btc_factory/FACTORY_STATUS_LATEST.json"
OUT = ROOT / "tools/gate_btc_research_factory_status.json"

SAFETY = {
    "research_only": True,
    "shadow_only": True,
    "not_approved": True,
    "orders": 0,
    "real_capital": 0,
    "engine_feed": False,
    "no_holdout_contamination": True,
}


def load(path: Path) -> dict:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"FAIL state master refresh cannot read {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(obj, dict):
        raise SystemExit(f"FAIL state master refresh expected object: {path.relative_to(ROOT)}")
    return obj


def main() -> int:
    src = load(SOURCE)
    if src.get("safety") != SAFETY:
        raise SystemExit("FAIL state master safety boundary mismatch")

    latest = load(FACTORY_LATEST) if FACTORY_LATEST.exists() else {}
    tracks = src.get("tracks")
    if not isinstance(tracks, dict) or not tracks:
        raise SystemExit("FAIL missing canonical factory tracks")

    # Refresh is deliberately conservative: it preserves canonical scientific
    # classifications/status text unless a canonical factory status artifact
    # carries a same-named track object. Unknown/missing evidence never clears
    # blockers or approvals.
    latest_tracks = latest.get("tracks", {}) if isinstance(latest, dict) else {}
    if latest_tracks and not isinstance(latest_tracks, dict):
        raise SystemExit("FAIL invalid latest factory tracks")

    merged = {}
    for name, current in tracks.items():
        if not isinstance(current, dict):
            raise SystemExit(f"FAIL invalid track {name}")
        candidate = latest_tracks.get(name)
        if isinstance(candidate, dict):
            row = dict(current)
            # Only operational freshness/observation fields may be refreshed
            # automatically. Scientific status/classification/threshold content
            # remains frozen unless changed canonically elsewhere.
            for key in (
                "last_success_at", "last_snapshot", "prospective_count",
                "next_expected_run", "blocker", "open_issue", "open_pr",
                "source_qa_workflow_run", "source_qa_artifact",
            ):
                if key in candidate:
                    row[key] = candidate[key]
            merged[name] = row
        else:
            merged[name] = dict(current)

    src["tracks"] = merged
    src["generated_at_utc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    src["auto_refresh"] = {
        "mode": "OPERATIONAL_FIELDS_ONLY",
        "scientific_state_mutation_allowed": False,
        "fail_closed": True,
    }
    OUT.write_text(json.dumps(src, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("FACTORY_STATE_MASTER_REFRESH=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
