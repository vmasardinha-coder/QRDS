import json
from pathlib import Path

from crypto_decision_lab.reports.phase10_offline_sample_intake_promotion_pack import build_phase10_offline_sample_intake_promotion_pack


def test_phase10_offline_sample_intake_promotion_pack_builds_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    p = root / "crypto_decision_lab" / "artifacts" / "phase10_offline_intake_validation_pack" / "phase10_offline_intake_validation_pack_index.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"gate_answer": "PHASE10_OFFLINE_INTAKE_VALIDATION_PACK_READY_RESEARCH_ONLY", "payload": {"template_validations": [{"symbol": "BTC-USDT", "interval": "1h", "valid": True, "template_path": "x"}]}}), encoding="utf-8")

    result = build_phase10_offline_sample_intake_promotion_pack(output_dir=tmp_path / "out", repo_root=root)
    payload = result["payload"]

    assert payload["policy_lock"] == "ACTIVE"
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["inbox_ready"] is True
    assert payload["artifact_sample_files"] == 1
    assert payload["files_validated"] >= 1
    assert payload["valid_rows"] > 0
    assert payload["canonical_data_writes"] == 0
    assert payload["promotion_allowed"] is False
    assert Path(result["html_path"]).exists()


def test_phase10_offline_sample_intake_promotion_pack_has_no_operational_flags(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    result = build_phase10_offline_sample_intake_promotion_pack(output_dir=tmp_path / "out", repo_root=root)
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
