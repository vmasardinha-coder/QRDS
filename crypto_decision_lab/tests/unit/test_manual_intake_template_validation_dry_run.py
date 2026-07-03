import json
from pathlib import Path

from crypto_decision_lab.reports.manual_intake_template_validation_dry_run import build_manual_intake_template_validation_dry_run


def test_manual_intake_template_validation_dry_run_builds_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    q = root / "crypto_decision_lab" / "artifacts" / "canonical_data_source_adapter_dry_run" / "canonical_data_source_adapter_dry_run_index.json"
    q.parent.mkdir(parents=True)
    q.write_text(json.dumps({"gate_answer": "CANONICAL_DATA_SOURCE_ADAPTER_DRY_RUN_READY_RESEARCH_ONLY", "payload": {"adapter_jobs": [{"symbol": "BTC-USDT", "interval": "1h", "source_type": "MANUAL_FILE_DROP", "gap_rows": 10, "output_path": "x.jsonl"}]}}), encoding="utf-8")

    result = build_manual_intake_template_validation_dry_run(output_dir=tmp_path / "out", repo_root=root)
    payload = result["payload"]

    assert payload["policy_lock"] == "ACTIVE"
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["adapter_queue_present"] is True
    assert payload["templates_created"] == 1
    assert payload["valid_templates"] == 1
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()


def test_manual_intake_template_validation_dry_run_has_no_operational_flags(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    result = build_manual_intake_template_validation_dry_run(output_dir=tmp_path / "out", repo_root=root)
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
