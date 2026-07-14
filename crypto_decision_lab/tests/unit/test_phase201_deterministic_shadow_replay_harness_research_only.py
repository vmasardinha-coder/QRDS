from crypto_decision_lab.scripts.phase201_deterministic_shadow_replay_harness_research_only import replay_events


def test_phase201_replay_is_deterministic_and_non_operational() -> None:
    events = [{"timestamp": "2026-01-01T00:00:00Z", "source_id": "x", "value": 1.0}]
    first = replay_events(events)
    second = replay_events(events)
    assert first == second
    assert first["trace"][0]["decision_emitted"] is False
    assert first["trace"][0]["order_emitted"] is False


def test_phase201_checksum_changes_with_input() -> None:
    a = replay_events([{"timestamp": "2026-01-01T00:00:00Z", "value": 1.0}])
    b = replay_events([{"timestamp": "2026-01-01T00:00:00Z", "value": 2.0}])
    assert a["replay_checksum"] != b["replay_checksum"]
