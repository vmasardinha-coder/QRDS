from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.canonical_data_collection_dry_run import build_canonical_data_collection_dry_run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Canonical Data Collection Dry Run.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--symbols", default="BTC-USDT,ETH-USDT,SOL-USDT")
    parser.add_argument("--target-rows-per-symbol", type=int, default=5000)
    parser.add_argument("--interval", default="1h")
    args = parser.parse_args(argv)

    result = build_canonical_data_collection_dry_run(
        output_dir=Path(args.output_dir),
        repo_root=args.repo_root or None,
        symbols=args.symbols,
        target_rows_per_symbol=args.target_rows_per_symbol,
        interval=args.interval,
    )
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
