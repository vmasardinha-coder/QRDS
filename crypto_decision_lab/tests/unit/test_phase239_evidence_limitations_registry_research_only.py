from __future__ import annotations

from crypto_decision_lab.scripts.phase239_evidence_limitations_registry_research_only import (
    build_evidence_limitations_registry,
)


def test_phase239_limitations_are_explicit_and_blocking():
    payload = build_evidence_limitations_registry()
    assert payload["passed"] is True
    assert payload["blocking_limitation_count"] == 6
    assert payload["evidence_admitted"] is False
