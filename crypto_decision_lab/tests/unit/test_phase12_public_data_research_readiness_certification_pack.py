import csv
import json
from pathlib import Path
from crypto_decision_lab.reports.phase12_public_data_research_readiness_certification_pack import build_phase12_public_data_research_readiness_certification_pack

def write_index(root: Path, folder: str, file: str, data: dict):
    p = root / "crypto_decision_lab" / "artifacts" / folder / file
    p.parent.mkdir(parents=True, exist_ok=True)
    data.setdefault("policy_lock", "ACTIVE")
    data.setdefault("app_mode", "INTERACTIVE_RESEARCH_ONLY")
    data.setdefault("gate_answer", "READY_RESEARCH_ONLY")
    p.write_text(json.dumps(data), encoding="utf-8")

def test_phase12_public_data_research_readiness_certification_pack_builds(tmp_path: Path):
    root = tmp_path / "repo"
    inbox = root / "crypto_decision_lab" / "manual_intake" / "inbox"
    inbox.mkdir(parents=True)
    for sym in ["btc_usdt", "eth_usdt", "sol_usdt"]:
        p = inbox / f"{sym}_binance_public_klines_1h.csv"
        dash = sym.upper().replace("_", "-")
        with p.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["timestamp","open","high","low","close","volume","symbol","interval","source"])
            w.writeheader()
            for i in range(2):
                w.writerow({"timestamp": f"2026-01-01T0{i}:00:00Z", "open": 100+i, "high": 101+i, "low": 99+i, "close": 100.5+i, "volume": 1+i, "symbol": dash, "interval": "1h", "source": "BINANCE_SPOT_PUBLIC_KLINES_RESEARCH_ONLY"})
    write_index(root, "phase12_public_market_data_fetch_pack", "phase12_public_market_data_fetch_pack_index.json", {"canonical_data_writes": 0, "promotion_allowed": False})
    write_index(root, "phase11_offline_source_normalizer_pack", "phase11_offline_source_normalizer_pack_index.json", {"rows_normalized": 6})
    write_index(root, "phase11_data_drop_acceptance_pipeline_pack", "phase11_data_drop_acceptance_pipeline_pack_index.json", {"data_drop_mode": "INBOX_DATA", "rows_normalized": 6, "valid_rows": 6, "staging_rows": 6, "total_gap_rows": 0, "promotion_allowed": False, "canonical_data_writes": 0})
    write_index(root, "phase10_sample_quality_promotion_gate_pack", "phase10_sample_quality_promotion_gate_pack_index.json", {"sample_quality_ready": True, "full_depth_ready": True})
    write_index(root, "phase11_canonical_promotion_dry_run_lock_pack", "phase11_canonical_promotion_dry_run_lock_pack_index.json", {"safe_apply_allowed": False, "promotion_allowed": False, "canonical_data_writes": 0})
    r = build_phase12_public_data_research_readiness_certification_pack(tmp_path / "out", root)
    payload = r["payload"]
    assert payload["policy_lock"] == "ACTIVE"
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["public_file_count"] == 3
    assert payload["public_rows_total"] == 6
    assert payload["promotion_allowed"] is False
    assert payload["canonical_data_writes"] == 0
    assert Path(r["html_path"]).exists()

def test_phase12_public_data_research_readiness_certification_pack_has_no_operational_flags(tmp_path: Path):
    r = build_phase12_public_data_research_readiness_certification_pack(tmp_path / "out", tmp_path / "repo")
    p = r["payload"]
    for key in ["api_key_present","authenticated_connection_used","orders_generated","real_orders_generated","real_capital_used","trading_signal_generated","executable_signal_generated","recommendation_generated","allocation_generated","portfolio_decision_generated","operational_decision_allowed"]:
        assert p[key] is False
