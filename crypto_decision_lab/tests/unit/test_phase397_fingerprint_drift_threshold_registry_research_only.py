from pathlib import Path
from tests.unit._phase396_405_fixtures import assert_locked, load_phase, payload, write_json

def test_phase397_freezes_zero_drift_release_thresholds(tmp_path):
    project=tmp_path/"crypto_decision_lab"
    module=load_phase(Path(r"C:\QRDS\crypto_decision_lab"),397)
    p396=write_json(tmp_path/"396.json",payload(396))
    result=module.build(p396,output_dir=project/"artifacts/phase397",project_root=project,git_root=tmp_path)
    assert result["drift_thresholds_frozen"] is True
    assert set(result["drift_thresholds"].values()) == {0}
    assert result["scientific_metrics_computed"] is False
    assert_locked(result)
