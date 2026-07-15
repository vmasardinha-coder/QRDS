from crypto_decision_lab.scripts import phase311_candidate_eligibility_contract_v2_research_only as module
from tests.unit._phase306_315_fixtures import patch_roots, payload, phase304_payload, write_json


def test_phase311_candidate_eligibility_contract_blocks_failed_gates(monkeypatch, tmp_path):
    patch_roots(monkeypatch, tmp_path, module)
    p304 = write_json(tmp_path / "artifacts/phase304.json", phase304_payload())
    p306 = write_json(tmp_path / "artifacts/phase306.json", payload(306, temporal_stability_pass=False, failure_reasons=["X"]))
    p307 = write_json(tmp_path / "artifacts/phase307.json", payload(307, regime_concentration_pass=False, failure_reasons=["X"]))
    p308 = write_json(tmp_path / "artifacts/phase308.json", payload(308, dependency_pass=True, failure_reasons=[]))
    p309 = write_json(tmp_path / "artifacts/phase309.json", payload(309, extreme_cost_liquidity_pass=False, failure_reasons=["X"]))
    p310 = write_json(tmp_path / "artifacts/phase310.json", payload(310, timestamp_sensitivity_pass=False, failure_reasons=["X"]))
    result = module.build(p304, p306, p307, p308, p309, p310, tmp_path / "artifacts/phase311")
    assert result["phase"] == 311
    assert result["candidate_eligible"] is False
    assert result["failed_gate_count"] > 0
    assert result["gate_waivers_allowed"] is False
    assert result["freeze_created"] is False
    assert result["strategy_approved"] is False
