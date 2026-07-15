from crypto_decision_lab.scripts import phase314_scientific_decision_portal_research_only as module
from tests.unit._phase306_315_fixtures import patch_roots, payload, phase304_payload, write_json


def test_phase314_portal_has_required_plain_language_blocks(monkeypatch, tmp_path):
    patch_roots(monkeypatch, tmp_path, module)
    p304 = write_json(tmp_path / "artifacts/phase304.json", phase304_payload())
    p306 = write_json(tmp_path / "artifacts/phase306.json", payload(306, temporal_stability_pass=False))
    p307 = write_json(tmp_path / "artifacts/phase307.json", payload(307, regime_concentration_pass=False))
    p308 = write_json(tmp_path / "artifacts/phase308.json", payload(308, dependency_pass=True))
    p309 = write_json(tmp_path / "artifacts/phase309.json", payload(309, extreme_cost_liquidity_pass=False))
    p310 = write_json(tmp_path / "artifacts/phase310.json", payload(310, timestamp_sensitivity_pass=False))
    gates = [{"gate_id": "G01", "passed": False, "label": "test", "failure_code": "FAIL", "waiver_allowed": False}]
    p311 = write_json(
        tmp_path / "artifacts/phase311.json",
        payload(
            311,
            candidate_hypothesis_id="OI_MOM_H8_T005",
            candidate_eligible=False,
            failed_gate_count=1,
            eligibility_gate_count=1,
            failed_gate_ids=["G01"],
            gates=gates,
        ),
    )
    p312 = write_json(tmp_path / "artifacts/phase312.json", payload(312, freeze_created=False))
    p313 = write_json(tmp_path / "artifacts/phase313.json", payload(313, evidence_clock_started=False))
    result = module.build(
        p304, p306, p307, p308, p309, p310, p311, p312, p313,
        tmp_path / "artifacts/phase314",
    )
    portal = tmp_path / result["portal_path"]
    text = portal.read_text(encoding="utf-8")
    assert result["scientific_decision"] == "CLOSE_CURRENT_FAMILY_RESEARCH_ONLY"
    assert "O QUE FOI COLETADO" in text
    assert "EXEMPLO COM R$10.000" in text
    assert "VOCE ESTA AQUI" in text
    assert result["strategy_approved"] is False
