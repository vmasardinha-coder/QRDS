from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    synthetic_rows,
)
from crypto_decision_lab.scripts.phase207_replay_window_builder_research_only import (
    build_windows,
)


def test_build_windows_is_deterministic_and_walk_forward():
    rows = synthetic_rows(symbols=("BTC-USDT",), rows_per_symbol=240)
    first = build_windows(rows)
    second = build_windows(rows)

    assert first == second
    assert first
    for window in first:
        assert window["train_end_index_exclusive"] == window["test_start_index"]
        assert window["train_end_timestamp"] < window["test_start_timestamp"]
        assert window["train_rows"] == 96
        assert window["test_rows"] == 24
