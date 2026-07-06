from pathlib import Path

from crypto_decision_lab.scripts.phase53_shadow_journal_replay_metrics_research_only import (
    READY_GATE,
    SAMPLE_REPLAYS,
    build_phase53,
    compute_replay_metrics,
)

def test_phase53_compute_metrics():
    metrics = compute_replay_metrics(SAMPLE_REPLAYS)
    assert metrics["replay_count"] == 5
    assert metrics["paper_win_count"] == 2
    assert metrics["paper_loss_count"] == 2
    assert metrics["paper_flat_count"] == 1
    assert metrics["paper_win_rate"] == 0.4

def test_phase53_shadow_journal_replay_metrics_builds(tmp_path):
    result = build_phase53(tmp_path / "phase53")
    out = Path(tmp_path / "phase53")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert result["page_count"] == 5
    assert result["sample_replay_count"] == 5
    for name in [
        "index.html",
        "sample_replay.html",
        "metric_definitions.html",
        "bias_review.html",
        "safety_boundaries.html",
        "phase53_sample_replay.csv",
        "phase53_metric_definitions.csv",
        "phase53_shadow_journal_replay_metrics.json",
        "phase53_checksums.json",
    ]:
        assert (out / name).exists(), name
