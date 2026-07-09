from crypto_decision_lab.scripts.phase147_ruin_scenario_model_research_only import (
    READY_GATE,
    build_phase147,
    build_ruin_scenario_model,
    evaluate_ruin_scenario,
)

def test_phase147_model_passes():
    model = build_ruin_scenario_model()
    assert model["gate"] == READY_GATE
    assert model["model_pass"] is True
    assert model["scenario_count"] == 3
    assert model["ruin_hit_count"] == 1
    assert model["decision_valid_count"] == 0
    assert model["position_sizing_export_count"] == 0
    assert model["allocation_export_count"] == 0

def test_phase147_ruin_boundary_hits():
    scenario = {
        "scenario_id": "test",
        "capital_at_risk": 100000.0,
        "loss_fraction": 0.50,
        "ruin_threshold_fraction": 0.50,
    }
    result = evaluate_ruin_scenario(scenario)
    assert result["ruin_hit"] is True
    assert result["remaining_capital"] == 50000.0
    assert result["valid_for_decision"] is False

def test_phase147_non_ruin_does_not_hit():
    scenario = {
        "scenario_id": "test",
        "capital_at_risk": 100000.0,
        "loss_fraction": 0.10,
        "ruin_threshold_fraction": 0.50,
    }
    result = evaluate_ruin_scenario(scenario)
    assert result["ruin_hit"] is False
    assert result["position_sizing_exported"] is False
    assert result["allocation_generated"] is False

def test_phase147_locks_are_closed():
    model = build_ruin_scenario_model()
    assert model["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert model["edge_validated"] is False
    assert model["decision_layer_allowed"] is False
    assert model["safe_apply_allowed"] is False
    assert model["canonical_data_writes"] == 0
    assert model["trading_signal_generated"] is False
    assert model["allocation_generated"] is False

def test_phase147_builds_artifact(tmp_path):
    result = build_phase147(tmp_path / "phase147")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase147" / "phase147_ruin_scenario_model.json").exists()
