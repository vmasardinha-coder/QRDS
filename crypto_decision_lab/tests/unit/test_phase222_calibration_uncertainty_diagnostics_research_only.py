from pathlib import Path

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    synthetic_rows,
    write_json,
    write_jsonl,
)
from crypto_decision_lab.scripts.phase207_replay_window_builder_research_only import (
    build_windows,
)
from crypto_decision_lab.scripts.phase222_calibration_uncertainty_diagnostics_research_only import (
    build_phase222,
)


def test_phase222_reports_uncertainty_without_validating_calibration(tmp_path: Path):
    rows = synthetic_rows(symbols=("BTC-USDT",), rows_per_symbol=480)
    dataset = tmp_path / "dataset.jsonl"
    p207 = tmp_path / "p207.json"
    p221 = tmp_path / "p221.json"
    write_jsonl(dataset, rows)
    write_json(p207, {"windows": build_windows(rows)})
    write_json(p221, {"benchmark_comparison_passed": True})

    result = build_phase222(
        p207,
        p221,
        dataset,
        tmp_path / "phase222.json",
        tmp_path / "phase222.md",
        root=tmp_path,
    )
    assert result["calibration_diagnostic_passed"] is True
    assert 0.0 <= result["diagnostic"]["empirical_coverage"] <= 1.0
    assert result["calibration_validated"] is False
