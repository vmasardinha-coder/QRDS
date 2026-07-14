from pathlib import Path

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    synthetic_rows,
    write_json,
    write_jsonl,
)
from crypto_decision_lab.scripts.phase218_outlier_contamination_sensitivity_research_only import (
    build_phase218,
)


def test_phase218_detects_injected_contamination(tmp_path: Path):
    rows = synthetic_rows(symbols=("BTC-USDT",), rows_per_symbol=480)
    dataset = tmp_path / "dataset.jsonl"
    p217 = tmp_path / "p217.json"
    write_jsonl(dataset, rows)
    write_json(p217, {"multi_source_agreement_diagnostic_passed": True})

    result = build_phase218(
        p217,
        dataset,
        tmp_path / "phase218.json",
        tmp_path / "phase218.md",
        root=tmp_path,
    )
    assert result["contamination_sensitivity_passed"] is True
    assert result["sensitivity"]["detector_recall"] >= 0.875
    assert result["locks"]["canonical_data_writes"] == 0
