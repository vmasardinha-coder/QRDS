from pathlib import Path


def test_xagent_fallback_validation_workflow_covers_boundary_tests():
    text = Path('.github/workflows/gate-btc-xagent-schedule-fallback-validation.yml').read_text()
    assert 'tests/test_gate_btc_xagent_schedule_fallback_boundary.py' in text
    assert 'tests/test_gate_btc_xagent_schedule_fallback_scope.py' in text
    assert 'tests/test_gate_btc_xagent_schedule_fallback_workflow.py' in text
    assert "ENGINE_FEED: 'false'" in text
    assert "NO_BACKFILL: 'true'" in text
