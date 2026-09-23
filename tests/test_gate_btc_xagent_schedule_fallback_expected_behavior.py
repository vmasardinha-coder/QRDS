from pathlib import Path


def test_expected_behavior_explicitly_forbids_backfill():
    text = Path('artifacts/gate_btc_2/XAGENT_SCHEDULE_FALLBACK_EXPECTED_BEHAVIOR_20260923.md').read_text()
    assert 'at least 5400 seconds old' in text
    assert 'does not backfill' in text
    assert 'zero scientific/survivor credit' in text
    assert 'no runtime write path' in text
