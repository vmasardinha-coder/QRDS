from pathlib import Path
from tests.unit._phase396_405_fixtures import assert_locked, load_phase, payload, write_json

def test_phase404_builds_locked_unified_portal(tmp_path):
    project=tmp_path/"crypto_decision_lab"
    module=load_phase(Path(r"C:\QRDS\crypto_decision_lab"),404)
    paths=[write_json(tmp_path/f"{p}.json",payload(p)) for p in range(400,404)]
    out=project/"artifacts/phase404"
    result=module.build(*paths,output_dir=out,project_root=project,git_root=tmp_path)
    html=(out/"index.html").read_text(encoding="utf-8")
    assert result["portal_ready"] is True
    assert "BLOCKED_RESEARCH_ONLY" in html
    assert "CAPITAL R$ 0" in html
    assert_locked(result)
