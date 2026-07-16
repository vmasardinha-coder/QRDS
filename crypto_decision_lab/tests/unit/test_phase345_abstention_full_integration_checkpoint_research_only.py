from __future__ import annotations

import json

from tests.unit._phase336_345_fixtures import create_previous_state, patch_roots, run_chain

def test_phase345_checkpoint_with_global_suite_override(tmp_path, monkeypatch):
    patch_roots(monkeypatch, tmp_path)
    paths=run_chain(tmp_path, create_previous_state(tmp_path), through=344)
    junit=tmp_path/"targeted.xml"
    junit.write_text('<testsuite tests="10" failures="0" errors="0" skipped="0"></testsuite>', encoding="utf-8")
    from crypto_decision_lab.scripts.phase345_abstention_full_integration_checkpoint_research_only import build_checkpoint
    full={"passed":True,"test_file_count":574,"totals":{"tests":1481,"failures":0,"errors":0,"skipped":0},"manifest_stable":True}
    artifact=tmp_path/"outputs/345/phase345_abstention_full_integration_checkpoint.json"
    item=build_checkpoint({phase:paths[phase] for phase in range(335,345)}, targeted_junit_path=junit, artifact_path=artifact, documentation_path=tmp_path/"docs/phase345.md", tracking_dir=tmp_path/"docs/tracking", full_suite_output_dir=tmp_path/"full", full_suite_override=full)
    assert item["global_full_suite"]["passed"] is True
    assert item["strategy_approved"] is False
    assert item["forward_evidence_clock_started"] is False
    assert item["next_tracking_checkpoint"] == 355
