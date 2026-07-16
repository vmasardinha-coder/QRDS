from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

LOCKS = {
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "action_status": "NO_ACTION_RESEARCH_ONLY",
    "decision_layer_allowed": False,
    "canonical_data_writes": 0,
    "account_connection_allowed": False,
    "private_api_allowed": False,
    "orders_allowed": False,
    "capital_allowed": False,
    "position_size": 0,
    "capital_used": 0,
    "real_orders_created": 0,
}

MODULES = {
    346: "phase346_abstention_negative_evidence_registration_research_only",
    347: "phase347_abstention_retest_blocklist_research_only",
    348: "phase348_abstention_failure_cause_audit_research_only",
    349: "phase349_abstention_data_limitation_audit_research_only",
    350: "phase350_abstention_closure_integrity_seal_research_only",
    351: "phase351_data_remediation_decision_research_only",
    352: "phase352_new_question_governance_research_only",
    353: "phase353_portal_inventory_registry_research_only",
    354: "phase354_unified_project_entry_portal_research_only",
}


def payload(phase: int, **extra: Any) -> dict[str, Any]:
    result = {
        "project": "QRDS/QOS/GATE BTC",
        "phase": phase,
        "status": f"PHASE{phase}_FIXTURE_RESEARCH_ONLY",
        "locks": dict(LOCKS),
        "historical_result_authorizes_execution": False,
        "strategy_approved": False,
        "forward_shadow_eligible": False,
        "forward_shadow_started": False,
        "paper_trading_started": False,
    }
    result.update(extra)
    return result


def write_json(path: Path, value: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def seed_project(tmp_path: Path) -> tuple[Path, Path]:
    git_root = tmp_path / "repo"
    project = git_root / "crypto_decision_lab"
    (project / "artifacts").mkdir(parents=True)
    (project / "docs/reports/project_tracking").mkdir(parents=True)
    (project / "scripts").mkdir(parents=True)
    (project / "src").mkdir(parents=True)
    (git_root / "README.md").write_text("# Existing QRDS README\n\nExisting content must remain.\n", encoding="utf-8")
    (git_root / "ABRIR_QRDS.ps1").write_text("# fixture launcher\n", encoding="utf-8")
    (project / "scripts/serve_latest_qrds_portal.ps1").write_text("# fixture server\n", encoding="utf-8")
    (project / "scripts/serve_phase354_unified_project_portal.ps1").write_text("# fixture phase354 server\n", encoding="utf-8")

    templates = []
    for index in range(12):
        templates.append(
            {
                "template_id": f"ABSTAIN_TEMPLATE_{index + 1:02d}",
                "model_kind": "LOGISTIC_REGRESSION" if index % 2 == 0 else "THRESHOLD_RULE",
                "feature_bundle": ["EXCHANGE", "QUALITY", "COMBINED"][index % 3],
                "operating_threshold": [0.60, 0.75][index % 2],
            }
        )
    write_json(
        project / "artifacts/phase336_finite_registry_opening_research_only/phase336_finite_registry_opening.json",
        payload(336, active_templates=templates, active_template_count=12, registry_open=True),
    )
    write_json(
        project / "artifacts/phase337_asof_quality_feature_matrix_research_only/phase337_asof_quality_feature_matrix.json",
        payload(337, row_count=26280, future_feature_use_allowed=False),
    )
    write_json(
        project / "artifacts/phase341_regime_provider_missingness_robustness_research_only/phase341_regime_provider_missingness_robustness.json",
        payload(341, robust_template_count=0),
    )

    gate_ids = [
        "REGISTRY_EXACT_12",
        "ASOF_FEATURES_NO_FUTURE",
        "TARGET_THRESHOLD_TRAIN_ONLY",
        "OUTER_HOLDOUT_UNTOUCHED",
        "HOLM_PRIMARY_SUCCESS",
        "CALIBRATION_VALIDATED",
        "ROBUST_ACROSS_STRATA",
        "COVERAGE_RELIABILITY_PASS",
        "NO_DIRECTIONAL_OR_MONETARY_TARGET",
    ]
    gate_records = {}
    for index, template in enumerate(templates):
        gates = []
        for gate_id in gate_ids:
            passed = gate_id in {
                "REGISTRY_EXACT_12",
                "ASOF_FEATURES_NO_FUTURE",
                "TARGET_THRESHOLD_TRAIN_ONLY",
                "OUTER_HOLDOUT_UNTOUCHED",
                "NO_DIRECTIONAL_OR_MONETARY_TARGET",
            }
            gates.append({"gate_id": gate_id, "passed": passed, "waiver_allowed": False})
        gate_records[template["template_id"]] = {
            "gates": gates,
            "passed_gate_count": sum(bool(item["passed"]) for item in gates),
            "gate_count": len(gates),
            "historical_research_candidate_eligible": False,
        }
    write_json(
        project / "artifacts/phase343_research_candidate_eligibility_research_only/phase343_research_candidate_eligibility.json",
        payload(
            343,
            template_gate_records=gate_records,
            eligible_template_ids=[],
            eligible_template_count=0,
            historical_research_candidate_id=None,
            family_decision="CLOSE_ABSTENTION_FAMILY_NO_SURVIVOR_RESEARCH_ONLY",
            registry_open=False,
            experiment_budget_open=False,
        ),
    )

    full_suite = {
        "passed": True,
        "test_file_count": 584,
        "totals": {"tests": 1491, "failures": 0, "errors": 0, "skipped": 0},
        "manifest_stable": True,
    }
    write_json(
        project / "artifacts/phase345_abstention_full_integration_checkpoint_research_only/phase345_abstention_full_integration_checkpoint.json",
        payload(
            345,
            historical_rows=26280,
            template_count=12,
            fold_count=8,
            holm_survivor_count=0,
            robust_template_count=0,
            eligible_template_count=0,
            historical_research_candidate_id=None,
            family_decision="CLOSE_ABSTENTION_FAMILY_NO_SURVIVOR_RESEARCH_ONLY",
            next_window_decision="ABSTENTION_FAMILY_CLOSED_NO_SURVIVOR_RESEARCH_ONLY",
            global_full_suite=full_suite,
        ),
    )
    write_json(
        project / "docs/reports/project_tracking/qrds_progress_snapshot_phase345.json",
        {
            "baseline_phase": 345,
            "next_tracking_checkpoint": 355,
            "next_mandatory_global_full_suite": 365,
            "safety": dict(LOCKS),
        },
    )

    for phase in (314, 344):
        portal = project / f"artifacts/phase{phase}_fixture_portal_research_only/portal/index.html"
        portal.parent.mkdir(parents=True, exist_ok=True)
        portal.write_text(f"<!doctype html><title>Phase {phase}</title><h1>Portal {phase}</h1>", encoding="utf-8")
    return git_root, project



def seed_generated_phase_artifacts(project: Path, through: int) -> None:
    artifacts = project / "artifacts"
    records: dict[int, tuple[str, dict[str, Any]]] = {
        346: (
            "abstention_negative_evidence_registration",
            payload(346, negative_evidence_registered=True, eligible_template_count=0, evaluated_template_count=12, family_decision="CLOSE_ABSTENTION_FAMILY_NO_SURVIVOR_RESEARCH_ONLY", failed_gate_counts={"HOLM_PRIMARY_SUCCESS": 12}),
        ),
        347: (
            "abstention_retest_blocklist",
            payload(347, blocked_template_count=12, semantic_retests_blocked=True, exact_retests_blocked=True, parameter_rescue_allowed=False, new_experiment_budget=0),
        ),
        348: (
            "abstention_failure_cause_audit",
            payload(348, failure_category_count=4, dominant_failure_category="MULTIPLE_TESTING_NO_SURVIVOR", parameter_rescue_recommended=False, scientific_classification="NEGATIVE_RESULT_NOT_SOFTWARE_FAILURE"),
        ),
        349: (
            "abstention_data_limitation_audit",
            payload(349, limitation_count=5, data_quality_issue_proves_edge=False, data_remediation_can_retroactively_rescue_family=False, new_collection_started=False),
        ),
        350: (
            "abstention_closure_integrity_seal",
            payload(350, closure_sealed=True, closure_reopen_allowed=False, parameter_rescue_experiments_allowed=0, active_hypotheses=0, active_experiment_budget=0),
        ),
        351: (
            "data_remediation_decision",
            payload(351, data_remediation_backlog_count=3, data_remediation_reopens_family=False, data_remediation_authorizes_new_hypotheses=False, public_network_collection_started=False, decision="DATA_REMEDIATION_DIAGNOSTICS_ALLOWED_WITHOUT_FAMILY_REOPEN_RESEARCH_ONLY"),
        ),
        352: (
            "new_question_governance",
            payload(352, required_review_gate_count=8, new_question_proposed=False, new_family_opened=False, new_hypotheses_registered=0, new_experiment_budget=0, automatic_question_generation_allowed=False, decision="MANUAL_NEW_QUESTION_OR_DATA_REMEDIATION_REVIEW_ONLY_RESEARCH_ONLY"),
        ),
        353: (
            "portal_inventory_registry",
            payload(353, portal_count=2, latest_existing_portal={"phase": 344, "relative_path": "artifacts/phase344_fixture_portal_research_only/portal/index.html"}, latest_existing_portal_found=True, registry_is_navigation_only=True, scientific_result_changed=False),
        ),
        354: (
            "unified_project_entry_portal",
            payload(354, portal_relative_path="artifacts/phase354_unified_project_entry_portal_research_only/portal/index.html", root_launcher_path=str(project.parent / "ABRIR_QRDS.ps1"), readme_updated_with_marked_block=True, capital_authorized_brl=0, navigation_reorganization_only=True, scientific_result_changed=False),
        ),
    }
    for phase in range(346, through + 1):
        slug, data = records[phase]
        write_json(artifacts / f"phase{phase}_{slug}_research_only" / f"phase{phase}_{slug}.json", data)
    if through >= 354:
        portal = artifacts / "phase354_unified_project_entry_portal_research_only/portal/index.html"
        portal.parent.mkdir(parents=True, exist_ok=True)
        portal.write_text("<!doctype html><h1>fixture phase354 portal</h1>", encoding="utf-8")
        write_json(artifacts / "project_portal_registry/current_portal.json", {"phase": 354, "relative_path": "artifacts/phase354_unified_project_entry_portal_research_only/portal/index.html", "capital_used": 0})

def run_module(project: Path, module: str, *args: str) -> subprocess.CompletedProcess[str]:
    source_root = Path(__file__).resolve().parents[2] / "src"
    env = dict(os.environ)
    env["QRDS_PROJECT_ROOT"] = str(project)
    env["QRDS_GIT_ROOT"] = str(project.parent)
    env["PYTHONPATH"] = str(source_root) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", f"crypto_decision_lab.scripts.{module}", *args],
        cwd=project,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def run_through(project: Path, phase: int) -> None:
    for current in range(346, phase + 1):
        if current == 355:
            raise ValueError("Use run_phase355 for checkpoint.")
        result = run_module(project, MODULES[current])
        assert result.returncode == 0, f"Phase {current} failed\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"


def write_junit(path: Path, tests: int = 10) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'<?xml version="1.0" encoding="utf-8"?><testsuites><testsuite name="targeted" tests="{tests}" failures="0" errors="0" skipped="0" time="0.1"></testsuite></testsuites>',
        encoding="utf-8",
    )
    return path
