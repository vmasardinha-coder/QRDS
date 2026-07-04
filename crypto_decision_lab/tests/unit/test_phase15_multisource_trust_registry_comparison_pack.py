import csv
import json
from pathlib import Path

from crypto_decision_lab.reports.phase15_multisource_trust_registry_comparison_pack import build_phase15_multisource_trust_registry_comparison_pack


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _write_rows(path: Path, coin: str, source: str, symbol: str, rows: int = 6) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["timestamp", "open", "high", "low", "close", "volume", "symbol", "source"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i in range(rows):
            price = 100 + i
            w.writerow(
                {
                    "timestamp": f"2026-01-01T0{i}:00:00Z",
                    "open": price,
                    "high": price + 1,
                    "low": price - 1,
                    "close": price + 0.5,
                    "volume": 1000 + i,
                    "symbol": symbol,
                    "source": source,
                }
            )


def test_phase15_multisource_registry_builds_with_bybit_pending(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write_json(root / "crypto_decision_lab/artifacts/phase12_public_data_research_readiness_certification_pack/phase12_public_data_research_readiness_certification_pack_index.json", {"gate_answer": "READY", "public_data_research_ready": True, "public_rows_total": 18})
    _write_json(root / "crypto_decision_lab/artifacts/phase13_hyperliquid_public_data_adapter_pack/phase13_hyperliquid_public_data_adapter_pack_index.json", {"gate_answer": "READY", "hyperliquid_adapter_ready": True, "hyperliquid_rows_total": 18})
    _write_json(root / "crypto_decision_lab/artifacts/phase14_okx_public_data_adapter_pack/phase14_okx_public_data_adapter_pack_index.json", {"gate_answer": "READY", "okx_adapter_ready": True, "okx_rows_total": 18})
    _write_json(root / "crypto_decision_lab/artifacts/phase14_bybit_public_data_adapter_pack/phase14_bybit_public_data_adapter_pack_index.json", {"gate_answer": "NEEDS_REVIEW", "bybit_adapter_ready": False, "bybit_rows_total": 0, "endpoint_access_status": "PUBLIC_ENDPOINT_BLOCKED_OR_UNAVAILABLE_RESEARCH_ONLY"})

    for coin in ["BTC", "ETH", "SOL"]:
        _write_rows(root / "crypto_decision_lab/manual_intake/inbox" / f"{coin.lower()}_usdt_binance_public_klines_1h.csv", coin, "BINANCE_SPOT_PUBLIC_KLINES_RESEARCH_ONLY", f"{coin}-USDT")
        _write_rows(root / "crypto_decision_lab/manual_intake/hyperliquid_inbox" / f"{coin.lower()}_hyperliquid_public_candles_1h.csv", coin, "HYPERLIQUID_PUBLIC_CANDLES_RESEARCH_ONLY", f"{coin}-USDC-PERP")
        _write_rows(root / "crypto_decision_lab/manual_intake/okx_inbox" / f"{coin.lower()}_usdt_swap_okx_public_candles_1h.csv", coin, "OKX_PUBLIC_CANDLES_RESEARCH_ONLY", f"{coin}-USDT-SWAP")

    import crypto_decision_lab.reports.phase15_multisource_trust_registry_comparison_pack as pack
    pack.TARGET_ROWS_PER_SYMBOL = 6
    result = build_phase15_multisource_trust_registry_comparison_pack(tmp_path / "out", root)
    payload = result["payload"]

    assert payload["ready_source_count"] == 3
    assert payload["pending_source_count"] == 1
    assert "BYBIT_LINEAR" in [s["source_id"] for s in payload["pending_sources"]]
    assert payload["canonical_data_writes"] == 0
    assert payload["promotion_allowed"] is False
    assert Path(result["html_path"]).exists()


def test_phase15_multisource_registry_has_no_operational_flags(tmp_path: Path) -> None:
    result = build_phase15_multisource_trust_registry_comparison_pack(tmp_path / "out", tmp_path / "repo")
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
