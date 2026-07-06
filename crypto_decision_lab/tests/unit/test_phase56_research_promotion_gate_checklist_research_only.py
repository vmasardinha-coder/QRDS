from pathlib import Path

from crypto_decision_lab.scripts.phase56_research_promotion_gate_checklist_research_only import (
    GATE_CHECKS,
    READY_GATE,
    build_phase56,
    evaluate_promotion_gates,
)

def test_phase56_promotion_gates_remain_blocked():
    result = evaluate_promotion_gates(GATE_CHECKS)
    assert result["promotion_allowed"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["edge_validated"] is False
    assert result["not_met_count"] >= 1
    assert result["all_required_met"] is False

def test_phase56_research_promotion_gate_checklist_builds(tmp_path):
    result = build_phase56(tmp_path / "phase56")
    out = Path(tmp_path / "phase56")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert result["gate_check_count"] >= 7
    assert result["gate_evaluation"]["not_met_count"] >= 1
    for name in [
        "index.html",
        "gate_checklist.html",
        "blocker_summary.html",
        "future_path.html",
        "safety_boundaries.html",
        "phase56_promotion_gate_checklist.csv",
        "phase56_research_promotion_gate_checklist.json",
        "phase56_checksums.json",
    ]:
        assert (out / name).exists(), name
