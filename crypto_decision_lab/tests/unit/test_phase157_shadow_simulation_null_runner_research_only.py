from crypto_decision_lab.scripts.phase157_shadow_simulation_null_runner_research_only import (
    READY_GATE,
    build_phase157,
    build_shadow_simulation_null_runner,
    run_shadow_null_simulation,
)

def test_phase157_runner_passes():
    runner = build_shadow_simulation_null_runner()
    assert runner["gate"] == READY_GATE
    assert runner["runner_pass"] is True
    assert runner["null_fields_ok"] is True
    assert runner["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase157_null_run_outputs_no_decision():
    run = run_shadow_null_simulation({"simulation_id": "x", "candidate_id": "y"})
    assert run["decision"] is None
    assert run["recommendation"] is None
    assert run["trading_signal"] is None
    assert run["allocation"] is None
    assert run["position_size"] is None
    assert run["order_payload"] is None
    assert run["safe_apply_payload"] is None

def test_phase157_null_run_flags_are_blocked():
    run = run_shadow_null_simulation({"simulation_id": "x"})
    assert run["shadow_decision_emitted"] is False
    assert run["decision_layer_allowed"] is False
    assert run["trading_signal_generated"] is False
    assert run["recommendation_generated"] is False
    assert run["allocation_generated"] is False
    assert run["order_payload_generated"] is False
    assert run["safe_apply_allowed"] is False
    assert run["canonical_data_writes"] == 0

def test_phase157_locks_are_closed():
    runner = build_shadow_simulation_null_runner()
    assert runner["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert runner["shadow_decision_allowed"] is False
    assert runner["decision_layer_allowed"] is False
    assert runner["safe_apply_allowed"] is False
    assert runner["canonical_data_writes"] == 0
    assert runner["trading_signal_generated"] is False
    assert runner["recommendation_generated"] is False
    assert runner["allocation_generated"] is False

def test_phase157_builds_artifact(tmp_path):
    result = build_phase157(tmp_path / "phase157")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase157" / "phase157_shadow_simulation_null_runner.json").exists()
