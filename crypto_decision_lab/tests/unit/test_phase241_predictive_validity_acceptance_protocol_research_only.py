from __future__ import annotations

from crypto_decision_lab.scripts.phase241_predictive_validity_acceptance_protocol_research_only import (
    build_predictive_validity_acceptance_protocol,
)


def test_phase241_protocol_passes():
    payload = build_predictive_validity_acceptance_protocol()
    assert payload["passed"] is True
    assert payload["protocol_ready"] is True
    assert payload["predictive_validity_established"] is False


def test_phase241_requires_zero_lookahead_leakage():
    payload = build_predictive_validity_acceptance_protocol()
    assert payload["requirements"]["lookahead_leakage_tolerance"] == 0
    assert payload["requirements"]["minimum_independent_windows"] >= 3
