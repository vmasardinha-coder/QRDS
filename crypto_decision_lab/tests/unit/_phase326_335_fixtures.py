from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase301_305_evidence_v2_common import LOCKS


def payload(phase: int, **fields: Any) -> dict[str, Any]:
    value = {
        "phase": phase,
        "project": "QRDS/QOS/GATE BTC",
        "status": f"PHASE_{phase}_TEST",
        "descriptive_only": True,
        "valid_for_decision": False,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "historical_result_authorizes_execution": False,
        "locks": dict(LOCKS),
        "gate": f"PHASE{phase}_TEST_GATE_RESEARCH_ONLY",
        "artifact_fingerprint": f"fingerprint-{phase}",
    }
    value.update(fields)
    return value


def write_json(path: Path, value: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return path


def patch_roots(monkeypatch, root: Path, *modules: Any) -> None:
    import crypto_decision_lab.scripts.phase316_325_negative_evidence_common as common316
    import crypto_decision_lab.scripts.phase326_335_preregistration_common as common326

    monkeypatch.setattr(common316, "ROOT", root)
    monkeypatch.setattr(common326, "ROOT", root)
    for module in modules:
        monkeypatch.setattr(module, "ROOT", root)


def write_junit(path: Path, tests: int = 10) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'<testsuite name="batch326_335" tests="{tests}" '
        'failures="0" errors="0" skipped="0"></testsuite>\n',
        encoding="utf-8",
    )
    return path


def phase325_fixture() -> dict[str, Any]:
    return payload(
        325,
        global_full_suite={
            "passed": True,
            "test_file_count": 564,
            "totals": {
                "tests": 1471,
                "failures": 0,
                "errors": 0,
                "skipped": 0,
            },
            "manifest_stable": True,
        },
        new_family_opened=False,
        experiment_budget_opened=False,
        strategy_approved=False,
    )


def accepted_phase327() -> dict[str, Any]:
    return payload(
        327,
        selected_decision="ACCEPT",
        effective_decision=(
            "ACCEPT_QUESTION_ONLY_FOR_PREREGISTRATION_RESEARCH_ONLY"
        ),
        decision_source="EXPLICIT_LOCAL_CONSOLE_INPUT",
        question_accepted_for_preregistration=True,
        question_rejected=False,
    )


def accepted_chain() -> dict[int, dict[str, Any]]:
    return {
        327: accepted_phase327(),
        328: payload(328, family_definition_frozen=True),
        329: payload(
            329,
            target_label_frozen=True,
            target_contract={
                "directional_return_prediction_allowed": False,
            },
        ),
        330: payload(
            330,
            budget_definition_frozen=True,
            maximum_hypothesis_budget=12,
            experiment_budget_opened=False,
        ),
        331: payload(
            331,
            sealed_template_count=12,
            sealed_templates=[],
            registry_open=False,
            active_hypotheses=0,
        ),
        332: payload(
            332,
            statistical_plan_frozen=True,
            statistical_plan={
                "outer_holdout_may_influence_selection": False,
            },
        ),
        333: payload(
            333,
            dry_run_pass=True,
            real_historical_rows_used=0,
            historical_performance_metrics_computed=False,
        ),
        334: payload(334, audit_pass=True),
    }
