from crypto_decision_lab.scripts import phase307_regime_concentration_audit_research_only as module
from tests.unit._phase306_315_fixtures import patch_roots, phase304_payload, write_json


def test_phase307_regime_concentration_audit(monkeypatch, tmp_path):
    patch_roots(monkeypatch, tmp_path, module)
    source = write_json(tmp_path / "artifacts/phase304.json", phase304_payload())
    result = module.build(source, tmp_path / "artifacts/phase307")
    assert result["phase"] == 307
    assert result["regime_count"] == 3
    assert result["regime_concentration_pass"] is False
    assert "AT_LEAST_ONE_REGIME_HAS_NON_POSITIVE_LOWER_95" in result["failure_reasons"]
    assert result["locks"]["position_size"] == 0
