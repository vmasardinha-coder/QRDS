from pathlib import Path

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    synthetic_rows,
    write_json,
    write_jsonl,
)
from crypto_decision_lab.scripts.phase207_replay_window_builder_research_only import (
    build_windows,
)
from crypto_decision_lab.scripts.phase219_window_boundary_perturbation_audit_research_only import (
    build_phase219,
)


def test_phase219_perturbs_boundaries_without_leakage(tmp_path: Path):
    rows = synthetic_rows(symbols=("BTC-USDT",), rows_per_symbol=480)
    dataset = tmp_path / "dataset.jsonl"
    p207 = tmp_path / "p207.json"
    p209 = tmp_path / "p209.json"
    p218 = tmp_path / "p218.json"
    write_jsonl(dataset, rows)
    write_json(p207, {"windows": build_windows(rows)})
    write_json(p209, {"historical_replay_passed": True})
    write_json(p218, {"contamination_sensitivity_passed": True})

    result = build_phase219(
        p207,
        p209,
        p218,
        dataset,
        tmp_path / "phase219.json",
        tmp_path / "phase219.md",
        root=tmp_path,
    )
    assert result["window_boundary_perturbation_passed"] is True
    assert result["diagnostic"]["all_cases_nonempty"] is True
    assert len(result["diagnostic"]["cases"]) == 4
