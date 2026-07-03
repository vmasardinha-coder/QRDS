from pathlib import Path

from crypto_decision_lab.reports.installer_archive_safe_apply import build_installer_archive_safe_apply


def test_installer_archive_safe_apply_dry_run_builds(tmp_path):
    root = tmp_path / "repo"
    (root / "crypto_decision_lab" / "src" / "crypto_decision_lab").mkdir(parents=True)
    (root / "scripts").mkdir()
    installer = root / "qrds_sprint_9A_workspace_housekeeping.sh"
    installer.write_text("#!/usr/bin/env bash\necho old\n", encoding="utf-8")
    result = build_installer_archive_safe_apply(tmp_path / "out", repo_root=root, apply=False)
    payload = result["payload"]
    assert payload["archive_candidates_before"] == 1
    assert payload["applied_item_count"] == 0
    assert installer.exists()
    assert payload["operational_decision_allowed"] is False
    assert payload["orders_generated"] is False


def test_installer_archive_safe_apply_moves_low_risk(tmp_path):
    root = tmp_path / "repo"
    (root / "crypto_decision_lab" / "src" / "crypto_decision_lab").mkdir(parents=True)
    (root / "scripts").mkdir()
    installer = root / "qrds_sprint_9B_data_coverage_gate.sh"
    installer.write_text("#!/usr/bin/env bash\necho old\n", encoding="utf-8")
    result = build_installer_archive_safe_apply(tmp_path / "out", repo_root=root, apply=True)
    payload = result["payload"]
    assert payload["applied_item_count"] == 1
    assert not installer.exists()
    assert (root / "scripts" / "archive" / "installers" / installer.name).exists()
    assert payload["remaining_archive_candidates"] == 0
