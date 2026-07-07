from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE106_REPLAY_EVIDENCE_QUERY_EXPORT_MANIFEST_RESEARCH_ONLY_READY_RESEARCH_ONLY"

PHASES = [101, 102, 103, 104, 105]

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

EXPORT_TARGETS = [
    {
        "name": "json_manifest",
        "format": "json",
        "purpose": "machine-readable descriptive query evidence export",
        "allowed": True,
    },
    {
        "name": "markdown_summary",
        "format": "md",
        "purpose": "human-readable descriptive query evidence export",
        "allowed": True,
    },
    {
        "name": "portal_stub",
        "format": "html",
        "purpose": "visual descriptive query evidence export",
        "allowed": True,
    },
    {
        "name": "trading_signal_export",
        "format": "blocked",
        "purpose": "blocked: evidence export cannot become trading signal",
        "allowed": False,
    },
    {
        "name": "allocation_export",
        "format": "blocked",
        "purpose": "blocked: evidence export cannot become allocation",
        "allowed": False,
    },
]

def collect_phase_files(root: Path, phase: int) -> list[str]:
    paths: list[Path] = []
    paths.extend((root / "src" / "crypto_decision_lab" / "scripts").glob(f"phase{phase}_*_research_only.py"))
    paths.extend((root / "tests" / "unit").glob(f"test_phase{phase}_*_research_only.py"))
    paths.extend((root / "docs" / "reports" / "journal_replay").glob(f"phase{phase}_*"))
    return sorted(path.relative_to(root).as_posix() for path in paths if path.is_file())

def build_export_manifest(project_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root) if project_root else Path.cwd()

    phase_entries = []
    for phase in PHASES:
        files = collect_phase_files(root, phase)
        phase_entries.append({
            "phase": phase,
            "file_count": len(files),
            "files": files,
            "export_status": "EXPORTABLE_RESEARCH_ONLY" if files else "NEEDS_REVIEW_RESEARCH_ONLY",
        })

    failed = [entry["phase"] for entry in phase_entries if entry["export_status"] != "EXPORTABLE_RESEARCH_ONLY"]
    blocked_targets = [target for target in EXPORT_TARGETS if target["allowed"] is False]

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "manifest_name": "replay_evidence_query_export_manifest_101_105",
        "phase_batch": PHASES,
        "phase_entries": phase_entries,
        "export_targets": EXPORT_TARGETS,
        "blocked_targets": blocked_targets,
        "failed_phases": failed,
        "export_manifest_pass": len(failed) == 0 and len(blocked_targets) == 2,
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase106(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase106_replay_evidence_query_export_manifest_research_only"
    out.mkdir(parents=True, exist_ok=True)

    manifest = build_export_manifest()
    (out / "phase106_replay_evidence_query_export_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "gate": READY_GATE,
        "ready": manifest["export_manifest_pass"],
        "manifest": manifest,
        **LOCKS,
    }

def main() -> int:
    result = build_phase106()
    manifest = result["manifest"]

    print(result["gate"])
    print("Export manifest pass:", manifest["export_manifest_pass"])
    print("Failed phases:", manifest["failed_phases"])
    print("Blocked targets:", [target["name"] for target in manifest["blocked_targets"]])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if manifest["export_manifest_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
