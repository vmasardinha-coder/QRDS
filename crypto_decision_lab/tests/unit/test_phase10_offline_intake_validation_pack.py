import json
from pathlib import Path

from crypto_decision_lab.reports.phase10_offline_intake_validation_pack import build_phase10_offline_intake_validation_pack


def test_phase10_offline_intake_validation_pack_builds_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    c = root / "crypto_decision_lab" / "artifacts" / "canonical_data_collection_dry_run" / "canonical_data_collection_dry_run_index.json"
    a = root / "crypto_decision_lab" / "artifacts" / "canonical_data_source_adapter_dry_run" / "canonical_data_source_adapter_dry_run_index.json"
    t = root / "crypto_decision_lab" / "artifacts" / "manual_intake_template_validation_dry_run" / "manual_intake_template_validation_dry_run_index.json"
    template_file = root / "crypto_decision_lab" / "artifacts" / "manual_intake_template_validation_dry_run" / "templates" / "btc_usdt_1h_manual_template.jsonl"
    template_file.parent.mkdir(parents=True)
    c.parent.mkdir(parents=True)
    a.parent.mkdir(parents=True)
    t.parent.mkdir(parents=True, exist_ok=True)
    c.write_text(json.dumps({"gate_answer": "CANONICAL_DATA_COLLECTION_DRY_RUN_READY_RESEARCH_ONLY"}), encoding="utf-8")
    a.write_text(json.dumps({"gate_answer": "CANONICAL_DATA_SOURCE_ADAPTER_DRY_RUN_READY_RESEARCH_ONLY"}), encoding="utf-8")
    template_file.write_text(json.dumps({"timestamp":"2026-01-01T00:00:00Z","open":0.0,"high":0.0,"low":0.0,"close":0.0,"volume":0.0,"symbol":"BTC-USDT","interval":"1h","source":"TEST"}) + "\n", encoding="utf-8")
    t.write_text(json.dumps({"gate_answer": "MANUAL_INTAKE_TEMPLATE_VALIDATION_DRY_RUN_READY_RESEARCH_ONLY", "payload": {"templates": [{"symbol":"BTC-USDT","interval":"1h","actual_template_path": str(template_file), "ready": True}]}}), encoding="utf-8")

    result = build_phase10_offline_intake_validation_pack(output_dir=tmp_path / "out", repo_root=root)
    payload = result["payload"]

    assert payload["policy_lock"] == "ACTIVE"
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["templates_checked"] == 1
    assert payload["valid_templates"] == 1
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()


def test_phase10_offline_intake_validation_pack_has_no_operational_flags(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    result = build_phase10_offline_intake_validation_pack(output_dir=tmp_path / "out", repo_root=root)
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
