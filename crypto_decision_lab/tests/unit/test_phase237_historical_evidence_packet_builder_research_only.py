from __future__ import annotations

from crypto_decision_lab.scripts.phase237_historical_evidence_packet_builder_research_only import (
    build_historical_evidence_packet,
)


def fake_inventory():
    return [
        {
            "phase": phase,
            "reported_phase": phase,
            "relative_path": f"phase{phase}.json",
            "exists": True,
            "sha256": f"{phase:064x}",
            "passed": True,
            "status": "PASS",
            "canonical_data_writes": 0,
            "score": 100 if phase == 224 else None,
        }
        for phase in range(216, 226)
    ]


def test_phase237_historical_packet_passes():
    payload = build_historical_evidence_packet(
        inventory=fake_inventory()
    )
    assert payload["passed"] is True
    assert payload["artifact_count"] == 10
    assert payload["data_trust_validated"] is False
