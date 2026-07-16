from __future__ import annotations
import json
from tests.unit._phase346_355_fixtures import run_module, seed_generated_phase_artifacts, seed_project

def test_phase354_creates_single_entry_without_erasing_readme(tmp_path):
    git_root, project = seed_project(tmp_path)
    seed_generated_phase_artifacts(project, 353)
    result = run_module(project, "phase354_unified_project_entry_portal_research_only")
    assert result.returncode == 0, result.stderr
    data = json.loads((project / "artifacts/phase354_unified_project_entry_portal_research_only/phase354_unified_project_entry_portal.json").read_text())
    page = (project / data["portal_relative_path"]).read_text()
    for heading in data["required_portal_headings"]:
        assert heading in page
    assert "VOCE ESTA AQUI" in page
    assert "Existing content must remain." in (git_root / "README.md").read_text()
    assert (git_root / "QRDS_START_HERE.md").is_file()
    registry = json.loads((project / "artifacts/project_portal_registry/current_portal.json").read_text())
    assert registry["phase"] == 354
    assert registry["capital_used"] == 0
