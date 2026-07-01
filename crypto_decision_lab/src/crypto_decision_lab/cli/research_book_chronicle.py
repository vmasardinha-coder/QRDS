"""CLI for QRDS/QOS research book chronicle."""

from __future__ import annotations

import argparse
from pathlib import Path

from crypto_decision_lab.reports.research_book_chronicle import build_research_book_chronicle, result_to_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the QRDS/QOS research book chronicle.")
    parser.add_argument("--output-dir", default="artifacts/research_book_chronicle")
    parser.add_argument("--symbols", default="BTC-USDT,ETH-USDT,SOL-USDT")
    parser.add_argument("--book-dir", default="docs/book")
    parser.add_argument("--docs-dir", default="docs")
    parser.add_argument("--no-sync-policy-docs", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_research_book_chronicle(
        Path(args.output_dir),
        symbols=args.symbols,
        book_dir=Path(args.book_dir),
        docs_dir=Path(args.docs_dir),
        sync_policy_docs=not args.no_sync_policy_docs,
    )
    print(result_to_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
