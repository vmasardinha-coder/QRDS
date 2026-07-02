from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.data_profile import build_data_profile_pack


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Data Profile Pack.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--symbols", default="BTC-USDT,ETH-USDT,SOL-USDT")
    parser.add_argument("--reports", default="")
    parser.add_argument("--manifest-reports", default="")
    args = parser.parse_args(argv)

    result = build_data_profile_pack(
        output_dir=Path(args.output_dir),
        symbols=args.symbols,
        reports=_split_csv(args.reports),
        manifest_reports=_split_csv(args.manifest_reports),
    )
    print(json.dumps({k: v for k, v in result.items() if k != "payload"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
