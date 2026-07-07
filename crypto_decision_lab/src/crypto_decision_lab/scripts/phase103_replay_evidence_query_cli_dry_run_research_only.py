from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase101_replay_evidence_query_index_research_only import build_query_index
from crypto_decision_lab.scripts.phase102_replay_evidence_query_manifest_research_only import build_query_manifest

READY_GATE = "PHASE103_REPLAY_EVIDENCE_QUERY_CLI_DRY_RUN_RESEARCH_ONLY_READY_RESEARCH_ONLY"

BLOCKED_ROUTES = {"decision_query", "signal_query", "allocation_query"}

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

def dry_run_query(route: str, value: str | int | None = None, project_root: str | Path | None = None) -> dict[str, Any]:
    index = build_query_index(project_root)
    manifest = build_query_manifest(project_root)

    if route in BLOCKED_ROUTES:
        return {
            "route": route,
            "value": value,
            "allowed": False,
            "query_status": "BLOCKED_RESEARCH_ONLY",
            "results": [],
            "reason": "Decision, signal and allocation routes are blocked in research-only mode.",
            **LOCKS,
        }

    results: list[dict[str, Any]] = []

    if route == "by_phase":
        phase_value = int(value) if value is not None else None
        results = [entry for entry in index["entries"] if entry["phase"] == phase_value]

    elif route == "by_tag":
        tag_value = str(value)
        results = [entry for entry in index["entries"] if tag_value in entry["tags"]]

    elif route == "by_checkpoint":
        results = [entry for entry in index["entries"] if "checkpoint" in entry["tags"]]

    elif route == "by_review_status":
        status_value = str(value) if value is not None else "INDEXED_RESEARCH_ONLY"
        results = [entry for entry in index["entries"] if entry["query_status"] == status_value]

    else:
        return {
            "route": route,
            "value": value,
            "allowed": False,
            "query_status": "UNKNOWN_ROUTE_NEEDS_REVIEW_RESEARCH_ONLY",
            "results": [],
            "reason": "Unknown evidence query route.",
            **LOCKS,
        }

    return {
        "route": route,
        "value": value,
        "allowed": True,
        "query_status": "PASS_RESEARCH_ONLY",
        "manifest_gate": manifest["gate"],
        "source_index_gate": index["gate"],
        "result_count": len(results),
        "results": results,
        **LOCKS,
    }

def build_cli_dry_run(project_root: str | Path | None = None) -> dict[str, Any]:
    sample_queries = [
        dry_run_query("by_phase", 100, project_root),
        dry_run_query("by_tag", "checkpoint", project_root),
        dry_run_query("by_review_status", "INDEXED_RESEARCH_ONLY", project_root),
        dry_run_query("decision_query", "should_buy", project_root),
        dry_run_query("signal_query", "btc", project_root),
        dry_run_query("allocation_query", "portfolio", project_root),
    ]

    blocked = [query for query in sample_queries if query["allowed"] is False]
    allowed = [query for query in sample_queries if query["allowed"] is True]

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dry_run_name": "replay_evidence_query_cli_dry_run",
        "sample_queries": sample_queries,
        "allowed_query_count": len(allowed),
        "blocked_query_count": len(blocked),
        "blocked_routes": sorted(BLOCKED_ROUTES),
        "dry_run_pass": len(blocked) == 3 and all(query["query_status"] == "BLOCKED_RESEARCH_ONLY" for query in blocked),
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase103(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase103_replay_evidence_query_cli_dry_run_research_only"
    out.mkdir(parents=True, exist_ok=True)

    dry_run = build_cli_dry_run()
    (out / "phase103_replay_evidence_query_cli_dry_run.json").write_text(
        json.dumps(dry_run, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "gate": READY_GATE,
        "ready": dry_run["dry_run_pass"],
        "dry_run": dry_run,
        **LOCKS,
    }

def main() -> int:
    result = build_phase103()
    dry_run = result["dry_run"]

    print(result["gate"])
    print("Dry run pass:", dry_run["dry_run_pass"])
    print("Allowed query count:", dry_run["allowed_query_count"])
    print("Blocked query count:", dry_run["blocked_query_count"])
    print("Blocked routes:", dry_run["blocked_routes"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if dry_run["dry_run_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
