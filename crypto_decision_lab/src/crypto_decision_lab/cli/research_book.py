"""CLI for QRDS/QOS research book generation."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from crypto_decision_lab.reports.research_book import build_research_book, sync_book_source_docs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the QRDS/QOS research-only book.")
    parser.add_argument("--output-dir", default="artifacts/research_book", help="Output directory for HTML/Markdown/PDF artifacts.")
    parser.add_argument("--symbols", default="BTC-USDT,ETH-USDT,SOL-USDT", help="Comma-separated symbols for the book header.")
    parser.add_argument("--no-pdf", action="store_true", help="Skip PDF generation.")
    parser.add_argument("--sync-source-docs", action="store_true", help="Regenerate docs/book source chapter files.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.sync_source_docs:
        sync_book_source_docs("docs/book")
    result = build_research_book(args.output_dir, args.symbols, make_pdf=not args.no_pdf)
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
