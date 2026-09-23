from pathlib import Path


def test_implementation_note_keeps_existing_transform_canonical():
    text = Path('artifacts/gate_btc_2/XAGENT_SCHEDULE_FALLBACK_IMPLEMENTATION_NOTE_20260923.md').read_text()
    assert 'sole source of feature computation and persistence' in text
    assert '5400 seconds' in text
    assert 'gate-btc-xagent-disagree-transform.yml' in text
