from crypto_decision_lab.scripts import phase310_timestamp_sensitivity_audit_research_only as module
from tests.unit._phase306_315_fixtures import (
    patch_roots,
    phase302_payload,
    phase303_payload,
    phase304_payload,
    write_json,
    write_matrix,
)


def test_phase310_timestamp_sensitivity_audit(monkeypatch, tmp_path):
    patch_roots(monkeypatch, tmp_path, module)
    matrix = write_matrix(tmp_path)
    phase302 = write_json(tmp_path / "artifacts/phase302.json", phase302_payload(matrix))
    phase303 = write_json(tmp_path / "artifacts/phase303.json", phase303_payload())
    phase304 = write_json(tmp_path / "artifacts/phase304.json", phase304_payload())
    result = module.build(phase302, phase303, phase304, tmp_path / "artifacts/phase310")
    assert result["phase"] == 310
    assert result["entry_delay_hours_tested"] == [0, 1, 2]
    assert result["future_data_used_for_signal"] is False
    assert result["new_hypotheses_added"] == 0
    assert result["strategy_approved"] is False
