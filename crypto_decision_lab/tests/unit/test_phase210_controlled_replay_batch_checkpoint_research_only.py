from pathlib import Path

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    write_json,
)
from crypto_decision_lab.scripts.phase210_controlled_replay_batch_checkpoint_research_only import (
    build_phase210,
)


def test_phase210_requires_all_pipeline_checks(tmp_path: Path):
    inputs = []
    payloads = [
        {"contract_passed": True, "dataset": {"dataset_digest": "a"}},
        {"window_builder_passed": True, "window_manifest_digest": "b"},
        {
            "missing_data_policy_passed": True,
            "audit": {"duplicate_records": 0},
        },
        {
            "historical_replay_passed": True,
            "deterministic_replay": True,
            "replay_digest": "c",
        },
    ]
    for index, payload in enumerate(payloads, start=206):
        path = tmp_path / f"phase{index}.json"
        write_json(path, payload)
        inputs.append(path)

    output = tmp_path / "phase210.json"
    documentation = tmp_path / "phase210.md"
    result = build_phase210(
        *inputs,
        output,
        documentation,
        root=tmp_path,
    )

    assert result["checkpoint_passed"] is True
    assert result["locks"]["decision_layer_allowed"] is False
