from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.dataset_evidence_scanner import build_dataset_evidence_scan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Dataset Evidence Scanner packet.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--symbols", default="BTC-USDT,ETH-USDT,SOL-USDT")
    parser.add_argument("--scan-roots", default="")
    parser.add_argument("--min-rows-per-symbol", type=int, default=1000)
    args = parser.parse_args(argv)

    result = build_dataset_evidence_scan(
        output_dir=Path(args.output_dir),
        symbols=args.symbols,
        scan_roots=args.scan_roots or None,
        min_rows_per_symbol=args.min_rows_per_symbol,
    )
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
