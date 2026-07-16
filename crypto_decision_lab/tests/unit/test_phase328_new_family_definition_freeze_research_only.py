from crypto_decision_lab.scripts import (
    phase328_new_family_definition_freeze_research_only as module,
)
from tests.unit._phase326_335_fixtures import (
    accepted_phase327,
    patch_roots,
    payload,
    write_json,
)


def test_phase328_freezes_definition_but_does_not_open_family(
    monkeypatch, tmp_path
):
    patch_roots(monkeypatch, tmp_path, module)
    p323 = write_json(
        tmp_path / "p323.json",
        payload(323, preregistration_draft_created=True),
    )
    p327 = write_json(tmp_path / "p327.json", accepted_phase327())
    result = module.build(p323, p327, tmp_path / "artifacts/phase328")
    assert result["family_definition_frozen"] is True
    assert result["family_definition_sha256"]
    assert result["new_family_opened"] is False
    assert result["hypotheses_registered"] == 0
