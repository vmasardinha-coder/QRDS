from __future__ import annotations
import json
from tests.unit._phase346_355_fixtures import run_module, seed_project

def test_phase349_separates_limitations_from_edge(tmp_path):
    _, project = seed_project(tmp_path)
    result = run_module(project, "phase349_abstention_data_limitation_audit_research_only")
    assert result.returncode == 0, result.stderr
    data = json.loads((project / "artifacts/phase349_abstention_data_limitation_audit_research_only/phase349_abstention_data_limitation_audit.json").read_text())
    assert data["limitation_count"] == 5
    assert data["data_quality_issue_proves_edge"] is False
    assert data["new_collection_started"] is False
