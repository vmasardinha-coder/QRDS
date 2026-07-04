from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.phase13_hyperliquid_public_data_adapter_pack import build_phase13_hyperliquid_public_data_adapter_pack


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Phase 13 Hyperliquid Public Data Adapter Pack.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--coins", default="BTC,ETH,SOL")
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--rows-per-coin", type=int, default=5000)
    parser.add_argument("--no-fetch", action="store_true")
    args = parser.parse_args(argv)
    coins = [x.strip().upper() for x in args.coins.split(",") if x.strip()]
    result = build_phase13_hyperliquid_public_data_adapter_pack(
        Path(args.output_dir),
        args.repo_root or None,
        coins=coins,
        interval=args.interval,
        rows_per_coin=args.rows_per_coin,
        fetch=not args.no_fetch,
    )
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
