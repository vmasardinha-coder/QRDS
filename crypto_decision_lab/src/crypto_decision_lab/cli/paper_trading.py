"""CLI for the QRDS/QOS Paper Trading Gate."""
from __future__ import annotations

import argparse
import json
from typing import Sequence

from crypto_decision_lab.reports.paper_trading import build_paper_trading_gate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate the QRDS/QOS research-only Paper Trading Gate packet."
    )
    parser.add_argument("--output-dir", required=True, help="Directory where paper-trading artifacts will be written.")
    parser.add_argument("--symbols", default="BTC-USDT", help="Comma-separated research symbols, e.g. BTC-USDT,ETH-USDT.")
    parser.add_argument("--reports", default="", help="Comma-separated prior gate JSON reports, e.g. 8L/8M/8N/8O/8P/8Q artifacts.")
    parser.add_argument("--paper-days", type=int, default=0, help="Paper-only observation days. Default: 0.")
    parser.add_argument("--paper-runs", type=int, default=0, help="Number of simulated/paper research runs. Default: 0.")
    parser.add_argument("--simulated-fill-rate", type=float, default=0.0, help="Observed simulated/paper fill coverage in [0, 1]. Default: 0.")
    parser.add_argument("--cost-model-present", action="store_true", help="Record that explicit cost/slippage tracking evidence is present.")
    parser.add_argument("--paper-artifact-present", action="store_true", help="Record that an external formal paper campaign artifact is present.")
    parser.add_argument(
        "--acceptance-state",
        default="NOT_REVIEWED",
        choices=["NOT_REVIEWED", "UNDER_REVIEW", "REJECTED", "APPROVED_RESEARCH_ONLY"],
        help="Research-only paper review state. This never unlocks operational use.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    index = build_paper_trading_gate(
        output_dir=args.output_dir,
        symbols=args.symbols,
        reports=args.reports,
        paper_days=args.paper_days,
        paper_runs=args.paper_runs,
        simulated_fill_rate=args.simulated_fill_rate,
        cost_model_present=args.cost_model_present,
        paper_artifact_present=args.paper_artifact_present,
        acceptance_state=args.acceptance_state,
    )
    print(json.dumps(index, indent=2, sort_keys=True))
    print()
    print(f"[QRDS 8R] Paper Trading Gate generated: {index['html_path']}")
    print("[QRDS 8R] Scope: paper/research observation only; no signal, no recommendation, no order.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
