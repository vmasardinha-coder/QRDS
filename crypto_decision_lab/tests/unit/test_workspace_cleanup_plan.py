from __future__ import annotations

from crypto_decision_lab.reports.workspace_cleanup_plan import build_workspace_cleanup_plan


def test_workspace_cleanup_plan_builds(tmp_path):
    result = build_workspace_cleanup_plan(tmp_path / "cleanup")
    payload = result["payload"]
    assert payload["policy_lock"] == "ACTIVE"
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["orders_generated"] is False
    assert payload["files_deleted"] is False
    assert payload["cleanup_actions_executed"] is False
    assert payload["criteria_ready_count"] >= 5
    assert (tmp_path / "cleanup" / "workspace_cleanup_plan.json").exists()
    assert (tmp_path / "cleanup" / "workspace_cleanup_plan.md").exists()
    assert (tmp_path / "cleanup" / "index.html").exists()


def test_workspace_cleanup_plan_is_plan_only(tmp_path):
    result = build_workspace_cleanup_plan(tmp_path / "cleanup")
    payload = result["payload"]
    assert payload["files_deleted"] is False
    assert payload["cleanup_actions_executed"] is False
    assert payload["gate_answer"].endswith("RESEARCH_ONLY")
