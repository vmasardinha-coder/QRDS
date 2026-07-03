import json
from pathlib import Path

from crypto_decision_lab.reports.foundation_checkpoint_next_phase import build_foundation_checkpoint_next_phase


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_foundation_checkpoint_next_phase_builds_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    base = root / "crypto_decision_lab" / "artifacts"
    _write_json(base / "data_source_contract" / "data_source_contract_index.json", {"gate_answer": "DATA_SOURCE_CONTRACT_CREATED_SCHEMA_READY_RESEARCH_ONLY"})
    _write_json(base / "data_acquisition_depth_plan" / "data_acquisition_depth_plan_index.json", {"gate_answer": "DATA_ACQUISITION_DEPTH_PLAN_HIGH_PRIORITY_GAPS_RESEARCH_ONLY", "total_rows": 324, "target_rows_per_symbol": 5000})
    _write_json(base / "archive_manifest_repo_hygiene" / "archive_manifest_repo_hygiene_index.json", {"gate_answer": "ARCHIVE_MANIFEST_REPO_HYGIENE_INDEX_READY_RESEARCH_ONLY", "archived_installer_count": 52})
    _write_json(base / "post_cleanup_portal_acceptance" / "post_cleanup_portal_acceptance_index.json", {"gate_answer": "POST_CLEANUP_PORTAL_ACCEPTANCE_READY_RESEARCH_ONLY"})

    result = build_foundation_checkpoint_next_phase(output_dir=tmp_path / "out", repo_root=root)
    payload = result["payload"]

    assert payload["policy_lock"] == "ACTIVE"
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["data_schema_ready"] is True
    assert payload["depth_plan_ready"] is True
    assert payload["repo_hygiene_ready"] is True
    assert payload["portal_acceptance_ready"] is True
    assert Path(result["html_path"]).exists()


def test_foundation_checkpoint_next_phase_has_no_operational_flags(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    result = build_foundation_checkpoint_next_phase(output_dir=tmp_path / "out", repo_root=root)
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
