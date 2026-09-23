from pathlib import Path


def test_final_scope_remains_operational_only():
    text = Path('artifacts/gate_btc_2/XAGENT_SCHEDULE_FALLBACK_FINAL_SCOPE_20260923.txt').read_text()
    for phrase in ['No science change', 'No backfill', 'No retune', 'No engine feed', 'No orders', 'No capital']:
        assert phrase in text
