from crypto_decision_lab.scripts import (
    phase334_synthetic_anti_leakage_review_portal_research_only as module,
)
from crypto_decision_lab.scripts.phase301_305_evidence_v2_common import (
    REQUIRED_PORTAL_HEADINGS,
)
from tests.unit._phase326_335_fixtures import (
    accepted_chain,
    patch_roots,
    write_json,
)


def test_phase334_portal_is_visual_and_registry_remains_closed(
    monkeypatch, tmp_path
):
    patch_roots(monkeypatch, tmp_path, module)
    values = accepted_chain()
    paths = [
        write_json(tmp_path / f"p{phase}.json", values[phase])
        for phase in range(327, 334)
    ]
    result = module.build(*paths, tmp_path / "artifacts/phase334")
    assert result["audit_pass"] is True
    assert result["registry_open"] is False
    assert result["historical_evaluation_started"] is False
    html = (tmp_path / result["portal_path"]).read_text(
        encoding="utf-8-sig"
    )
    assert "VOCE ESTA AQUI" in html
    for heading in REQUIRED_PORTAL_HEADINGS:
        assert heading in html
