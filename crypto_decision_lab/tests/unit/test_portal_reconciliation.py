from __future__ import annotations

from pathlib import Path

from crypto_decision_lab.reports.portal_reconciliation import build_portal_reconciliation


def _touch(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_portal_reconciliation_maps_primary_families(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _touch(root / "crypto_decision_lab/artifacts/dashboard_hub/index.html", "hub")
    _touch(root / "crypto_decision_lab/artifacts/evidence_stack/index.html", "stack")
    _touch(root / "crypto_decision_lab/artifacts/research_book_reader/index.html", "book")
    _touch(root / "crypto_decision_lab/artifacts/data_source_contract/index.html", "data")
    _touch(root / "crypto_decision_lab/docs/reports/PORTAL_RECONCILIATION.md", "doc")
    _touch(root / "qrds_dashboard_hub_serve.sh", "#!/usr/bin/env bash\n")

    result = build_portal_reconciliation(output_dir=tmp_path / "out", repo_root=root)
    payload = result["payload"]

    assert payload["policy_lock"] == "ACTIVE"
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["portal_index_count"] == 4
    assert payload["primary_family_ready_count"] >= 3
    assert payload["gate_answer"] == "PORTAL_RECONCILIATION_READY_RESEARCH_ONLY"
    assert payload["orders_generated"] is False
    assert (tmp_path / "out" / "index.html").exists()


def test_portal_reconciliation_blocks_empty_workspace(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "crypto_decision_lab").mkdir(parents=True)
    result = build_portal_reconciliation(output_dir=tmp_path / "out", repo_root=root)
    payload = result["payload"]

    assert payload["gate_answer"] == "NO_PORTAL_RECONCILIATION_SURFACES_FOUND_RESEARCH_ONLY"
    assert payload["operational_decision_allowed"] is False
