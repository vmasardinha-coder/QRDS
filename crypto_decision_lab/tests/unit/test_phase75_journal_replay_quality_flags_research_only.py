from crypto_decision_lab.scripts.phase72_journal_replay_dry_run_engine_research_only import (
    SAMPLE_REPLAY_ENTRIES,
    replay_batch_dry_run,
)
from crypto_decision_lab.scripts.phase73_journal_replay_aggregate_metrics_research_only import (
    aggregate_replay_metrics,
)
from crypto_decision_lab.scripts.phase74_journal_replay_distribution_diagnostics_research_only import (
    replay_distribution_diagnostics,
)
from crypto_decision_lab.scripts.phase75_journal_replay_quality_flags_research_only import (
    READY_GATE,
    build_phase75,
    compute_quality_flags,
)

def _sample_quality():
    replay = replay_batch_dry_run(SAMPLE_REPLAY_ENTRIES)
    metrics = aggregate_replay_metrics(replay)
    diagnostics = replay_distribution_diagnostics(replay)
    return compute_quality_flags(metrics, diagnostics)

def test_phase75_quality_flags_are_descriptive_only():
    quality = _sample_quality()
    assert quality["quality_flags_descriptive_only"] is True
    assert quality["edge_validated"] is False
    assert quality["edge_operationally_validated"] is False
    assert quality["shadow_decision_allowed"] is False
    assert quality["decision_layer_allowed"] is False
    assert quality["trading_signal_generated"] is False
    assert quality["recommendation_generated"] is False
    assert quality["allocation_generated"] is False
    assert quality["safe_apply_allowed"] is False
    assert quality["promotion_allowed"] is False
    assert quality["canonical_data_writes"] == 0

def test_phase75_flags_small_sample_and_not_edge():
    quality = _sample_quality()
    flags = {item["flag"] for item in quality["flags"]}
    assert "sample_too_small" in flags
    assert "metrics_not_edge_evidence" in flags
    assert quality["quality_status"] == "NEEDS_MORE_EVIDENCE_RESEARCH_ONLY"

def test_phase75_flags_invalid_rows():
    replay = replay_batch_dry_run(
        SAMPLE_REPLAY_ENTRIES
        + [{"journal_id": "bad", "would_have_action": "buy", "research_only_ack": False}]
    )
    metrics = aggregate_replay_metrics(replay)
    diagnostics = replay_distribution_diagnostics(replay)
    quality = compute_quality_flags(metrics, diagnostics)
    flags = {item["flag"] for item in quality["flags"]}
    assert "invalid_rows_present" in flags
    assert quality["canonical_data_writes"] == 0

def test_phase75_can_pass_descriptive_quality_without_medium_high_flags():
    metrics = {
        "active_paper_observation_count": 31,
        "invalid_row_count": 0,
    }
    diagnostics = {
        "outlier_count": 0,
        "drawdown_like_paper_pnl_sequence": 0.0,
        "asset_abs_pnl_concentration": [
            {"asset": "BTC", "abs_pnl_share": 0.5},
            {"asset": "ETH", "abs_pnl_share": 0.5},
        ],
    }
    quality = compute_quality_flags(metrics, diagnostics)
    assert quality["quality_status"] == "DESCRIPTIVE_OK_RESEARCH_ONLY"
    assert quality["high_flag_count"] == 0
    assert quality["medium_flag_count"] == 0
    assert quality["info_flag_count"] == 1
    assert quality["edge_validated"] is False

def test_phase75_builds_artifact(tmp_path):
    result = build_phase75(tmp_path / "phase75")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase75" / "phase75_journal_replay_quality_flags.json").exists()
    assert (tmp_path / "phase75" / "phase75_sample_quality_flags_only.json").exists()
    assert (tmp_path / "phase75" / "index.html").exists()
