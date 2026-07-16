from __future__ import annotations
import json
from tests.unit._phase346_355_fixtures import run_module, seed_generated_phase_artifacts, seed_project, write_junit

def test_phase355_integrates_closure_navigation_and_tracking(tmp_path):
    _, project = seed_project(tmp_path)
    seed_generated_phase_artifacts(project, 354)
    junit = write_junit(project / "artifacts/phase355_negative_evidence_navigation_checkpoint_research_only/targeted.xml")
    result = run_module(project, "phase355_negative_evidence_navigation_checkpoint_research_only", "--targeted-junit", str(junit))
    assert result.returncode == 0, result.stderr
    data = json.loads((project / "artifacts/phase355_negative_evidence_navigation_checkpoint_research_only/phase355_negative_evidence_navigation_checkpoint.json").read_text())
    assert data["blocked_template_count"] == 12
    assert data["unified_launcher_ready"] is True
    assert data["baseline_global_full_suite"]["tests"] == 1491
    assert data["global_full_suite_run_in_this_batch"] is False
    assert data["next_mandatory_global_full_suite"] == 365
    assert data["locks"]["capital_used"] == 0
    assert (project / "docs/reports/project_tracking/QRDS_ROADMAP_356_365_RESEARCH_ONLY.md").is_file()
