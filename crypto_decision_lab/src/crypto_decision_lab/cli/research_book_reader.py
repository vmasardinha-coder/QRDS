"""CLI for the QRDS research book reader portal."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_decision_lab.reports.research_book_reader import build_research_book_reader


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build QRDS research-only book reader portal.")
    parser.add_argument("--output-dir", default="artifacts/research_book_reader", help="Output directory for generated portal artifacts.")
    parser.add_argument("--symbols", default="BTC-USDT,ETH-USDT,SOL-USDT", help="Comma-separated research symbols for metadata only.")
    parser.add_argument("--source-root", default=".", help="crypto_decision_lab root containing docs/book.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_research_book_reader(Path(args.output_dir), args.symbols, source_root=Path(args.source_root))
    summary = {
        "schema": payload["schema"],
        "report_name": payload["report_name"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "planned_chapter_count": payload["planned_chapter_count"],
        "chapter_source_found_count": payload["chapter_source_found_count"],
        "legacy_file_count": payload["legacy_file_count"],
        "html_path": payload["html_path"],
        "markdown_path": payload["markdown_path"],
        "pdf_path": payload["pdf_path"],
        "report_path": payload["report_path"],
        "report_payload_sha256": payload["report_payload_sha256"],
        "orders_generated": payload["orders_generated"],
        "trading_signal_generated": payload["trading_signal_generated"],
        "recommendation_generated": payload["recommendation_generated"],
        "allocation_generated": payload["allocation_generated"],
        "operational_decision_allowed": payload["operational_decision_allowed"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
