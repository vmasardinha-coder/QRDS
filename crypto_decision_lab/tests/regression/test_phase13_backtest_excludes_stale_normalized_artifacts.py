import json
from pathlib import Path

from crypto_decision_lab.reports.phase13_research_backtest_baseline_pack import build_phase13_research_backtest_baseline_pack


def _write_jsonl(path: Path, symbol: str, rows: int, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for i in range(rows):
        price = 100 + i
        lines.append(
            json.dumps(
                {
                    "timestamp": f"2026-01-01T{i:02d}:00:00Z",
                    "open": price,
                    "high": price + 1,
                    "low": price - 1,
                    "close": price + 0.5,
                    "volume": 1000 + i,
                    "symbol": symbol,
                    "interval": "1h",
                    "source": source,
                },
                sort_keys=True,
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_phase13_backtest_uses_normalizer_manifest_not_stale_glob(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    norm_dir = root / "crypto_decision_lab" / "artifacts" / "phase11_offline_source_normalizer_pack" / "normalized"

    current_paths = []
    for symbol in ["BTC-USDT", "ETH-USDT", "SOL-USDT"]:
        safe = symbol.lower().replace("-", "_")
        p = norm_dir / f"{safe}_current_public.jsonl"
        _write_jsonl(p, symbol, 5, "BINANCE_SPOT_PUBLIC_KLINES_RESEARCH_ONLY")
        current_paths.append(str(p))

    _write_jsonl(norm_dir / "btc_usdt_stale_fallback.jsonl", "BTC-USDT", 5, "SAMPLE_FALLBACK_RESEARCH_ONLY")

    index = root / "crypto_decision_lab" / "artifacts" / "phase11_offline_source_normalizer_pack" / "phase11_offline_source_normalizer_pack_index.json"
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(
        json.dumps(
            {
                "gate_answer": "PHASE11_OFFLINE_SOURCE_NORMALIZER_READY_WITH_INBOX_FILES_RESEARCH_ONLY",
                "payload": {
                    "normalization_outputs": [{"path": p, "rows": 5} for p in current_paths],
                    "rows_normalized": 15,
                },
            }
        ),
        encoding="utf-8",
    )

    cert = root / "crypto_decision_lab" / "artifacts" / "phase12_public_data_research_readiness_certification_pack" / "phase12_public_data_research_readiness_certification_pack_index.json"
    cert.parent.mkdir(parents=True, exist_ok=True)
    cert.write_text(
        json.dumps(
            {
                "gate_answer": "PHASE12_PUBLIC_DATA_RESEARCH_READY_CERTIFIED_RESEARCH_ONLY",
                "public_data_research_ready": True,
                "public_rows_total": 15,
                "policy_lock": "ACTIVE",
                "app_mode": "INTERACTIVE_RESEARCH_ONLY",
            }
        ),
        encoding="utf-8",
    )

    accept = root / "crypto_decision_lab" / "artifacts" / "phase11_data_drop_acceptance_pipeline_pack" / "phase11_data_drop_acceptance_pipeline_pack_index.json"
    accept.parent.mkdir(parents=True, exist_ok=True)
    accept.write_text(
        json.dumps(
            {
                "gate_answer": "PHASE11_DATA_DROP_ACCEPTANCE_PIPELINE_READY_INBOX_DATA_RESEARCH_ONLY",
                "data_drop_mode": "INBOX_DATA",
                "rows_normalized": 15,
                "policy_lock": "ACTIVE",
                "app_mode": "INTERACTIVE_RESEARCH_ONLY",
            }
        ),
        encoding="utf-8",
    )

    result = build_phase13_research_backtest_baseline_pack(tmp_path / "out", root)
    payload = result["payload"]

    assert payload["rows_analyzed"] == 15
    assert payload["symbols_count"] == 3
    assert all("stale_fallback" not in p for p in payload["input_paths_checked"])
    assert payload["canonical_data_writes"] == 0
    assert payload["promotion_allowed"] is False
