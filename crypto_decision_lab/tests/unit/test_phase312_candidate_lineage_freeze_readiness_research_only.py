from crypto_decision_lab.scripts import phase312_candidate_lineage_freeze_readiness_research_only as module
from tests.unit._phase306_315_fixtures import patch_roots, payload, phase304_payload, write_json


def test_phase312_lineage_complete_but_no_automatic_freeze(monkeypatch, tmp_path):
    patch_roots(monkeypatch, tmp_path, module)
    paths = {
        304: write_json(tmp_path / "artifacts/phase304.json", phase304_payload()),
        306: write_json(tmp_path / "artifacts/phase306.json", payload(306)),
        307: write_json(tmp_path / "artifacts/phase307.json", payload(307)),
        308: write_json(tmp_path / "artifacts/phase308.json", payload(308)),
        309: write_json(tmp_path / "artifacts/phase309.json", payload(309)),
        310: write_json(tmp_path / "artifacts/phase310.json", payload(310)),
        311: write_json(
            tmp_path / "artifacts/phase311.json",
            payload(
                311,
                candidate_hypothesis_id="OI_MOM_H8_T005",
                candidate_eligible=False,
                eligibility_contract_fingerprint="contract",
            ),
        ),
    }
    result = module.build(
        paths[304], paths[306], paths[307], paths[308], paths[309], paths[310], paths[311],
        tmp_path / "artifacts/phase312",
    )
    assert result["phase"] == 312
    assert result["lineage_complete"] is True
    assert result["freeze_created"] is False
    assert result["freeze_status"] == "NOT_FROZEN_NO_ELIGIBLE_CANDIDATE"
    assert result["automatic_freeze_allowed"] is False
