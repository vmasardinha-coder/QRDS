from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE101_REPLAY_EVIDENCE_QUERY_INDEX_RESEARCH_ONLY_READY_RESEARCH_ONLY"

PHASES = list(range(84, 101))

LOCKS = {
    "app_mode": "INTERACTIVE_RESEARCH_ONLY",
    "policy_lock": "ACTIVE",
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "edge_validated": False,
    "edge_operationally_validated": False,
    "shadow_decision_allowed": False,
    "decision_layer_allowed": False,
    "trading_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "operational_decision_allowed": False,
    "safe_apply_allowed": False,
    "promotion_allowed": False,
    "canonical_data_writes": 0,
}

QUERY_TAGS = {
    "inventory": ["artifact", "presence", "files", "phase96"],
    "digest": ["sha256", "integrity", "hash", "phase97"],
    "drift": ["sentinel", "drift", "needs_review", "phase98"],
    "preflight": ["batch", "preflight", "phase99"],
    "checkpoint": ["checkpoint", "batch", "phase90", "phase100"],
    "portal": ["portal", "index", "qa", "phase91"],
    "runbook": ["runbook", "human_review", "checklist", "phase92", "phase93"],
    "readiness": ["matrix", "readiness", "blocked", "phase94"],
}

def classify_phase(phase: int, file_names: list[str]) -> list[str]:
    joined = " ".join(file_names).lower()
    tags: list[str] = []

    for tag, keywords in QUERY_TAGS.items():
        if any(keyword in joined for keyword in keywords):
            tags.append(tag)

    if "test_" in joined:
        tags.append("tests")
    if "summary" in joined:
        tags.append("summary")
    if "research_only" in joined:
        tags.append("research_only")

    return sorted(set(tags))

def phase_files(root: Path, phase: int) -> list[Path]:
    paths: list[Path] = []
    paths.extend((root / "src" / "crypto_decision_lab" / "scripts").glob(f"phase{phase}_*_research_only.py"))
    paths.extend((root / "tests" / "unit").glob(f"test_phase{phase}_*_research_only.py"))
    paths.extend((root / "docs" / "reports" / "journal_replay").glob(f"phase{phase}_*"))
    return sorted(path for path in paths if path.is_file())

def build_query_index(project_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root) if project_root else Path.cwd()

    entries = []
    for phase in PHASES:
        files = phase_files(root, phase)
        relative_files = [path.relative_to(root).as_posix() for path in files]
        file_names = [path.name for path in files]

        entries.append({
            "phase": phase,
            "file_count": len(files),
            "files": relative_files,
            "tags": classify_phase(phase, file_names),
            "query_status": "INDEXED_RESEARCH_ONLY" if files else "NEEDS_REVIEW_RESEARCH_ONLY",
        })

    needs_review = [entry["phase"] for entry in entries if entry["query_status"] != "INDEXED_RESEARCH_ONLY"]

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "index_name": "replay_evidence_query_index_84_100",
        "phase_start": 84,
        "phase_end": 100,
        "phase_count": len(entries),
        "entries": entries,
        "needs_review_phases": needs_review,
        "query_index_pass": len(needs_review) == 0,
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase101(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase101_replay_evidence_query_index_research_only"
    out.mkdir(parents=True, exist_ok=True)

    index = build_query_index()
    (out / "phase101_replay_evidence_query_index.json").write_text(
        json.dumps(index, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "gate": READY_GATE,
        "ready": index["query_index_pass"],
        "query_index": index,
        **LOCKS,
    }

def main() -> int:
    result = build_phase101()
    index = result["query_index"]

    print(result["gate"])
    print("Query index pass:", index["query_index_pass"])
    print("Needs review phases:", index["needs_review_phases"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if index["query_index_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
