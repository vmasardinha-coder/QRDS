from __future__ import annotations

from crypto_decision_lab.scripts.phase242_economic_edge_acceptance_protocol_research_only import (
    build_economic_edge_acceptance_protocol,
)


def test_phase242_protocol_passes_without_claiming_edge():
    payload = build_economic_edge_acceptance_protocol()
    assert payload["passed"] is True
    assert payload["protocol_ready"] is True
    assert payload["edge_validated"] is False


def test_phase242_requires_net_cost_model():
    requirements = build_economic_edge_acceptance_protocol()["requirements"]
    assert requirements["fees_included"] is True
    assert requirements["spread_included"] is True
    assert requirements["slippage_included"] is True
    assert requirements["latency_included"] is True
