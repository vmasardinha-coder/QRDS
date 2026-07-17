from pathlib import Path
from tests.unit._phase386_395_fixtures import assert_locked, load_phase_module, payload, write_json

def test_phase394_builds_unified_locked_portal(tmp_path):
    project = tmp_path/"crypto_decision_lab"
    module = load_phase_module(394)
    paths = [write_json(tmp_path/f"{p}.json",payload(p)) for p in range(386,394)]
    out = project/"artifacts/phase394"
    result = module.build(*paths,output_dir=out,project_root=project,git_root=tmp_path)
    html = (out/"index.html").read_text(encoding="utf-8")
    assert result["portal_ready"] is True
    assert "BLOCKED_RESEARCH_ONLY" in html
    assert "CAPITAL R$ 0" in html
    assert (project/"artifacts/project_portal_registry/current_portal.json").is_file()
    assert_locked(result)
