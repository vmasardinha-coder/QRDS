from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.dataset_depth_requirements import build_dataset_depth_requirements


def _split_reports(value: str | None) -> list[str]:
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Dataset Depth Requirements.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--symbols", default="BTC-USDT,ETH-USDT,SOL-USDT")
    parser.add_argument("--reports", default="")
    parser.add_argument("--scan-local", action="store_true", help="Optionally scan canonical local data under crypto_decision_lab/data/.")
    parser.add_argument("--no-scan-local", action="store_true", help="Compatibility flag: do not scan local data.")
    args = parser.parse_args(argv)

    result = build_dataset_depth_requirements(
        output_dir=Path(args.output_dir),
        symbols=args.symbols,
        reports=_split_reports(args.reports),
        scan_local=bool(args.scan_local),
        no_scan_local=bool(args.no_scan_local),
    )
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
