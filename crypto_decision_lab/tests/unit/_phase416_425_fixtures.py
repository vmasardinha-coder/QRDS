from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

LOCKS = {
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "action_status": "NO_ACTION_RESEARCH_ONLY",
    "decision_layer_allowed": False,
    "canonical_data_writes": 0,
    "orders_allowed": False,
    "capital_allowed": False,
    "position_size": 0,
    "capital_used": 0,
    "real_orders_created": 0,
}

META = {
    416: "certificate_retention_evidence_aging_policy_research_only",
    417: "artifact_freshness_audit_research_only",
    418: "deterministic_reproducibility_spotcheck_research_only",
    419: "documentation_tracking_drift_audit_research_only",
    420: "reliability_retention_midpoint_checkpoint_research_only",
    421: "readonly_governance_evidence_index_research_only",
    422: "future_manual_scientific_approval_prerequisites_audit_research_only",
    423: "approval_absence_scientific_family_closed_guard_research_only",
    424: "reliability_governance_unified_portal_research_only",
    425: "reliability_governance_integrated_checkpoint_research_only",
}

INPUTS = {
    416: [415],
    417: [416],
    418: [415, 416, 417],
    419: [415, 417],
    420: [416, 417, 418, 419],
    421: [420],
    422: [420, 421],
    423: [422],
    424: [420, 421, 422, 423],
    425: list(range(416, 425)),
}


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def assert_locked(payload: dict[str, Any]) -> None:
    assert payload["locks"] == LOCKS
    assert payload["strategy_approved"] is False
    assert payload["capital_used"] == 0
    assert payload["real_orders_created"] == 0


def seed_project(tmp_path: Path) -> Path:
    project = tmp_path / "crypto_decision_lab"

    tracking = project / "docs" / "reports" / "project_tracking"
    tracking.mkdir(parents=True, exist_ok=True)
    documents = {
        "QRDS_ROADMAP_416_425_RESEARCH_ONLY.md": "416 425",
        "QRDS_PROGRESS_TABLE_BY_TENS_PHASE415.md": "406 415",
        "QRDS_MASTER_PROGRESS_BY_TENS_PHASE415.md": "415",
        "QRDS_INTEGRATED_TEST_MILESTONE_406_415.md": "PASS",
    }
    for name, text in documents.items():
        (tracking / name).write_text(text, encoding="utf-8")
    write_json(
        tracking / "qrds_progress_snapshot_phase415.json",
        {"baseline_phase": 415},
    )

    p405 = (
        project
        / "artifacts"
        / "phase405_mandatory_global_full_suite_integrated_checkpoint_research_only"
        / "phase405_mandatory_global_full_suite_integrated_checkpoint_research_only.json"
    )
    write_json(p405, {"phase": 405, "pass": True})

    return project


def phase415_payload() -> dict[str, Any]:
    return {
        "phase": 415,
        "gate": "PHASE415",
        "phase_status": "READY_RESEARCH_ONLY",
        "locks": dict(LOCKS),
        "strategy_approved": False,
        "integrated_checkpoint_ready": True,
        "targeted_suite_executed": True,
        "targeted_suite_pass": True,
        "targeted_test_files": 12,
        "targeted_tests": 12,
        "global_full_suite_required": False,
        "global_full_suite_executed": False,
        "capital_used": 0,
        "real_orders_created": 0,
    }


def build_chain(
    tmp_path: Path,
    through_phase: int,
) -> tuple[Path, dict[int, dict[str, Any]], dict[int, Path]]:
    project = seed_project(tmp_path)
    phase415_path = (
        project
        / "artifacts"
        / "phase415_post_global_suite_integrated_tracking_checkpoint_research_only"
        / "phase415_post_global_suite_integrated_tracking_checkpoint_research_only.json"
    )
    paths: dict[int, Path] = {
        415: write_json(phase415_path, phase415_payload())
    }
    results: dict[int, dict[str, Any]] = {}

    for phase in range(416, through_phase + 1):
        slug = META[phase]
        module = importlib.import_module(
            f"crypto_decision_lab.scripts.phase{phase}_{slug}"
        )
        output_dir = (
            project / "artifacts" / f"phase{phase}_{slug}"
        )
        result = module.build(
            *[paths[number] for number in INPUTS[phase]],
            output_dir=output_dir,
            project_root=project,
            git_root=tmp_path,
            context={},
        )
        results[phase] = result
        paths[phase] = (
            output_dir / f"phase{phase}_{slug}.json"
        )

    return project, results, paths
