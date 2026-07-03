from pathlib import Path

from crypto_decision_lab.reports.post_cleanup_portal_acceptance import build_post_cleanup_portal_acceptance


def test_post_cleanup_portal_acceptance_builds_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "crypto_decision_lab" / "docs").mkdir(parents=True)
    (root / "crypto_decision_lab" / "docs" / "x.md").write_text("doc", encoding="utf-8")
    (root / "crypto_decision_lab" / "artifacts" / "unified_portal_suite").mkdir(parents=True)
    (root / "crypto_decision_lab" / "artifacts" / "unified_portal_suite" / "index.html").write_text("<html></html>", encoding="utf-8")
    (root / "scripts" / "archive" / "installers").mkdir(parents=True)
    (root / "scripts" / "archive" / "installers" / "qrds_sprint_9A_example.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    for name in [
        "qrds_unified_portal_serve.sh",
        "qrds_research_command_center_serve.sh",
        "qrds_research_book_reader_serve.sh",
        "qrds_data_source_contract_from_stack_serve.sh",
        "qrds_archive_manifest_repo_hygiene_serve.sh",
    ]:
        (root / name).write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    result = build_post_cleanup_portal_acceptance(output_dir=tmp_path / "out", repo_root=root)
    payload = result["payload"]

    assert payload["policy_lock"] == "ACTIVE"
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["root_sprint_installer_count"] == 0
    assert payload["archived_installer_count"] == 1
    assert Path(result["html_path"]).exists()


def test_post_cleanup_portal_acceptance_has_no_operational_flags(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "crypto_decision_lab" / "docs").mkdir(parents=True)
    (root / "crypto_decision_lab" / "artifacts").mkdir(parents=True)
    result = build_post_cleanup_portal_acceptance(output_dir=tmp_path / "out", repo_root=root)
    payload = result["payload"]

    for key in [
        "api_key_present",
        "authenticated_connection_used",
        "orders_generated",
        "real_orders_generated",
        "real_capital_used",
        "trading_signal_generated",
        "executable_signal_generated",
        "recommendation_generated",
        "allocation_generated",
        "portfolio_decision_generated",
        "operational_decision_allowed",
    ]:
        assert payload[key] is False
