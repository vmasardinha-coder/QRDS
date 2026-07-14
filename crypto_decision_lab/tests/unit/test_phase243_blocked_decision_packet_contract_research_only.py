from __future__ import annotations

from crypto_decision_lab.scripts.phase243_blocked_decision_packet_contract_research_only import (
    DECISION_PACKET_FIELDS,
    build_blocked_decision_packet,
    build_blocked_decision_packet_contract,
)


def test_phase243_contract_passes():
    payload = build_blocked_decision_packet_contract()
    assert payload["passed"] is True
    assert payload["fields_complete"] is True
    assert len(payload["decision_packet_fields"]) == 15


def test_phase243_packet_cannot_recommend_or_size_position():
    packet = build_blocked_decision_packet(
        asset="BTC",
        market="RESEARCH_ONLY",
    )
    assert list(packet) == DECISION_PACKET_FIELDS
    assert packet["action"] == "NO_ACTION_RESEARCH_ONLY"
    assert packet["position_size"] == 0
    assert packet["entry"] is None
    assert packet["exit"] is None
    assert packet["stop"] is None
