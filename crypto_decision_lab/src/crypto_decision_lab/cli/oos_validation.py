"""CLI for QRDS Out-of-Sample Validation Gate."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from crypto_decision_lab.reports.oos_validation import generate_oos_validation_gate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a QRDS/QOS out-of-sample validation gate packet. Research-only; no signal, recommendation, allocation, order, or operational decision.",
    )
    parser.add_argument("--output-dir", default="artifacts/oos_validation", help="Output directory for HTML/JSON/Markdown artifacts.")
    parser.add_argument("--symbols", default="BTC-USDT", help="Comma-separated symbols for validation context.")
    parser.add_argument("--reports", default="", help="Optional comma-separated input report JSON files from prior gates.")
    parser.add_argument("--min-splits", type=int, default=6, help="Minimum walk-forward split count expected for OOS readiness.")
    parser.add_argument("--min-train-rows", type=int, default=1000, help="Minimum training row coverage expected for OOS readiness.")
    parser.add_argument("--min-test-rows", type=int, default=250, help="Minimum held-out/OOS row coverage expected for OOS readiness.")
    parser.add_argument("--max-leakage-alerts", type=int, default=0, help="Maximum acceptable leakage/embargo alerts.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    index = generate_oos_validation_gate(
        output_dir=Path(args.output_dir),
        symbols=args.symbols,
        reports=args.reports,
        min_splits=args.min_splits,
        min_train_rows=args.min_train_rows,
        min_test_rows=args.min_test_rows,
        max_leakage_alerts=args.max_leakage_alerts,
        base_dir=Path.cwd(),
    )
    print(json.dumps(index, indent=2, sort_keys=True))
    print(f"\n[QRDS 8Q] OOS Validation Gate generated: {index['html_path']}", file=sys.stderr)
    print("[QRDS 8Q] Scope: research validation only; no signal, no recommendation, no order.", file=sys.stderr)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
