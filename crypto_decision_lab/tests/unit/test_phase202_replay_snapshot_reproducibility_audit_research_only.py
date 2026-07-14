from pathlib import Path
import json
from crypto_decision_lab.scripts.phase201_deterministic_shadow_replay_harness_research_only import replay_events
from crypto_decision_lab.scripts.phase202_replay_snapshot_reproducibility_audit_research_only import build_phase202


def test_phase202_repeated_runs_match(tmp_path: Path) -> None:
    events = [{"timestamp": "2026-01-01T00:00:00Z", "value": 1.0}, {"timestamp": "2026-01-01T00:01:00Z", "value": 2.0}]
    source = {"phase": 201, **replay_events(events)}
    path = tmp_path / "p201.json"; path.write_text(json.dumps(source))
    result = build_phase202(path, tmp_path / "out", runs=4)
    assert result["reproducible"] is True
    assert result["unique_checksum_count"] == 1
    assert result["valid_for_decision"] is False
