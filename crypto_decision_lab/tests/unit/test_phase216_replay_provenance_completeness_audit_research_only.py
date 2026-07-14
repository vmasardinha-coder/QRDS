from pathlib import Path

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    locks_copy,
    stable_digest,
    synthetic_rows,
    write_json,
    write_jsonl,
)
from crypto_decision_lab.scripts.phase216_replay_provenance_completeness_audit_research_only import (
    build_phase216,
)


def test_phase216_provenance_completeness(tmp_path: Path):
    rows = synthetic_rows(symbols=("BTC-USDT",), rows_per_symbol=240)
    dataset = tmp_path / "dataset.jsonl"
    write_jsonl(dataset, rows)

    p206 = tmp_path / "p206.json"
    p209 = tmp_path / "p209.json"
    p215 = tmp_path / "p215.json"
    write_json(
        p206,
        {
            "contract_passed": True,
            "dataset": {
                "row_count": len(rows),
                "dataset_digest": stable_digest(rows),
                "normalized_dataset_path": "dataset.jsonl",
                "source_mode": "DETERMINISTIC_FIXTURE_FALLBACK",
            },
        },
    )
    write_json(
        p209,
        {
            "historical_replay_passed": True,
            "replay_digest": "abc",
        },
    )
    write_json(
        p215,
        {
            "window_integration_passed": True,
            "phase_chain_digest": "def",
            "locks": locks_copy(),
        },
    )

    result = build_phase216(
        p206,
        p209,
        p215,
        dataset,
        tmp_path / "phase216.json",
        tmp_path / "phase216.md",
        root=tmp_path,
    )
    assert result["provenance_completeness_passed"] is True
    assert result["completeness_ratio"] == 1.0
    assert result["caps"]["data_trust_validated"] is False
