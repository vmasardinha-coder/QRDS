from crypto_decision_lab.scripts.phase72_journal_replay_dry_run_engine_research_only import (
    SAMPLE_REPLAY_ENTRIES,
    replay_batch_dry_run,
)
from crypto_decision_lab.scripts.phase73_journal_replay_aggregate_metrics_research_only import (
    READY_GATE,
    aggregate_replay_metrics,
    build_phase73,
)

def test_phase73_aggregates_replay_metrics_descriptive_only():
    replay = replay_batch_dry_run(SAMPLE_REPLAY_ENTRIES)
    metrics = aggregate_replay_metrics(replay)
    assert metrics["metrics_descriptive_only"] is True
    assert metrics["row_count"] == 3
    assert metrics["valid_row_count"] == 3
    assert metrics["active_paper_observation_count"] == 2
    assert metrics["edge_validated"] is False
    assert metrics["shadow_decision_allowed"] is False
    assert metrics["decision_layer_allowed"] is False
    assert metrics["trading_signal_generated"] is False
    assert metrics["recommendation_generated"] is False
    assert metrics["allocation_generated"] is False
    assert metrics["canonical_data_writes"] == 0

def test_phase73_computes_win_loss_counts():
    replay = replay_batch_dry_run(SAMPLE_REPLAY_ENTRIES)
    metrics = aggregate_replay_metrics(replay)
    assert metrics["wins"] == 1
    assert metrics["losses"] == 1
    assert metrics["flats"] == 0
    assert metrics["win_rate_descriptive_only"] == 0.5

def test_phase73_summarizes_by_asset():
    replay = replay_batch_dry_run(SAMPLE_REPLAY_ENTRIES)
    metrics = aggregate_replay_metrics(replay)
    assets = {row["asset"]: row for row in metrics["by_asset"]}
    assert set(assets) == {"BTC", "ETH", "SOL"}
    assert assets["BTC"]["active_paper_observation_count"] == 1
    assert assets["SOL"]["active_paper_observation_count"] == 0

def test_phase73_handles_invalid_rows_without_canonical_writes():
    replay = replay_batch_dry_run(
        SAMPLE_REPLAY_ENTRIES
        + [{"journal_id": "bad", "would_have_action": "buy", "research_only_ack": False}]
    )
    metrics = aggregate_replay_metrics(replay)
    assert metrics["invalid_row_count"] == 1
    assert len(metrics["invalid_rows"]) == 1
    assert metrics["safe_apply_allowed"] is False
    assert metrics["promotion_allowed"] is False
    assert metrics["canonical_data_writes"] == 0

def test_phase73_builds_artifact(tmp_path):
    result = build_phase73(tmp_path / "phase73")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase73" / "phase73_journal_replay_aggregate_metrics.json").exists()
    assert (tmp_path / "phase73" / "phase73_sample_replay_metrics_only.json").exists()
    assert (tmp_path / "phase73" / "index.html").exists()
