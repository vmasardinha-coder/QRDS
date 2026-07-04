from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.phase14_bybit_public_data_adapter_pack import build_phase14_bybit_public_data_adapter_pack


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Phase 14 Bybit Public Data Adapter Pack.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--symbols", default="BTCUSDT,ETHUSDT,SOLUSDT")
    parser.add_argument("--category", default="linear")
    parser.add_argument("--interval", default="60")
    parser.add_argument("--rows-per-symbol", type=int, default=5000)
    parser.add_argument("--no-fetch", action="store_true")
    args = parser.parse_args(argv)
    symbols = [x.strip().upper() for x in args.symbols.split(",") if x.strip()]
    result = build_phase14_bybit_public_data_adapter_pack(
        Path(args.output_dir),
        args.repo_root or None,
        symbols=symbols,
        category=args.category,
        interval=args.interval,
        rows_per_symbol=args.rows_per_symbol,
        fetch=not args.no_fetch,
    )
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
