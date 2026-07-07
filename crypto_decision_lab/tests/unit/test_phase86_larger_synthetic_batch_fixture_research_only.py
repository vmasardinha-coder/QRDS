from crypto_decision_lab.scripts.phase79_journal_replay_batch_loader_research_only import SAMPLE_BATCH
from crypto_decision_lab.scripts.phase86_larger_synthetic_batch_fixture_research_only import (
    READY_GATE,
    build_larger_synthetic_batch,
    build_larger_synthetic_batch_package,
    build_phase86,
    render_larger_synthetic_batch_fixture_html,
)

def test_phase86_builds_larger_synthetic_batch():
    batch = build_larger_synthetic_batch(multiplier=4)
    assert batch["batch_id"] == "larger-synthetic-batch-phase86-x4"
    assert batch["research_only_ack"] is True
    assert batch["synthetic_fixture"] is True
    assert batch["synthetic_fixture_multiplier"] == 4
    assert len(batch["entries"]) == len(SAMPLE_BATCH["entries"]) * 4
    assert all(entry["synthetic_fixture_row"] is True for entry in batch["entries"])

def test_phase86_rejects_small_multiplier():
    try:
        build_larger_synthetic_batch(multiplier=1)
    except ValueError as exc:
        assert "multiplier must be >= 2" in str(exc)
    else:
        raise AssertionError("expected ValueError")

def test_phase86_builds_package(tmp_path):
    package = build_larger_synthetic_batch_package(tmp_path, multiplier=3)
    assert package["gate"] == READY_GATE
    assert package["larger_synthetic_batch_fixture_descriptive_only"] is True
    assert package["entry_count"] == len(SAMPLE_BATCH["entries"]) * 3
    assert package["batch_validation"]["batch_valid_for_replay_loader"] is True
    assert package["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert package["edge_validated"] is False
    assert package["shadow_decision_allowed"] is False
    assert package["decision_layer_allowed"] is False
    assert package["safe_apply_allowed"] is False
    assert package["canonical_data_writes"] == 0
    assert (tmp_path / "larger_synthetic_batch_phase86.json").exists()
    assert (tmp_path / "phase86_larger_synthetic_batch_fixture.json").exists()
    assert (tmp_path / "batch_report_index.json").exists()

def test_phase86_render_contains_research_locks(tmp_path):
    package = build_larger_synthetic_batch_package(tmp_path, multiplier=2)
    html = render_larger_synthetic_batch_fixture_html(package)
    assert READY_GATE in html
    assert "Operational: BLOCKED_RESEARCH_ONLY" in html
    assert "Full suite: SKIPPED_LOCAL_ECONOMICAL" in html
    assert "safe_apply_allowed: False" in html
    assert "canonical_data_writes: 0" in html
    assert "does not validate edge" in html

def test_phase86_builds_artifact(tmp_path):
    result = build_phase86(tmp_path / "phase86")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
