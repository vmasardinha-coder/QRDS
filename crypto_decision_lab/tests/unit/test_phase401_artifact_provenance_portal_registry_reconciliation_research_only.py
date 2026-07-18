from pathlib import Path
from tests.unit._phase396_405_fixtures import assert_locked, load_phase, payload, write_json

def test_phase401_reconciles_phase395_portal_provenance(tmp_path):
    project=tmp_path/"crypto_decision_lab"
    portal=project/"artifacts/phase394/index.html"
    portal.parent.mkdir(parents=True)
    portal.write_text("ok",encoding="utf-8")
    registry=project/"artifacts/project_portal_registry/current_portal.json"
    registry.parent.mkdir(parents=True)
    registry.write_text('{"phase":394,"relative_path":"artifacts/phase394/index.html"}',encoding="utf-8")
    module=load_phase(Path(r"C:\QRDS\crypto_decision_lab"),401)
    p395=write_json(tmp_path/"395.json",payload(395))
    p400=write_json(tmp_path/"400.json",payload(400))
    result=module.build(p395,p400,output_dir=project/"artifacts/phase401",project_root=project,git_root=tmp_path)
    assert result["provenance_registry_reconciled"] is True
    assert result["portal_exists"] is True
    assert_locked(result)
