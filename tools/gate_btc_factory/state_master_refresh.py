#!/usr/bin/env python3
from __future__ import annotations

import json
import re
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

RESULT_RE = re.compile(r"gate_btc_b3_h(\d+)_h(\d+)_result\.json$")
PREREG_RE = re.compile(r"b3_h(\d+)_h(\d+)_.*prereg\.md$")
ISSUE_RE = re.compile(r"(?im)^Issue:\s*#(\d+)\s*$")


def load(path: Path) -> dict:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"FAIL state master refresh cannot read {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(obj, dict):
        raise SystemExit(f"FAIL state master refresh expected object: {path.relative_to(ROOT)}")
    return obj


def _canonical_terminal_results(root: Path) -> list[tuple[int, int, Path, dict]]:
    rows: list[tuple[int, int, Path, dict]] = []
    for path in (root / "tools").glob("gate_btc_b3_h*_h*_result.json"):
        m = RESULT_RE.search(path.name)
        if not m:
            continue
        start, end = map(int, m.groups())
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        expected_status = f"CLOSED_NO_H{start}_H{end}_SURVIVOR"
        if obj.get("status") != expected_status or obj.get("survivors") != []:
            continue
        if obj.get("h1_economics_read") is not False:
            continue
        if obj.get("survivor_partial_economics_read") is not False:
            continue
        if obj.get("engine_feed") is not False:
            continue
        if obj.get("orders_generated") != 0 or obj.get("real_capital_used") != 0:
            continue
        rows.append((start, end, path, obj))
    return sorted(rows, key=lambda r: (r[1], r[0]))


def _canonical_preregs(root: Path) -> list[tuple[int, int, Path, int | None]]:
    rows: list[tuple[int, int, Path, int | None]] = []
    research = root / "research"
    if not research.exists():
        return rows
    for path in research.glob("b3_h*_h*_*prereg.md"):
        m = PREREG_RE.search(path.name)
        if not m:
            continue
        start, end = map(int, m.groups())
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        issue_match = ISSUE_RE.search(text)
        issue = int(issue_match.group(1)) if issue_match else None
        rows.append((start, end, path, issue))
    return sorted(rows, key=lambda r: (r[1], r[0]))


def sync_b3_frontier(src: dict, root: Path = ROOT) -> dict:
    """Sync only a materialized B3 generation pointer from canonical repo evidence.

    No family is invented and no scientific parameter/result is changed. Only a
    terminal CLOSED_NO_* result satisfying immutable safety can retire stale
    pointers. A newer prereg may mark an already-materialized active generation.
    """
    tracks = src.get("tracks", {})
    track = tracks.get("B3_H40_PLUS") if isinstance(tracks, dict) else None
    if not isinstance(track, dict) or track.get("classification") != "OPEN_DISCOVERY":
        return src

    terminals = _canonical_terminal_results(root)
    if not terminals:
        return src
    start, end, result_path, result_obj = terminals[-1]
    terminal_status = str(result_obj["status"])

    preregs = [r for r in _canonical_preregs(root) if r[1] > end]
    row = dict(track)
    row["canonical_terminal_result"] = str(result_path.relative_to(root))
    row["canonical_terminal_generation"] = f"H{start}-H{end}"
    row["open_pr"] = None

    if preregs:
        pstart, pend, prereg_path, issue = preregs[-1]
        row["status"] = f"{terminal_status}__H{pstart}_H{pend}_PREREGISTERED_SOURCE_QA_READY"
        row["canonical_active_prereg"] = str(prereg_path.relative_to(root))
        row["canonical_active_generation"] = f"H{pstart}-H{pend}"
        row["open_issue"] = issue
        row["action"] = (
            f"H{pstart}-H{pend} is already materialized by canonical preregistration; "
            "continue source QA / frozen progression only; no duplicate generation, retune, backfill, or partial economics"
        )
    else:
        row["status"] = terminal_status
        row["open_issue"] = None
        row.pop("canonical_active_prereg", None)
        row.pop("canonical_active_generation", None)
        row["action"] = (
            f"H{start}-H{end} is canonically closed with no survivor; next generation may be created only through frozen factory continuation"
        )

    tracks = dict(tracks)
    tracks["B3_H40_PLUS"] = row
    src["tracks"] = tracks
    return src


def main() -> int:
    src = load(SOURCE)
    if src.get("safety") != SAFETY:
        raise SystemExit("FAIL state master safety boundary mismatch")

    latest = load(FACTORY_LATEST) if FACTORY_LATEST.exists() else {}
    tracks = src.get("tracks")
    if not isinstance(tracks, dict) or not tracks:
        raise SystemExit("FAIL missing canonical factory tracks")

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
    src = sync_b3_frontier(src, ROOT)
    src["generated_at_utc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    src["auto_refresh"] = {
        "mode": "OPERATIONAL_FIELDS_PLUS_CANONICAL_FRONTIER_POINTER",
        "scientific_state_mutation_allowed": False,
        "canonical_frontier_pointer_sync_allowed": True,
        "frontier_authority": "CANONICAL_REPO_TERMINAL_RESULT_AND_PREREG_FILES_ONLY",
        "fail_closed": True,
    }
    OUT.write_text(json.dumps(src, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("FACTORY_STATE_MASTER_REFRESH=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
