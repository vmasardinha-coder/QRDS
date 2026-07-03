import json
from pathlib import Path
from crypto_decision_lab.reports.phase11_canonical_promotion_dry_run_lock_pack import build_phase11_canonical_promotion_dry_run_lock_pack

def test_phase11_canonical_promotion_dry_run_lock_pack_builds_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    sample_base = root / "crypto_decision_lab" / "artifacts" / "phase10_offline_sample_intake_promotion_pack"
    quality_base = root / "crypto_decision_lab" / "artifacts" / "phase10_sample_quality_promotion_gate_pack"
    staging = sample_base / "validated_staging"
    staging.mkdir(parents=True)
    quality_base.mkdir(parents=True)
    rows = [{"timestamp": f"2026-01-01T0{i}:00:00Z", "open": 100+i, "high": 101+i, "low": 99+i, "close": 100.5+i, "volume": 1000+i, "symbol": "BTC-USDT", "interval": "1h", "source": "TEST"} for i in range(5)]
    sf = staging / "btc_usdt_1h_validated_staging.jsonl"
    sf.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    man = {"entries": [{"symbol": "BTC-USDT", "interval": "1h", "staging_file": str(sf), "rows": 5}], "canonical_data_writes": 0, "promotion_allowed": False}
    (sample_base / "phase10_offline_sample_intake_promotion_pack_index.json").write_text(json.dumps({"gate_answer": "PHASE10_OFFLINE_SAMPLE_INTAKE_PROMOTION_PACK_READY_REVIEW_BLOCKED_RESEARCH_ONLY", "payload": {"validated_staging_manifest": man}}), encoding="utf-8")
    (quality_base / "phase10_sample_quality_promotion_gate_pack_index.json").write_text(json.dumps({"gate_answer": "PHASE10_SAMPLE_QUALITY_PROMOTION_GATE_READY_BLOCKED_RESEARCH_ONLY", "sample_quality_ready": True, "full_depth_ready": False, "promotion_allowed": False, "canonical_data_writes": 0}), encoding="utf-8")
    result = build_phase11_canonical_promotion_dry_run_lock_pack(tmp_path / "out", root)
    payload = result["payload"]
    assert payload["policy_lock"] == "ACTIVE"
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["promotion_candidates_count"] == 1
    assert payload["total_candidate_rows"] == 5
    assert payload["safe_apply_allowed"] is False
    assert payload["promotion_allowed"] is False
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()

def test_phase11_canonical_promotion_dry_run_lock_pack_has_no_operational_flags(tmp_path: Path) -> None:
    result = build_phase11_canonical_promotion_dry_run_lock_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]
    for key in ["api_key_present", "authenticated_connection_used", "orders_generated", "real_orders_generated", "real_capital_used", "trading_signal_generated", "executable_signal_generated", "recommendation_generated", "allocation_generated", "portfolio_decision_generated", "operational_decision_allowed"]:
        assert payload[key] is False
