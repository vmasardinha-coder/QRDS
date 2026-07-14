from pathlib import Path
from crypto_decision_lab.scripts.phase205_full_integration_tracking_checkpoint_research_only import build_manifest, split_shards


def test_phase205_manifest_and_shards_are_deterministic(tmp_path: Path, monkeypatch) -> None:
    files = []
    for index in range(7):
        path = tmp_path / f"test_{index}.py"; path.write_text(f"# {index}\n"); files.append(path)
    first = split_shards(files, 3)
    second = split_shards(files, 3)
    assert first == second
    assert sum(len(shard) for shard in first) == 7
    assert max(len(shard) for shard in first) - min(len(shard) for shard in first) <= 1
