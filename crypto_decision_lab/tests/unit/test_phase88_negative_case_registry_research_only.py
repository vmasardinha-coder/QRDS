from crypto_decision_lab.scripts.phase88_negative_case_registry_research_only import (
    NEGATIVE_CASES,
    READY_GATE,
    build_negative_case_registry,
    build_phase88,
    evaluate_negative_case,
    render_negative_case_registry_html,
)

def test_phase88_has_negative_cases():
    assert len(NEGATIVE_CASES) >= 5
    assert all(case["must_not_infer_edge"] is True for case in NEGATIVE_CASES)

def test_phase88_evaluates_each_case_as_safe():
    for case in NEGATIVE_CASES:
        result = evaluate_negative_case(case)
        assert result["negative_case_passed"] is True
        assert result["must_not_infer_edge"] is True
        assert result["edge_validated"] is False
        assert result["shadow_decision_allowed"] is False
        assert result["decision_layer_allowed"] is False
        assert result["safe_apply_allowed"] is False
        assert result["promotion_allowed"] is False
        assert result["canonical_data_writes"] == 0

def test_phase88_registry_passes_research_only():
    registry = build_negative_case_registry()
    assert registry["gate"] == READY_GATE
    assert registry["registry_status"] == "PASS_RESEARCH_ONLY"
    assert registry["negative_case_registry_descriptive_only"] is True
    assert registry["failing_case_count"] == 0
    assert registry["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert registry["edge_validated"] is False
    assert registry["decision_layer_allowed"] is False
    assert registry["canonical_data_writes"] == 0

def test_phase88_html_contains_boundaries():
    registry = build_negative_case_registry()
    html = render_negative_case_registry_html(registry)
    assert READY_GATE in html
    assert "Operational: BLOCKED_RESEARCH_ONLY" in html
    assert "negative_case_registry_descriptive_only: True" in html
    assert "safe_apply_allowed: False" in html
    assert "canonical_data_writes: 0" in html
    assert "do not validate edge" in html

def test_phase88_builds_artifact(tmp_path):
    result = build_phase88(tmp_path / "phase88")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase88" / "phase88_negative_case_registry.json").exists()
    assert (tmp_path / "phase88" / "phase88_negative_case_registry.html").exists()
