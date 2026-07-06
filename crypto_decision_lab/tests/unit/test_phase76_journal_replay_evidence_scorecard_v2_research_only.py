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
    compute_quality_flags,
)
from crypto_decision_lab.scripts.phase76_journal_replay_evidence_scorecard_v2_research_only import (
    READY_GATE,
    build_evidence_scorecard,
    build_phase76,
    build_scorecard_from_entries,
)

def test_phase76_builds_scorecard_as_descriptive_only():
    scorecard = build_scorecard_from_entries(SAMPLE_REPLAY_ENTRIES)
    assert scorecard["scorecard_descriptive_only"] is True
    assert scorecard["edge_validated"] is False
    assert scorecard["edge_operationally_validated"] is False
    assert scorecard["shadow_decision_allowed"] is False
    assert scorecard["decision_layer_allowed"] is False
    assert scorecard["trading_signal_generated"] is False
    assert scorecard["recommendation_generated"] is False
    assert scorecard["allocation_generated"] is False
    assert scorecard["operational_decision_allowed"] is False
    assert scorecard["safe_apply_allowed"] is False
    assert scorecard["promotion_allowed"] is False
    assert scorecard["canonical_data_writes"] == 0

def test_phase76_reports_insufficient_evidence_for_sample():
    scorecard = build_scorecard_from_entries(SAMPLE_REPLAY_ENTRIES)
    assert scorecard["evidence_status"] == "INSUFFICIENT_EVIDENCE_RESEARCH_ONLY"
    assert "active_sample_below_minimum_research_threshold" in scorecard["blockers_to_edge"]
    assert "descriptive_replay_is_not_edge_validation" in scorecard["blockers_to_edge"]

def test_phase76_composes_existing_replay_layers():
    replay = replay_batch_dry_run(SAMPLE_REPLAY_ENTRIES)
    metrics = aggregate_replay_metrics(replay)
    diagnostics = replay_distribution_diagnostics(replay)
    quality = compute_quality_flags(metrics, diagnostics)
    scorecard = build_evidence_scorecard(replay, metrics, diagnostics, quality)
    assert scorecard["row_count"] == replay["row_count"]
    assert scorecard["total_paper_pnl"] == metrics["total_paper_pnl"]
    assert scorecard["outlier_count"] == diagnostics["outlier_count"]
    assert scorecard["quality_flag_count"] == quality["flag_count"]
    assert scorecard["canonical_data_writes"] == 0

def test_phase76_handles_better_descriptive_sample_without_unlocking_edge():
    entries = []
    for i in range(31):
        entries.append({
            "journal_id": f"sample-{i}",
            "asset": "BTC" if i % 2 == 0 else "ETH",
            "would_have_action": "paper_long",
            "paper_size_notional": 1000.0,
            "entry_reference_price": 100.0,
            "exit_reference_price": 100.1,
            "fees_slippage_bps": 0.0,
            "research_only_ack": True,
        })
    scorecard = build_scorecard_from_entries(entries)
    assert scorecard["active_paper_observation_count"] == 31
    assert scorecard["edge_validated"] is False
    assert scorecard["decision_layer_allowed"] is False
    assert scorecard["canonical_data_writes"] == 0
    assert "descriptive_replay_is_not_edge_validation" in scorecard["blockers_to_edge"]

def test_phase76_builds_artifact(tmp_path):
    result = build_phase76(tmp_path / "phase76")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase76" / "phase76_journal_replay_evidence_scorecard_v2.json").exists()
    assert (tmp_path / "phase76" / "phase76_sample_evidence_scorecard_only.json").exists()
    assert (tmp_path / "phase76" / "index.html").exists()
