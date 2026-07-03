import json
from pathlib import Path

from crypto_decision_lab.reports.phase10_sample_quality_promotion_gate_pack import build_phase10_sample_quality_promotion_gate_pack


def test_phase10_sample_quality_promotion_gate_pack_builds_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    base = root / "crypto_decision_lab" / "artifacts" / "phase10_offline_sample_intake_promotion_pack"
    staging = base / "validated_staging"
    staging.mkdir(parents=True)
    rows = []
    for i in range(5):
        rows.append({"timestamp": f"2026-01-01T0{i}:00:00Z", "open": 100+i, "high": 101+i, "low": 99+i, "close": 100.5+i, "volume": 1000+i, "symbol": "BTC-USDT", "interval": "1h", "source": "TEST"})
    staging_file = staging / "btc_usdt_1h_validated_staging.jsonl"
    staging_file.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    manifest = {"entries": [{"symbol": "BTC-USDT", "interval": "1h", "staging_file": str(staging_file), "rows": 5}], "canonical_data_writes": 0, "promotion_allowed": False}
    (staging / "validated_staging_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (base / "phase10_offline_sample_intake_promotion_pack_index.json").write_text(json.dumps({"gate_answer": "PHASE10_OFFLINE_SAMPLE_INTAKE_PROMOTION_PACK_READY_REVIEW_BLOCKED_RESEARCH_ONLY", "payload": {"validated_staging_manifest": manifest}}), encoding="utf-8")

    result = build_phase10_sample_quality_promotion_gate_pack(output_dir=tmp_path / "out", repo_root=root)
    payload = result["payload"]

    assert payload["policy_lock"] == "ACTIVE"
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["sample_quality_ready"] is True
    assert payload["full_depth_ready"] is False
    assert payload["promotion_allowed"] is False
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()


def test_phase10_sample_quality_promotion_gate_pack_has_no_operational_flags(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    result = build_phase10_sample_quality_promotion_gate_pack(output_dir=tmp_path / "out", repo_root=root)
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
