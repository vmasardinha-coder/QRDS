import json
from pathlib import Path

from crypto_decision_lab.reports.phase10_depth_expansion_readiness_pack import build_phase10_depth_expansion_readiness_pack


def test_phase10_depth_expansion_readiness_pack_builds_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    q = root / "crypto_decision_lab" / "artifacts" / "phase10_sample_quality_promotion_gate_pack" / "phase10_sample_quality_promotion_gate_pack_index.json"
    q.parent.mkdir(parents=True)
    q.write_text(json.dumps({"gate_answer": "PHASE10_SAMPLE_QUALITY_PROMOTION_GATE_READY_BLOCKED_RESEARCH_ONLY", "payload": {"quality_metrics": {"per_symbol": [{"symbol": "BTC-USDT", "rows": 5, "intervals": ["1h"], "full_depth_gap": 4995}]}}}), encoding="utf-8")

    result = build_phase10_depth_expansion_readiness_pack(output_dir=tmp_path / "out", repo_root=root)
    payload = result["payload"]

    assert payload["policy_lock"] == "ACTIVE"
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["prior_quality_pack_present"] is True
    assert payload["symbols_planned"] == 1
    assert payload["batches_planned"] >= 1
    assert payload["source_requests_written"] == 1
    assert payload["promotion_allowed"] is False
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()


def test_phase10_depth_expansion_readiness_pack_has_no_operational_flags(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    result = build_phase10_depth_expansion_readiness_pack(output_dir=tmp_path / "out", repo_root=root)
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
