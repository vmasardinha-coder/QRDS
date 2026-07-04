import csv
import json
from pathlib import Path

from crypto_decision_lab.reports.phase18_research_feature_regime_diagnostics_pack import build_phase18_research_feature_regime_diagnostics_pack


def _write_phase17_index(root: Path) -> None:
    p = root / "crypto_decision_lab/artifacts/phase17_consensus_quality_drift_monitor_pack/phase17_consensus_quality_drift_monitor_pack_index.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"gate_answer": "READY", "quality_drift_monitor_ready": True}), encoding="utf-8")


def _write_consensus(path: Path, coin: str, rows: int = 200) -> None:
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
            price = 100 + i * 0.1
            w.writerow(
                {
                    "timestamp": f"2026-01-{1 + (i // 24):02d}T{i % 24:02d}:00:00Z",
                    "coin": coin,
                    "source_count": 3,
                    "ready_sources": "BINANCE_SPOT|HYPERLIQUID_PERP|OKX_SWAP",
                    "consensus_close_median": price,
                    "consensus_close_mean": price,
                    "source_close_min": price - 0.05,
                    "source_close_max": price + 0.05,
                    "source_dispersion_bps": 10,
                    "research_only": "true",
                    "source": "QRDS_MULTISOURCE_CONSENSUS_RESEARCH_ONLY",
                    "canonical_write": "false",
                    "trading_signal_generated": "false",
                    "recommendation_generated": "false",
                }
            )


def test_phase18_feature_regime_diagnostics_builds(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write_phase17_index(root)
    for coin in ["BTC", "ETH", "SOL"]:
        _write_consensus(
            root / "crypto_decision_lab/artifacts/phase16_multisource_consensus_baseline_pack/consensus" / f"{coin.lower()}_multisource_consensus_1h.csv",
            coin,
            rows=200,
        )

    import crypto_decision_lab.reports.phase18_research_feature_regime_diagnostics_pack as pack
    pack.MIN_ROWS_PER_COIN = 200
    pack.ROLL_SLOW = 24

    result = build_phase18_research_feature_regime_diagnostics_pack(tmp_path / "out", root)
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE18_RESEARCH_FEATURE_REGIME_DIAGNOSTICS_READY_RESEARCH_ONLY"
    assert payload["feature_regime_diagnostics_ready"] is True
    assert payload["feature_rows_total"] == 600
    assert payload["diagnostic_labels_are_signals"] is False
    assert payload["canonical_data_writes"] == 0
    assert payload["promotion_allowed"] is False
    assert payload["safe_apply_allowed"] is False
    assert Path(result["html_path"]).exists()
    for item in payload["feature_outputs"]:
        assert Path(item["path"]).exists()
        assert item["canonical_write"] is False


def test_phase18_feature_regime_diagnostics_has_no_operational_flags(tmp_path: Path) -> None:
    result = build_phase18_research_feature_regime_diagnostics_pack(tmp_path / "out", tmp_path / "repo")
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
