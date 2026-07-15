from crypto_decision_lab.scripts import phase313_forward_evidence_design_readiness_research_only as module
from tests.unit._phase306_315_fixtures import patch_roots, payload, write_json


def test_phase313_forward_clock_stays_inactive_without_freeze(monkeypatch, tmp_path):
    patch_roots(monkeypatch, tmp_path, module)
    p311 = write_json(
        tmp_path / "artifacts/phase311.json",
        payload(311, candidate_eligible=False),
    )
    p312 = write_json(
        tmp_path / "artifacts/phase312.json",
        payload(312, freeze_readiness=False, freeze_created=False),
    )
    result = module.build(p311, p312, tmp_path / "artifacts/phase313")
    assert result["phase"] == 313
    assert result["contract_complete"] is True
    assert result["activation_ready"] is False
    assert result["evidence_clock_started"] is False
    assert result["forward_evidence_credit"] == 0
    assert result["historical_backfill_to_forward_clock"] is False
