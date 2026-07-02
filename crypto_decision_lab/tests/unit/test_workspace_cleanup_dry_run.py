from pathlib import Path

from crypto_decision_lab.reports.workspace_cleanup_dry_run import build_workspace_cleanup_dry_run


def test_workspace_cleanup_dry_run_detects_exact_duplicate(tmp_path: Path) -> None:
    (tmp_path / "crypto_decision_lab" / "docs" / "reports").mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    root_wrapper = tmp_path / "qrds_sample.sh"
    script_wrapper = tmp_path / "scripts" / "qrds_sample.sh"
    root_wrapper.write_text("#!/usr/bin/env bash\necho ok\n", encoding="utf-8")
    script_wrapper.write_text("#!/usr/bin/env bash\necho ok\n", encoding="utf-8")
    (tmp_path / "crypto_decision_lab" / "docs" / "reports" / "X.md").write_text("# X\n", encoding="utf-8")

    result = build_workspace_cleanup_dry_run(tmp_path / "out", repo_root=tmp_path)
    payload = result["payload"]

    assert payload["policy_lock"] == "ACTIVE"
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["exact_duplicate_wrapper_count"] == 1
    assert payload["low_risk_candidate_count"] >= 1
    assert payload["applied_count"] == 0
    assert payload["orders_generated"] is False


def test_workspace_cleanup_apply_requires_explicit_flag(tmp_path: Path) -> None:
    (tmp_path / "crypto_decision_lab").mkdir()
    (tmp_path / "scripts").mkdir()
    root_wrapper = tmp_path / "qrds_sample.sh"
    script_wrapper = tmp_path / "scripts" / "qrds_sample.sh"
    root_wrapper.write_text("same\n", encoding="utf-8")
    script_wrapper.write_text("same\n", encoding="utf-8")

    build_workspace_cleanup_dry_run(tmp_path / "dry", repo_root=tmp_path)
    assert script_wrapper.exists()

    result = build_workspace_cleanup_dry_run(tmp_path / "apply", repo_root=tmp_path, apply_low_risk=True)
    assert result["payload"]["applied_count"] >= 1
    assert not script_wrapper.exists()
