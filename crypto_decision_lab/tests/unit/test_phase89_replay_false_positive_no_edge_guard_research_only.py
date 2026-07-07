from crypto_decision_lab.scripts.phase89_replay_false_positive_no_edge_guard_research_only import (
    ALLOWED_INTERPRETATIONS,
    FORBIDDEN_ESCALATIONS,
    READY_GATE,
    build_phase89,
    guard_replay_false_positive,
    render_false_positive_guard_html,
)

def test_phase89_forbidden_escalations_include_operational_paths():
    assert "EDGE_VALIDATED" in FORBIDDEN_ESCALATIONS
    assert "TRADING_SIGNAL" in FORBIDDEN_ESCALATIONS
    assert "RECOMMENDATION" in FORBIDDEN_ESCALATIONS
    assert "ALLOCATION" in FORBIDDEN_ESCALATIONS
    assert "CANONICAL_WRITE" in FORBIDDEN_ESCALATIONS

def test_phase89_threshold_pass_stays_research_candidate_only():
    report = guard_replay_false_positive({
        "row_count": 80,
        "invalid_row_count": 0,
        "active_paper_observation_count": 60,
        "outlier_count": 1,
        "asset_abs_pnl_concentration": 0.20,
        "drawdown_like_paper_pnl_sequence": False,
    })
    assert report["guard_status"] == "PASS_RESEARCH_ONLY"
    assert report["interpretation"] == "RESEARCH_CANDIDATE_DESCRIPTIVE_ONLY"
    assert report["interpretation"] in ALLOWED_INTERPRETATIONS
    assert "threshold_pass_is_not_edge_validation" in report["guard_warnings"]
    assert report["edge_validated"] is False
    assert report["edge_operationally_validated"] is False
    assert report["shadow_decision_allowed"] is False
    assert report["decision_layer_allowed"] is False
    assert report["safe_apply_allowed"] is False
    assert report["promotion_allowed"] is False
    assert report["canonical_data_writes"] == 0

def test_phase89_small_sample_is_insufficient_only():
    report = guard_replay_false_positive({
        "row_count": 10,
        "invalid_row_count": 0,
        "active_paper_observation_count": 10,
        "outlier_count": 0,
        "asset_abs_pnl_concentration": 0.10,
        "drawdown_like_paper_pnl_sequence": False,
    })
    assert report["interpretation"] == "INSUFFICIENT_EVIDENCE_RESEARCH_ONLY"
    assert report["edge_validated"] is False
    assert report["decision_layer_allowed"] is False
    assert report["canonical_data_writes"] == 0

def test_phase89_invalid_rows_need_review_only():
    report = guard_replay_false_positive({
        "row_count": 50,
        "invalid_row_count": 1,
        "active_paper_observation_count": 40,
        "outlier_count": 0,
        "asset_abs_pnl_concentration": 0.10,
        "drawdown_like_paper_pnl_sequence": False,
    })
    assert report["interpretation"] == "NEEDS_REVIEW_RESEARCH_ONLY"
    assert report["safe_apply_allowed"] is False
    assert report["promotion_allowed"] is False

def test_phase89_html_contains_no_edge_boundary():
    report = guard_replay_false_positive({
        "row_count": 80,
        "invalid_row_count": 0,
        "active_paper_observation_count": 60,
        "outlier_count": 1,
        "asset_abs_pnl_concentration": 0.20,
        "drawdown_like_paper_pnl_sequence": False,
    })
    html = render_false_positive_guard_html(report)
    assert READY_GATE in html
    assert "Operational: BLOCKED_RESEARCH_ONLY" in html
    assert "false_positive_guard_descriptive_only: True" in html
    assert "safe_apply_allowed: False" in html
    assert "canonical_data_writes: 0" in html
    assert "does not validate edge" in html

def test_phase89_builds_artifact(tmp_path):
    result = build_phase89(tmp_path / "phase89")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase89" / "phase89_replay_false_positive_no_edge_guard.json").exists()
    assert (tmp_path / "phase89" / "phase89_replay_false_positive_no_edge_guard.html").exists()
