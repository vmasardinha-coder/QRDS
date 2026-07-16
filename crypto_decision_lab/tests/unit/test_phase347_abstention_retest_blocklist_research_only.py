from __future__ import annotations
import json
from tests.unit._phase346_355_fixtures import run_module, seed_generated_phase_artifacts, seed_project

def test_phase347_blocks_exact_and_semantic_retests(tmp_path):
    _, project = seed_project(tmp_path)
    seed_generated_phase_artifacts(project, 346)
    result = run_module(project, "phase347_abstention_retest_blocklist_research_only")
    assert result.returncode == 0, result.stderr
    data = json.loads((project / "artifacts/phase347_abstention_retest_blocklist_research_only/phase347_abstention_retest_blocklist.json").read_text())
    assert data["blocked_template_count"] == 12
    assert data["semantic_retests_blocked"] is True
    assert data["parameter_rescue_allowed"] is False
