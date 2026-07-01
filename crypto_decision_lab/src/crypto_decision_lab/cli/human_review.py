"""CLI for QRDS Human Review / Policy Lock Gate."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from crypto_decision_lab.reports.human_review import generate_human_review_gate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a QRDS/QOS human review and policy lock gate packet. Research-only; no signal, recommendation, allocation, order, or operational decision.",
    )
    parser.add_argument("--output-dir", default="artifacts/human_review", help="Output directory for HTML/JSON/Markdown artifacts.")
    parser.add_argument("--symbols", default="BTC-USDT", help="Comma-separated symbols for review context.")
    parser.add_argument("--reports", default="", help="Optional comma-separated input report JSON files from 8L/8M/8N/8O.")
    parser.add_argument(
        "--review-state",
        default="NOT_REVIEWED",
        choices=["NOT_REVIEWED", "UNDER_REVIEW", "RESEARCH_APPROVED_WITH_BLOCKERS", "RESEARCH_REJECTED"],
        help="Research-only human review state. This never unlocks operational use.",
    )
    parser.add_argument("--reviewer", default="UNSPECIFIED_RESEARCH_REVIEWER", help="Reviewer label for the research packet.")
    parser.add_argument("--notes", default="", help="Optional human research review notes.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    index = generate_human_review_gate(
        output_dir=Path(args.output_dir),
        symbols=args.symbols,
        reports=args.reports,
        review_state=args.review_state,
        reviewer=args.reviewer,
        notes=args.notes,
        base_dir=Path.cwd(),
    )
    print(json.dumps(index, indent=2, sort_keys=True))
    print(f"\n[QRDS 8P] Human Review / Policy Lock generated: {index['html_path']}", file=sys.stderr)
    print("[QRDS 8P] Scope: research review only; no signal, no recommendation, no order.", file=sys.stderr)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
