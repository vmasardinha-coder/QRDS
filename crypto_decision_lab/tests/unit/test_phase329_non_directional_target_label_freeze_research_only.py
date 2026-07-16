from crypto_decision_lab.scripts import (
    phase329_non_directional_target_label_freeze_research_only as module,
)
from tests.unit._phase326_335_fixtures import (
    patch_roots,
    payload,
    write_json,
)


def test_phase329_freezes_only_abstention_reliability_target(
    monkeypatch, tmp_path
):
    patch_roots(monkeypatch, tmp_path, module)
    p328 = write_json(
        tmp_path / "p328.json",
        payload(328, family_definition_frozen=True),
    )
    result = module.build(p328, tmp_path / "artifacts/phase329")
    contract = result["target_contract"]
    assert result["target_label_frozen"] is True
    assert contract["directional_return_prediction_allowed"] is False
    assert contract["threshold_source"] == "TRAINING_FOLD_ONLY"
    assert result["real_historical_labels_created"] == 0
