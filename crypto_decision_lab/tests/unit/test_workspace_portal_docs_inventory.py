from __future__ import annotations

from pathlib import Path

from crypto_decision_lab.reports.workspace_portal_docs_inventory import build_workspace_portal_docs_inventory


def test_workspace_portal_docs_inventory_builds(tmp_path: Path) -> None:
    result = build_workspace_portal_docs_inventory(output_dir=tmp_path, repo_root=Path.cwd().parent)
    payload = result["payload"]
    assert payload["policy_lock"] == "ACTIVE"
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["orders_generated"] is False
    assert payload["real_capital_used"] is False
    assert payload["trading_signal_generated"] is False
    assert payload["gate_answer"].endswith("RESEARCH_ONLY")
    assert (tmp_path / "index.html").exists()
    assert (tmp_path / "workspace_portal_docs_inventory.md").exists()
    assert payload["criteria_total_count"] >= 6
