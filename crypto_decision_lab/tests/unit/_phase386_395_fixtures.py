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


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_phase_module(phase: int):
    install_src(PROJECT_ROOT)
    mapping = {
        386: "phase386_observation_only_use_case_freeze_research_only",
        387: "phase387_schema_compatibility_observation_adapter_research_only",
        388: "phase388_repeated_integrity_fingerprint_observation_research_only",
        389: "phase389_release_harness_failure_taxonomy_coverage_audit_research_only",
        390: "phase390_clean_clone_interrupted_resume_fixture_exercise_research_only",
        391: "phase391_github_manual_pr_release_workflow_validation_research_only",
        392: "phase392_scientific_novelty_approval_gate_research_only",
        393: "phase393_no_scientific_family_checkpoint_research_only",
        394: "phase394_observation_release_hardening_unified_portal_research_only",
        395: "phase395_observation_release_hardening_integrated_checkpoint_research_only",
    }
    return importlib.import_module("crypto_decision_lab.scripts." + mapping[phase])


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def payload(phase: int, **overrides: Any) -> dict[str, Any]:
    base = {
        "phase": phase,
        "capital_used": 0,
        "canonical_data_writes": 0,
        "strategy_approved": False,
        "active_hypotheses": 0,
        "active_experiment_budget": 0,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "action_status": "NO_ACTION_RESEARCH_ONLY",
    }
    defaults = {
        383: {"release_harness_pass": True},
        385: {
            "batch_gate": "PHASE376_385_NONCANONICAL_RESEARCH_DATASET_ADOPTION_CHECKPOINT_PASS_RESEARCH_ONLY",
            "candidate_dataset_adopted_noncanonical": True,
            "candidate_dataset_adopted_canonical": False,
            "candidate_contract_fingerprint": "abc",
            "candidate_row_count": 26280,
            "raw_input_count": 4,
        },
        386: {"observation_only_use_cases_frozen": True},
        387: {"schema_compatible": True},
        388: {"fingerprints_stable": True},
        389: {"release_harness_coverage_complete": True},
        390: {"fixture_exercise_pass": True},
        391: {"workflow_configuration_valid": True},
        392: {"explicit_novelty_approval_present": False, "scientific_family_opened": False},
        393: {"scientific_family_opened": False, "no_scientific_family_checkpoint_pass": True},
        394: {"portal_ready": True, "current_portal_relative_path": "artifacts/phase394/index.html"},
    }
    base.update(defaults.get(phase, {}))
    base.update(overrides)
    return base


def assert_locked(result: dict[str, Any]) -> None:
    assert result["capital_used"] == 0
    assert result["canonical_data_writes"] == 0
    assert result["strategy_approved"] is False
    assert result["active_hypotheses"] == 0
    assert result["active_experiment_budget"] == 0
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["action_status"] == "NO_ACTION_RESEARCH_ONLY"
