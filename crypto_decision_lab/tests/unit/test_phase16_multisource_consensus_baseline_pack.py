import csv
import json
from pathlib import Path

from crypto_decision_lab.reports.phase16_multisource_consensus_baseline_pack import build_phase16_multisource_consensus_baseline_pack


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _write_rows(path: Path, source: str, symbol: str, rows: int = 6, offset: float = 0.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["timestamp", "open", "high", "low", "close", "volume", "symbol", "source"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i in range(rows):
            price = 100 + i + offset
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


def test_phase16_multisource_consensus_baseline_builds(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write_json(
        root / "crypto_decision_lab/artifacts/phase15_multisource_trust_registry_comparison_pack/phase15_multisource_trust_registry_comparison_pack_index.json",
        {
            "gate_answer": "PHASE15_MULTISOURCE_TRUST_REGISTRY_COMPARISON_READY_RESEARCH_ONLY",
            "multisource_comparison_ready": True,
            "ready_sources": ["BINANCE_SPOT", "HYPERLIQUID_PERP", "OKX_SWAP"],
            "pending_source_count": 1,
        },
    )

    for coin in ["BTC", "ETH", "SOL"]:
        _write_rows(root / "crypto_decision_lab/manual_intake/inbox" / f"{coin.lower()}_usdt_binance_public_klines_1h.csv", "BINANCE_SPOT_PUBLIC_KLINES_RESEARCH_ONLY", f"{coin}-USDT", offset=0.0)
        _write_rows(root / "crypto_decision_lab/manual_intake/hyperliquid_inbox" / f"{coin.lower()}_hyperliquid_public_candles_1h.csv", "HYPERLIQUID_PUBLIC_CANDLES_RESEARCH_ONLY", f"{coin}-USDC-PERP", offset=0.1)
        _write_rows(root / "crypto_decision_lab/manual_intake/okx_inbox" / f"{coin.lower()}_usdt_swap_okx_public_candles_1h.csv", "OKX_PUBLIC_CANDLES_RESEARCH_ONLY", f"{coin}-USDT-SWAP", offset=-0.1)

    result = build_phase16_multisource_consensus_baseline_pack(tmp_path / "out", root, min_common_rows_per_coin=6)
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE16_MULTISOURCE_CONSENSUS_BASELINE_READY_RESEARCH_ONLY"
    assert payload["consensus_baseline_ready"] is True
    assert payload["ready_source_count"] == 3
    assert payload["consensus_rows_total"] == 18
    assert payload["canonical_data_writes"] == 0
    assert payload["promotion_allowed"] is False
    assert payload["safe_apply_allowed"] is False
    assert Path(result["html_path"]).exists()
    for item in payload["consensus_outputs"]:
        assert Path(item["path"]).exists()
        assert item["canonical_write"] is False


def test_phase16_multisource_consensus_baseline_has_no_operational_flags(tmp_path: Path) -> None:
    result = build_phase16_multisource_consensus_baseline_pack(tmp_path / "out", tmp_path / "repo")
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
