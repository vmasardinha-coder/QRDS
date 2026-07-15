from pathlib import Path

from crypto_decision_lab.scripts import phase301_official_public_history_extension_research_only as phase301
from crypto_decision_lab.scripts import phase302_controlled_feature_registry_v2_research_only as phase302
from crypto_decision_lab.scripts import phase303_finite_hypothesis_registry_v2_research_only as phase303
from crypto_decision_lab.scripts import phase304_nested_walk_forward_v2_research_only as phase304
from crypto_decision_lab.scripts.phase301_305_evidence_v2_common import REQUIRED_PORTAL_HEADINGS, write_json


def test_phase304_portal_is_visual_and_never_approves_execution(tmp_path: Path, monkeypatch):
    for module in (phase301, phase302, phase303, phase304):
        monkeypatch.setattr(module, "ROOT", tmp_path)

    p301_dir = tmp_path / "artifacts/phase301"
    p301_payload = phase301.build_fixture(p301_dir, hours=1200)
    p301_path = p301_dir / "phase301.json"
    write_json(p301_path, p301_payload)
    p302_payload = phase302.build(p301_path, tmp_path / "artifacts/phase302")
    p302_path = tmp_path / "artifacts/phase302/phase302_controlled_feature_registry_v2.json"
    p303_payload = phase303.build(p302_path, tmp_path / "artifacts/phase303")
    p303_path = tmp_path / "artifacts/phase303/phase303_finite_hypothesis_registry_v2.json"

    custom_folds = [
        {"train_start": 168, "train_end": 419, "inner_start": 420, "inner_end": 599, "outer_start": 624, "outer_end": 799, "embargo_hours": 24},
        {"train_start": 168, "train_end": 619, "inner_start": 620, "inner_end": 799, "outer_start": 824, "outer_end": 999, "embargo_hours": 24},
        {"train_start": 168, "train_end": 799, "inner_start": 800, "inner_end": 949, "outer_start": 974, "outer_end": 1149, "embargo_hours": 24},
    ]
    monkeypatch.setattr(phase304, "_folds", lambda length: custom_folds)
    payload = phase304.build(p302_path, p303_path, tmp_path / "artifacts/phase304")

    assert payload["phase"] == 304
    assert payload["nested_walk_forward"] is True
    assert payload["outer_data_used_for_selection"] is False
    assert payload["strategy_approved"] is False
    assert payload["forward_shadow_eligible"] is False
    assert payload["automatic_promotion"] is False
    assert payload["locks"]["capital_used"] == 0

    portal = tmp_path / payload["portal_path"]
    html = portal.read_text(encoding="utf-8")
    assert "VOCE ESTA AQUI" in html
    for heading in REQUIRED_PORTAL_HEADINGS:
        assert heading in html
