from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    stable_digest,
    synthetic_rows,
)
from crypto_decision_lab.scripts.phase207_replay_window_builder_research_only import (
    build_windows,
)
from crypto_decision_lab.scripts.phase209_historical_replay_runner_research_only import (
    run_replay,
)


def test_replay_is_deterministic_and_causal():
    rows = synthetic_rows(symbols=("BTC-USDT",), rows_per_symbol=240)
    windows = build_windows(rows)
    first = run_replay(rows, windows)
    second = run_replay(rows, windows)

    assert stable_digest(first) == stable_digest(second)
    assert first
    for result in first:
        assert result["test_rows"] == 24
        for trace in result["traces"]:
            assert trace["feature_timestamp"] < trace["target_timestamp"]
