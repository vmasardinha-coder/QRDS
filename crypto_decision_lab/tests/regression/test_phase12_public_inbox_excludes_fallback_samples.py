import csv
import json
from pathlib import Path

from crypto_decision_lab.reports.phase10_offline_sample_intake_promotion_pack import build_phase10_offline_sample_intake_promotion_pack


def test_public_inbox_files_exclude_artifact_fallback_samples(tmp_path: Path) -> None:
    root = tmp_path / "repo"

    prior = root / "crypto_decision_lab" / "artifacts" / "phase10_offline_intake_validation_pack" / "phase10_offline_intake_validation_pack_index.json"
    prior.parent.mkdir(parents=True)
    prior.write_text(
        json.dumps(
            {
                "gate_answer": "PHASE10_OFFLINE_INTAKE_VALIDATION_PACK_READY_RESEARCH_ONLY",
                "payload": {
                    "template_validations": [
                        {"symbol": "BTC-USDT", "interval": "1h", "valid": True, "template_path": "template"}
                    ]
                },
            }
        ),
        encoding="utf-8",
    )

    inbox = root / "crypto_decision_lab" / "manual_intake" / "inbox"
    inbox.mkdir(parents=True)
    public_file = inbox / "btc_usdt_binance_public_klines_1h.csv"
    with public_file.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["timestamp", "open", "high", "low", "close", "volume", "symbol", "interval", "source"],
        )
        w.writeheader()
        for i in range(5):
            w.writerow(
                {
                    "timestamp": f"2026-01-02T0{i}:00:00Z",
                    "open": 100 + i,
                    "high": 101 + i,
                    "low": 99 + i,
                    "close": 100.5 + i,
                    "volume": 1000 + i,
                    "symbol": "BTC-USDT",
                    "interval": "1h",
                    "source": "BINANCE_SPOT_PUBLIC_KLINES_RESEARCH_ONLY",
                }
            )

    result = build_phase10_offline_sample_intake_promotion_pack(tmp_path / "out", root)
    payload = result["payload"]

    assert payload["files_validated"] == 1
    assert payload["valid_rows"] == 5
    assert payload["staging_rows"] == 5
    assert payload["canonical_data_writes"] == 0
    assert payload["promotion_allowed"] is False
    assert payload["validated_staging_manifest"]["entries"][0]["source_file"].endswith("btc_usdt_binance_public_klines_1h.csv")
