from crypto_decision_lab.scripts.phase87_replay_evidence_threshold_registry_research_only import (
    READY_GATE,
    THRESHOLD_REGISTRY,
    build_phase87,
    evaluate_replay_evidence_thresholds,
    render_threshold_registry_html,
)

def test_phase87_registry_has_research_only_boundaries():
    assert THRESHOLD_REGISTRY["registry_descriptive_only"] is True
    assert THRESHOLD_REGISTRY["threshold_pass_does_not_validate_edge"] is True
    assert "EDGE_VALIDATED" in THRESHOLD_REGISTRY["forbidden_interpretations"]
    assert "TRADING_SIGNAL" in THRESHOLD_REGISTRY["forbidden_interpretations"]
    assert "CANONICAL_WRITE" in THRESHOLD_REGISTRY["forbidden_interpretations"]

def test_phase87_insufficient_sample_status():
    result = evaluate_replay_evidence_thresholds({
        "row_count": 10,
        "invalid_row_count": 0,
        "active_paper_observation_count": 10,
        "outlier_count": 0,
        "asset_abs_pnl_concentration": 0.10,
        "drawdown_like_paper_pnl_sequence": False,
    })
    assert result["threshold_status"] == "INSUFFICIENT_SAMPLE_RESEARCH_ONLY"
    assert "minimum_active_paper_observations_not_met" in result["blockers"]
    assert result["edge_validated"] is False
    assert result["decision_layer_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase87_invalid_rows_need_review():
    result = evaluate_replay_evidence_thresholds({
        "row_count": 50,
        "invalid_row_count": 1,
        "active_paper_observation_count": 40,
        "outlier_count": 0,
        "asset_abs_pnl_concentration": 0.10,
        "drawdown_like_paper_pnl_sequence": False,
    })
    assert result["threshold_status"] == "NEEDS_REVIEW_RESEARCH_ONLY"
    assert "invalid_row_rate_above_threshold" in result["blockers"]
    assert result["safe_apply_allowed"] is False

def test_phase87_threshold_pass_still_does_not_validate_edge():
    result = evaluate_replay_evidence_thresholds({
        "row_count": 60,
        "invalid_row_count": 0,
        "active_paper_observation_count": 50,
        "outlier_count": 1,
        "asset_abs_pnl_concentration": 0.20,
        "drawdown_like_paper_pnl_sequence": False,
    })
    assert result["threshold_status"] == "RESEARCH_CANDIDATE_THRESHOLD_PASS_DESCRIPTIVE_ONLY"
    assert result["threshold_pass_does_not_validate_edge"] is True
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase87_html_contains_locks():
    result = evaluate_replay_evidence_thresholds({
        "row_count": 60,
        "invalid_row_count": 0,
        "active_paper_observation_count": 50,
        "outlier_count": 1,
        "asset_abs_pnl_concentration": 0.20,
        "drawdown_like_paper_pnl_sequence": False,
    })
    html = render_threshold_registry_html(result)
    assert READY_GATE in html
    assert "Operational: BLOCKED_RESEARCH_ONLY" in html
    assert "safe_apply_allowed: False" in html
    assert "canonical_data_writes: 0" in html
    assert "Passing thresholds does not validate edge" in html

def test_phase87_builds_artifact(tmp_path):
    result = build_phase87(tmp_path / "phase87")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase87" / "phase87_replay_evidence_threshold_registry.json").exists()
    assert (tmp_path / "phase87" / "phase87_replay_evidence_threshold_registry.html").exists()
