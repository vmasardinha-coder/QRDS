from __future__ import annotations

from crypto_decision_lab.scripts.phase240_evidence_admission_checkpoint_research_only import (
    build_evidence_admission_checkpoint,
)


def test_phase240_framework_passes_without_admitting_data():
    artifacts = [
        {"phase": 236, "passed": True},
        {"phase": 237, "passed": True},
        {"phase": 238, "passed": True},
        {
            "phase": 239,
            "passed": True,
            "blocking_limitation_count": 6,
        },
    ]
    payload = build_evidence_admission_checkpoint(artifacts)
    assert payload["passed"] is True
    assert payload["evidence_admitted"] is False
    assert payload["classification"] == (
        "EVIDENCE_ADMISSION_FRAMEWORK_READY_DATA_NOT_ADMITTED"
    )
