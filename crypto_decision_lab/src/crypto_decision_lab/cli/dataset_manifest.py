from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.dataset_manifest import build_dataset_manifest_pack


def _split_reports(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Dataset Manifest Pack.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--symbols", default="BTC-USDT,ETH-USDT,SOL-USDT")
    parser.add_argument("--reports", default="")
    args = parser.parse_args(argv)

    result = build_dataset_manifest_pack(
        output_dir=Path(args.output_dir),
        symbols=args.symbols,
        reports=_split_reports(args.reports),
    )
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
