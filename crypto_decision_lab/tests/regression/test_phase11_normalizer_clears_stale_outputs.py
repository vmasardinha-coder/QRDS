import csv
from pathlib import Path

from crypto_decision_lab.reports.phase11_offline_source_normalizer_pack import build_phase11_offline_source_normalizer_pack


def test_phase11_normalizer_clears_stale_normalized_outputs(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    out = tmp_path / "out"
    stale = out / "normalized" / "stale_fallback.jsonl"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text('{"symbol":"BTC-USDT","source":"SAMPLE_FALLBACK_RESEARCH_ONLY"}\n', encoding="utf-8")

    inbox = root / "crypto_decision_lab" / "manual_intake" / "inbox"
    inbox.mkdir(parents=True)
    public_file = inbox / "btc_usdt_binance_public_klines_1h.csv"
    with public_file.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["timestamp", "open", "high", "low", "close", "volume", "symbol", "interval", "source"])
        w.writeheader()
        w.writerow(
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "open": 100,
                "high": 101,
                "low": 99,
                "close": 100.5,
                "volume": 1000,
                "symbol": "BTC-USDT",
                "interval": "1h",
                "source": "BINANCE_SPOT_PUBLIC_KLINES_RESEARCH_ONLY",
            }
        )

    result = build_phase11_offline_source_normalizer_pack(out, root)
    payload = result["payload"]

    assert payload["rows_normalized"] == 1
    assert not stale.exists()
    normalized_files = list((out / "normalized").glob("*.jsonl"))
    assert len(normalized_files) == 1
    assert "BINANCE_SPOT_PUBLIC_KLINES_RESEARCH_ONLY" in normalized_files[0].read_text(encoding="utf-8")
