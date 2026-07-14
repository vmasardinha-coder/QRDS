from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    synthetic_rows,
)
from crypto_decision_lab.scripts.phase208_missing_data_policy_research_only import (
    audit_missing_data,
)


def test_missing_data_policy_keeps_gaps_descriptive():
    rows = synthetic_rows(symbols=("BTC-USDT",), rows_per_symbol=130)
    rows.pop(50)
    audit = audit_missing_data(rows)

    assert audit["duplicate_records"] == 0
    assert audit["large_gaps"] == 1
    assert audit["policy"]["future_fill_allowed"] is False
    assert audit["policy"]["cross_window_fill_allowed"] is False
