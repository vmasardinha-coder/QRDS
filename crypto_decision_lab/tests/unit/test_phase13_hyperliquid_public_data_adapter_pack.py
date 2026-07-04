import csv
from pathlib import Path

from crypto_decision_lab.reports.phase13_hyperliquid_public_data_adapter_pack import build_phase13_hyperliquid_public_data_adapter_pack


def test_phase13_hyperliquid_public_data_adapter_pack_builds_existing_files(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    inbox = root / "crypto_decision_lab" / "manual_intake" / "hyperliquid_inbox"
    inbox.mkdir(parents=True)
    p = inbox / "btc_hyperliquid_public_candles_1h.csv"
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["timestamp", "open", "high", "low", "close", "volume", "symbol", "coin", "interval", "source", "venue"])
        w.writeheader()
        for i in range(3):
            price = 100 + i
            w.writerow(
                {
                    "timestamp": f"2026-01-01T0{i}:00:00Z",
                    "open": price,
                    "high": price + 1,
                    "low": price - 1,
                    "close": price + 0.5,
                    "volume": 1000 + i,
                    "symbol": "BTC-USDC-PERP",
                    "coin": "BTC",
                    "interval": "1h",
                    "source": "HYPERLIQUID_PUBLIC_CANDLES_RESEARCH_ONLY",
                    "venue": "HYPERLIQUID",
                }
            )
    result = build_phase13_hyperliquid_public_data_adapter_pack(tmp_path / "out", root, coins=["BTC"], rows_per_coin=3, fetch=False)
    payload = result["payload"]
    assert payload["policy_lock"] == "ACTIVE"
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["hyperliquid_file_count"] == 1
    assert payload["hyperliquid_rows_total"] == 3
    assert payload["exchange_endpoint_used"] is False
    assert payload["authenticated_connection_used"] is False
    assert payload["canonical_data_writes"] == 0
    assert payload["promotion_allowed"] is False
    assert Path(result["html_path"]).exists()


def test_phase13_hyperliquid_public_data_adapter_pack_has_no_operational_flags(tmp_path: Path) -> None:
    result = build_phase13_hyperliquid_public_data_adapter_pack(tmp_path / "out", tmp_path / "repo", coins=["BTC"], rows_per_coin=3, fetch=False)
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
