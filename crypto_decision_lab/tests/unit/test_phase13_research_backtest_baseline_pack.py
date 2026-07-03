import csv
import json
from pathlib import Path

from crypto_decision_lab.reports.phase13_research_backtest_baseline_pack import build_phase13_research_backtest_baseline_pack


def _write_cert(root: Path, rows: int = 15) -> None:
    p = root / "crypto_decision_lab" / "artifacts" / "phase12_public_data_research_readiness_certification_pack" / "phase12_public_data_research_readiness_certification_pack_index.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(
            {
                "gate_answer": "PHASE12_PUBLIC_DATA_RESEARCH_READY_CERTIFIED_RESEARCH_ONLY",
                "public_data_research_ready": True,
                "public_rows_total": rows,
                "policy_lock": "ACTIVE",
                "app_mode": "INTERACTIVE_RESEARCH_ONLY",
            }
        ),
        encoding="utf-8",
    )


def _write_acceptance(root: Path, rows: int = 15) -> None:
    p = root / "crypto_decision_lab" / "artifacts" / "phase11_data_drop_acceptance_pipeline_pack" / "phase11_data_drop_acceptance_pipeline_pack_index.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(
            {
                "gate_answer": "PHASE11_DATA_DROP_ACCEPTANCE_PIPELINE_READY_INBOX_DATA_RESEARCH_ONLY",
                "data_drop_mode": "INBOX_DATA",
                "rows_normalized": rows,
                "policy_lock": "ACTIVE",
                "app_mode": "INTERACTIVE_RESEARCH_ONLY",
            }
        ),
        encoding="utf-8",
    )


def _write_inbox(root: Path) -> None:
    inbox = root / "crypto_decision_lab" / "manual_intake" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    for sym in ["BTC-USDT", "ETH-USDT", "SOL-USDT"]:
        safe = sym.lower().replace("-", "_")
        p = inbox / f"{safe}_binance_public_klines_1h.csv"
        with p.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["timestamp", "open", "high", "low", "close", "volume", "symbol", "interval", "source"])
            w.writeheader()
            for i in range(5):
                price = 100 + i
                w.writerow(
                    {
                        "timestamp": f"2026-01-01T0{i}:00:00Z",
                        "open": price,
                        "high": price + 1,
                        "low": price - 1,
                        "close": price + 0.5,
                        "volume": 1000 + i,
                        "symbol": sym,
                        "interval": "1h",
                        "source": "BINANCE_SPOT_PUBLIC_KLINES_RESEARCH_ONLY",
                    }
                )


def test_phase13_research_backtest_baseline_pack_builds_metrics(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write_cert(root, rows=15)
    _write_acceptance(root, rows=15)
    _write_inbox(root)

    result = build_phase13_research_backtest_baseline_pack(tmp_path / "out", root)
    payload = result["payload"]

    assert payload["policy_lock"] == "ACTIVE"
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["public_data_research_ready"] is True
    assert payload["rows_analyzed"] == 15
    assert payload["symbols_count"] == 3
    assert len(payload["symbol_metrics"]) == 3
    assert payload["canonical_data_writes"] == 0
    assert payload["promotion_allowed"] is False
    assert payload["safe_apply_allowed"] is False
    assert Path(result["html_path"]).exists()


def test_phase13_research_backtest_baseline_pack_has_no_operational_flags(tmp_path: Path) -> None:
    result = build_phase13_research_backtest_baseline_pack(tmp_path / "out", tmp_path / "repo")
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
