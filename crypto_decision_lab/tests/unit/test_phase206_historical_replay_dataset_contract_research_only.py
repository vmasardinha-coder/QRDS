from pathlib import Path

from crypto_decision_lab.scripts import (
    phase206_historical_replay_dataset_contract_research_only as phase206,
)
from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    synthetic_rows,
)


def test_synthetic_rows_are_deterministic_and_ordered():
    first = synthetic_rows(rows_per_symbol=130)
    second = synthetic_rows(rows_per_symbol=130)
    assert first == second
    assert len(first) == 390
    assert first[0]["timestamp"] < first[1]["timestamp"]


def test_phase206_builds_contract_from_fixture(tmp_path: Path):
    artifact = tmp_path / "artifacts" / "phase206.json"
    dataset = tmp_path / "artifacts" / "dataset.jsonl"
    documentation = tmp_path / "docs" / "phase206.md"

    payload = phase206.build_phase206(
        artifact,
        dataset,
        documentation,
        root=tmp_path,
    )

    assert payload["contract_passed"] is True
    assert payload["dataset"]["source_mode"] == (
        "DETERMINISTIC_FIXTURE_FALLBACK"
    )
    assert dataset.is_file()
    assert documentation.is_file()
    assert payload["locks"]["canonical_data_writes"] == 0
