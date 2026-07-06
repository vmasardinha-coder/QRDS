from crypto_decision_lab.scripts.phase72_journal_replay_dry_run_engine_research_only import (
    SAMPLE_REPLAY_ENTRIES,
    replay_batch_dry_run,
)
from crypto_decision_lab.scripts.phase74_journal_replay_distribution_diagnostics_research_only import (
    READY_GATE,
    build_phase74,
    replay_distribution_diagnostics,
)

def test_phase74_distribution_diagnostics_are_descriptive_only():
    replay = replay_batch_dry_run(SAMPLE_REPLAY_ENTRIES)
    diagnostics = replay_distribution_diagnostics(replay)
    assert diagnostics["distribution_diagnostics_descriptive_only"] is True
    assert diagnostics["active_paper_observation_count"] == 2
    assert diagnostics["positive_count"] == 1
    assert diagnostics["negative_count"] == 1
    assert diagnostics["edge_validated"] is False
    assert diagnostics["shadow_decision_allowed"] is False
    assert diagnostics["decision_layer_allowed"] is False
    assert diagnostics["trading_signal_generated"] is False
    assert diagnostics["recommendation_generated"] is False
    assert diagnostics["allocation_generated"] is False
    assert diagnostics["canonical_data_writes"] == 0

def test_phase74_computes_distribution_stats():
    replay = replay_batch_dry_run(SAMPLE_REPLAY_ENTRIES)
    diagnostics = replay_distribution_diagnostics(replay)
    assert diagnostics["max_paper_return_pct"] > diagnostics["min_paper_return_pct"]
    assert diagnostics["mean_paper_pnl"] != 0
    assert diagnostics["median_paper_pnl"] != 0
    assert isinstance(diagnostics["drawdown_like_paper_pnl_sequence"], float)

def test_phase74_computes_asset_concentration():
    replay = replay_batch_dry_run(SAMPLE_REPLAY_ENTRIES)
    diagnostics = replay_distribution_diagnostics(replay)
    assets = {row["asset"] for row in diagnostics["asset_abs_pnl_concentration"]}
    assert assets == {"BTC", "ETH"}
    total_share = sum(row["abs_pnl_share"] for row in diagnostics["asset_abs_pnl_concentration"])
    assert 0.99 <= total_share <= 1.01

def test_phase74_handles_empty_active_rows():
    replay = replay_batch_dry_run([
        {
            "journal_id": "watch-only",
            "asset": "BTC",
            "would_have_action": "watch",
            "paper_size_notional": 0.0,
            "entry_reference_price": 100.0,
            "exit_reference_price": 101.0,
            "research_only_ack": True,
        }
    ])
    diagnostics = replay_distribution_diagnostics(replay)
    assert diagnostics["active_paper_observation_count"] == 0
    assert diagnostics["mean_paper_return_pct"] == 0.0
    assert diagnostics["canonical_data_writes"] == 0
    assert diagnostics["safe_apply_allowed"] is False

def test_phase74_builds_artifact(tmp_path):
    result = build_phase74(tmp_path / "phase74")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase74" / "phase74_journal_replay_distribution_diagnostics.json").exists()
    assert (tmp_path / "phase74" / "phase74_sample_distribution_diagnostics_only.json").exists()
    assert (tmp_path / "phase74" / "index.html").exists()
