from __future__ import annotations

from crypto_decision_lab.scripts.phase236_evidence_admission_contract_registry_research_only import (
    build_evidence_admission_contract_registry,
)


def test_phase236_contract_registry_passes():
    payload = build_evidence_admission_contract_registry()
    assert payload["passed"] is True
    assert payload["criterion_count"] == 10
    assert payload["evidence_admitted"] is False


def test_phase236_locks_remain_closed():
    payload = build_evidence_admission_contract_registry()
    assert payload["locks"]["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert payload["locks"]["canonical_data_writes"] == 0
