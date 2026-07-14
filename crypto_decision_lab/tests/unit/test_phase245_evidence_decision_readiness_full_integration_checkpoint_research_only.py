from __future__ import annotations

from crypto_decision_lab.scripts.phase245_evidence_decision_readiness_full_integration_checkpoint_research_only import (
    build_phase245_checkpoint,
    tracking_documents,
)


def fake_full_suite():
    return {
        "passed": True,
        "coverage_complete": True,
        "manifest_stable": True,
        "test_file_count": 484,
        "coverage_file_count": 484,
        "totals": {
            "tests": 1390,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
        },
        "recovery_mode": "STANDARD_PYTEST_COVERAGE_RESUME_V10",
    }


def test_phase245_checkpoint_passes():
    artifacts = [
        {"phase": phase, "passed": True}
        for phase in range(236, 245)
    ]
    artifacts[-1].update(
        {
            "framework_score": 100,
            "technical_reliability_score": 100,
            "operational_readiness_score": 0,
            "classification": (
                "PRODUCT_DECISION_FRAMEWORK_READY_"
                "EVIDENCE_NOT_VALIDATED"
            ),
        }
    )
    payload = build_phase245_checkpoint(
        artifacts,
        fake_full_suite(),
    )
    assert payload["passed"] is True
    assert payload["global_full_suite_passed"] is True
    assert payload["next_tracking_checkpoint"] == 255
    assert payload["next_mandatory_global_full_suite"] == 265
    assert payload["valid_for_decision"] is False
    assert len(tracking_documents(payload)) == 6
