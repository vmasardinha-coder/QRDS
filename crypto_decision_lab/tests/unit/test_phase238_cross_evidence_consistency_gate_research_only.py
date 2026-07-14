from __future__ import annotations

from crypto_decision_lab.scripts.phase238_cross_evidence_consistency_gate_research_only import (
    build_cross_evidence_consistency_gate,
)


def test_phase238_consistency_gate_passes():
    inventory = [
        {
            "phase": phase,
            "sha256": f"{phase:064x}",
            "passed": True,
            "status": "PASS",
            "canonical_data_writes": 0,
            "score": 100 if phase == 224 else None,
        }
        for phase in range(216, 226)
    ]
    payload = build_cross_evidence_consistency_gate(
        {"inventory": inventory}
    )
    assert payload["passed"] is True
    assert payload["unique_artifact_hashes"] == 10
    assert payload["data_trust_validated"] is False
