from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.dataset_depth_requirements import build_dataset_depth_requirements


def _split_reports(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Dataset Depth Requirements packet.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--symbols", default="BTC-USDT,ETH-USDT,SOL-USDT")
    parser.add_argument("--reports", default="")
    parser.add_argument("--min-total-rows", type=int, default=3000)
    parser.add_argument("--min-rows-per-symbol", type=int, default=1000)
    parser.add_argument("--no-scan-local", action="store_true")
    args = parser.parse_args(argv)

    result = build_dataset_depth_requirements(
        output_dir=Path(args.output_dir),
        symbols=args.symbols,
        reports=_split_reports(args.reports),
        min_total_rows=args.min_total_rows,
        min_rows_per_symbol=args.min_rows_per_symbol,
        scan_local=not args.no_scan_local,
    )
    printable = {k: v for k, v in result.items() if k != "payload"}
    print(json.dumps(printable, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
