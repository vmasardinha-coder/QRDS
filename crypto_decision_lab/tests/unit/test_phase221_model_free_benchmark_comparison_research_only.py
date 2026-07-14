from pathlib import Path

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    synthetic_rows,
    write_json,
    write_jsonl,
)
from crypto_decision_lab.scripts.phase207_replay_window_builder_research_only import (
    build_windows,
)
from crypto_decision_lab.scripts.phase221_model_free_benchmark_comparison_research_only import (
    build_phase221,
)


def test_phase221_compares_three_model_free_baselines(tmp_path: Path):
    rows = synthetic_rows(symbols=("BTC-USDT",), rows_per_symbol=480)
    dataset = tmp_path / "dataset.jsonl"
    p207 = tmp_path / "p207.json"
    p209 = tmp_path / "p209.json"
    p220 = tmp_path / "p220.json"
    write_jsonl(dataset, rows)
    write_json(p207, {"windows": build_windows(rows)})
    write_json(p209, {"historical_replay_passed": True})
    write_json(p220, {"robustness_checkpoint_passed": True})

    result = build_phase221(
        p207,
        p209,
        p220,
        dataset,
        tmp_path / "phase221.json",
        tmp_path / "phase221.md",
        root=tmp_path,
    )
    assert result["benchmark_comparison_passed"] is True
    assert len(result["comparison"]["benchmarks"]) == 3
    assert result["winner_claim_allowed"] is False
