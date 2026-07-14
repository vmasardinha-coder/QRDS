from pathlib import Path

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    synthetic_rows,
    write_json,
    write_jsonl,
)
from crypto_decision_lab.scripts.phase217_multi_source_agreement_diagnostics_research_only import (
    build_phase217,
    diagnose_agreement,
)


def test_phase217_derived_views_are_not_independent_sources():
    diagnostic = diagnose_agreement(
        synthetic_rows(symbols=("BTC-USDT",), rows_per_symbol=20)
    )
    assert diagnostic["view_count"] == 3
    assert diagnostic["independent_source_count"] == 0
    assert 0.0 <= diagnostic["agreement_ratio"] <= 1.0


def test_phase217_build_preserves_data_trust_cap(tmp_path: Path):
    rows = synthetic_rows(symbols=("BTC-USDT",), rows_per_symbol=240)
    dataset = tmp_path / "dataset.jsonl"
    phase216 = tmp_path / "phase216.json"
    write_jsonl(dataset, rows)
    write_json(phase216, {"provenance_completeness_passed": True})

    result = build_phase217(
        phase216,
        dataset,
        tmp_path / "phase217.json",
        tmp_path / "phase217.md",
        root=tmp_path,
    )
    assert result["multi_source_agreement_diagnostic_passed"] is True
    assert result["independent_source_agreement_validated"] is False
    assert result["caps"]["data_trust_validated"] is False
