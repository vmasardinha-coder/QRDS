from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any


def install_src(project_root: Path) -> None:
    src = str(project_root / "src")
    if src not in sys.path:
        sys.path.insert(0, src)


def load_phase(project_root: Path, phase: int):
    install_src(project_root)
    names = {
        396: "phase396_repeated_observation_run_manifest_semantics_freeze_research_only",
        397: "phase397_fingerprint_drift_threshold_registry_research_only",
        398: "phase398_repeated_clean_clone_interrupted_resume_reliability_research_only",
        399: "phase399_release_workflow_least_privilege_trigger_isolation_audit_research_only",
        400: "phase400_release_reliability_midpoint_checkpoint_research_only",
        401: "phase401_artifact_provenance_portal_registry_reconciliation_research_only",
        402: "phase402_deterministic_release_package_reconstruction_research_only",
        403: "phase403_scientific_family_opening_block_research_only",
        404: "phase404_repeated_release_reliability_unified_portal_research_only",
        405: "phase405_mandatory_global_full_suite_integrated_checkpoint_research_only",
    }
    return importlib.import_module(
        "crypto_decision_lab.scripts." + names[phase]
    )


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def payload(phase: int, **overrides: Any) -> dict[str, Any]:
    base = {
        "phase": phase,
        "gate": f"PHASE{phase}_TEST",
        "strategy_approved": False,
        "capital_used": 0,
        "canonical_data_writes": 0,
        "active_hypotheses": 0,
        "active_experiment_budget": 0,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "action_status": "NO_ACTION_RESEARCH_ONLY",
    }
    defaults = {
        395: {
            "batch_checkpoint_pass": True,
            "current_portal_relative_path": "artifacts/phase394/index.html",
        },
        396: {"manifest_semantics_frozen": True},
        397: {"drift_thresholds_frozen": True},
        398: {"repeated_reliability_pass": True},
        399: {"workflow_audit_pass": True},
        400: {"midpoint_checkpoint_pass": True},
        401: {"provenance_registry_reconciled": True},
        402: {"deterministic_reconstruction_pass": True},
        403: {"scientific_family_opening_blocked": True},
        404: {
            "portal_ready": True,
            "current_portal_relative_path": "artifacts/phase404/index.html",
        },
    }
    base.update(defaults.get(phase, {}))
    base.update(overrides)
    return base


def assert_locked(result: dict[str, Any]) -> None:
    assert result["strategy_approved"] is False
    assert result["capital_used"] == 0
    assert result["canonical_data_writes"] == 0
    assert result["active_hypotheses"] == 0
    assert result["active_experiment_budget"] == 0
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["action_status"] == "NO_ACTION_RESEARCH_ONLY"
