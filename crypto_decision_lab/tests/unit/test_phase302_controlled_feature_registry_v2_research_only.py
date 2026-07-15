from pathlib import Path

from crypto_decision_lab.scripts import phase301_official_public_history_extension_research_only as phase301
from crypto_decision_lab.scripts import phase302_controlled_feature_registry_v2_research_only as phase302
from crypto_decision_lab.scripts.phase301_305_evidence_v2_common import write_json


def test_phase302_builds_past_only_feature_matrix(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(phase301, "ROOT", tmp_path)
    monkeypatch.setattr(phase302, "ROOT", tmp_path)

    phase301_dir = tmp_path / "artifacts/phase301"
    phase301_payload = phase301.build_fixture(phase301_dir, hours=900)
    phase301_path = phase301_dir / "phase301.json"
    write_json(phase301_path, phase301_payload)

    payload = phase302.build(phase301_path, tmp_path / "artifacts/phase302")

    assert payload["phase"] == 302
    assert payload["row_count"] == 900
    assert payload["feature_count"] == len(payload["feature_registry"])
    assert payload["feature_count"] >= 15
    assert payload["future_leakage_allowed"] is False
    assert payload["features_use_closed_or_settled_data_only"] is True
    assert payload["feature_selection_performed"] is False
    assert payload["strategy_approved"] is False
    assert (tmp_path / payload["matrix_path"]).is_file()
