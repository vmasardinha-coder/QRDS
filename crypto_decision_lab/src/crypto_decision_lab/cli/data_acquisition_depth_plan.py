from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.data_acquisition_depth_plan import build_data_acquisition_depth_plan


def _split_reports(value: str | None) -> list[str]:
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Data Acquisition Depth Plan.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--symbols", default="BTC-USDT,ETH-USDT,SOL-USDT")
    parser.add_argument("--reports", default="")
    parser.add_argument("--min-rows-per-symbol", type=int, default=5000)
    parser.add_argument("--interval", default="1h")
    args = parser.parse_args(argv)

    result = build_data_acquisition_depth_plan(
        output_dir=Path(args.output_dir),
        symbols=args.symbols,
        reports=_split_reports(args.reports),
        min_rows_per_symbol=args.min_rows_per_symbol,
        interval=args.interval,
    )
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
