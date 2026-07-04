import csv
import json
from pathlib import Path

from crypto_decision_lab.reports.phase17_consensus_quality_drift_monitor_pack import build_phase17_consensus_quality_drift_monitor_pack


def _write_phase16_index(root: Path) -> None:
    p = root / "crypto_decision_lab/artifacts/phase16_multisource_consensus_baseline_pack/phase16_multisource_consensus_baseline_pack_index.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"gate_answer": "READY", "consensus_baseline_ready": True}), encoding="utf-8")


def _write_consensus(path: Path, coin: str, rows: int = 6) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "timestamp",
        "coin",
        "source_count",
        "ready_sources",
        "consensus_close_median",
        "consensus_close_mean",
        "source_close_min",
        "source_close_max",
        "source_dispersion_bps",
        "BINANCE_SPOT_close",
        "BINANCE_SPOT_deviation_bps",
        "HYPERLIQUID_PERP_close",
        "HYPERLIQUID_PERP_deviation_bps",
        "OKX_SWAP_close",
        "OKX_SWAP_deviation_bps",
        "research_only",
        "source",
        "canonical_write",
        "trading_signal_generated",
        "recommendation_generated",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i in range(rows):
            price = 100 + i
            w.writerow(
                {
                    "timestamp": f"2026-01-01T0{i}:00:00Z",
                    "coin": coin,
                    "source_count": 3,
                    "ready_sources": "BINANCE_SPOT|HYPERLIQUID_PERP|OKX_SWAP",
                    "consensus_close_median": price,
                    "consensus_close_mean": price,
                    "source_close_min": price - 0.05,
                    "source_close_max": price + 0.05,
                    "source_dispersion_bps": 10,
                    "BINANCE_SPOT_close": price,
                    "BINANCE_SPOT_deviation_bps": 0,
                    "HYPERLIQUID_PERP_close": price + 0.01,
                    "HYPERLIQUID_PERP_deviation_bps": 1,
                    "OKX_SWAP_close": price - 0.01,
                    "OKX_SWAP_deviation_bps": -1,
                    "research_only": "true",
                    "source": "QRDS_MULTISOURCE_CONSENSUS_RESEARCH_ONLY",
                    "canonical_write": "false",
                    "trading_signal_generated": "false",
                    "recommendation_generated": "false",
                }
            )


def test_phase17_consensus_quality_drift_monitor_builds(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write_phase16_index(root)
    for coin in ["BTC", "ETH", "SOL"]:
        _write_consensus(
            root / "crypto_decision_lab/artifacts/phase16_multisource_consensus_baseline_pack/consensus" / f"{coin.lower()}_multisource_consensus_1h.csv",
            coin,
            rows=6,
        )

    result = build_phase17_consensus_quality_drift_monitor_pack(tmp_path / "out", root, min_rows_per_coin=6)
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE17_CONSENSUS_QUALITY_DRIFT_MONITOR_READY_RESEARCH_ONLY"
    assert payload["quality_drift_monitor_ready"] is True
    assert payload["quality_rows_total"] == 18
    assert payload["canonical_data_writes"] == 0
    assert payload["promotion_allowed"] is False
    assert payload["safe_apply_allowed"] is False
    assert Path(result["quality_summary_csv"]).exists()
    assert Path(result["html_path"]).exists()


def test_phase17_consensus_quality_drift_monitor_has_no_operational_flags(tmp_path: Path) -> None:
    result = build_phase17_consensus_quality_drift_monitor_pack(tmp_path / "out", tmp_path / "repo")
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
