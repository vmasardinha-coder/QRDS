import csv, json
from pathlib import Path
from crypto_decision_lab.reports.phase13_binance_hyperliquid_source_comparison_pack import build_phase13_binance_hyperliquid_source_comparison_pack

def _idx(root, rel, data):
    p = root / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(data), encoding="utf-8")

def _csv(path, coin, source, symbol, rows=6):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["timestamp", "open", "high", "low", "close", "volume", "symbol", "interval", "source"]
    if "hyperliquid" in path.name: fields = ["timestamp", "open", "high", "low", "close", "volume", "symbol", "coin", "interval", "source", "venue"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for i in range(rows):
            price = 100 + i
            row = {"timestamp": f"2026-01-01T0{i}:00:00Z", "open": price, "high": price+1, "low": price-1, "close": price+0.5, "volume": 1000+i, "symbol": symbol, "interval": "1h", "source": source}
            if "coin" in fields: row.update({"coin": coin, "venue": "HYPERLIQUID"})
            w.writerow(row)

def test_phase13_binance_hyperliquid_source_comparison_pack_builds(tmp_path):
    root = tmp_path / "repo"
    _idx(root, "crypto_decision_lab/artifacts/phase12_public_data_research_readiness_certification_pack/phase12_public_data_research_readiness_certification_pack_index.json", {"public_data_research_ready": True, "gate_answer": "READY"})
    _idx(root, "crypto_decision_lab/artifacts/phase13_hyperliquid_public_data_adapter_pack/phase13_hyperliquid_public_data_adapter_pack_index.json", {"hyperliquid_adapter_ready": True, "gate_answer": "READY"})
    for coin in ["BTC", "ETH", "SOL"]:
        _csv(root/"crypto_decision_lab"/"manual_intake"/"inbox"/f"{coin.lower()}_usdt_binance_public_klines_1h.csv", coin, "BINANCE_SPOT_PUBLIC_KLINES_RESEARCH_ONLY", f"{coin}-USDT")
        _csv(root/"crypto_decision_lab"/"manual_intake"/"hyperliquid_inbox"/f"{coin.lower()}_hyperliquid_public_candles_1h.csv", coin, "HYPERLIQUID_PUBLIC_CANDLES_RESEARCH_ONLY", f"{coin}-USDC-PERP")
    r = build_phase13_binance_hyperliquid_source_comparison_pack(tmp_path/"out", root); p = r["payload"]
    assert p["policy_lock"] == "ACTIVE"; assert p["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"; assert p["coins_count"] == 3; assert p["min_common_timestamps"] == 6; assert p["canonical_data_writes"] == 0; assert p["promotion_allowed"] is False; assert Path(r["html_path"]).exists()

def test_phase13_binance_hyperliquid_source_comparison_pack_has_no_operational_flags(tmp_path):
    r = build_phase13_binance_hyperliquid_source_comparison_pack(tmp_path/"out", tmp_path/"repo"); p = r["payload"]
    for key in ["api_key_present", "authenticated_connection_used", "orders_generated", "real_orders_generated", "real_capital_used", "trading_signal_generated", "executable_signal_generated", "recommendation_generated", "allocation_generated", "portfolio_decision_generated", "operational_decision_allowed"]:
        assert p[key] is False
