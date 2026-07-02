from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.data_source_contract import build_data_source_contract


def _split_reports(value: str | None) -> list[str]:
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Data Source Contract / Canonical Schema Pack.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--symbols", default="BTC-USDT,ETH-USDT,SOL-USDT")
    parser.add_argument("--reports", default="")
    parser.add_argument("--max-files", type=int, default=300)
    args = parser.parse_args(argv)

    result = build_data_source_contract(
        output_dir=Path(args.output_dir),
        symbols=args.symbols,
        reports=_split_reports(args.reports),
        max_files=args.max_files,
    )
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
