"""CLI for QRDS/QOS legacy book intake."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from crypto_decision_lab.reports.research_book_legacy_intake import build_legacy_book_intake


def main() -> None:
    parser = argparse.ArgumentParser(description="Build QRDS legacy research-book intake packet.")
    parser.add_argument("--output-dir", default="artifacts/research_book_legacy_intake")
    parser.add_argument("--symbols", default="BTC-USDT,ETH-USDT,SOL-USDT")
    parser.add_argument("--book-dir", default="docs/book")
    parser.add_argument("--imports-dir", default=None)
    args = parser.parse_args()
    result = build_legacy_book_intake(
        args.output_dir,
        args.symbols,
        book_dir=args.book_dir,
        imports_dir=args.imports_dir,
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
