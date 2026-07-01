"""CLI for QRDS Evidence Drilldown / Data Coverage Gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from crypto_decision_lab.reports.evidence_drilldown import (
    EvidenceDrilldownError,
    build_fixture_evidence_quality_report,
    load_evidence_report_payload,
    parse_symbols,
    write_evidence_drilldown,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qrds-evidence-drilldown",
        description="Build a research-only Evidence Drilldown / Data Coverage Gate dashboard.",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/evidence_drilldown",
        help="Output directory for JSON, Markdown and HTML artifacts.",
    )
    parser.add_argument(
        "--evidence-report",
        default=None,
        help="Optional path to an 8L evidence_quality_gate.json or evidence_quality_index.json.",
    )
    parser.add_argument(
        "--symbols",
        default="BTC-USDT,ETH-USDT,SOL-USDT",
        help="Comma-separated symbols used only when --evidence-report is not supplied.",
    )
    parser.add_argument("--min-dataset-rows", type=int, default=None)
    parser.add_argument("--min-walk-forward-splits", type=int, default=None)
    parser.add_argument("--min-stress-retention-ratio", type=float, default=0.50)
    parser.add_argument("--min-research-readiness-score", type=float, default=0.50)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.evidence_report:
            evidence_report = load_evidence_report_payload(Path(args.evidence_report))
        else:
            evidence_report = build_fixture_evidence_quality_report(parse_symbols(args.symbols))

        index = write_evidence_drilldown(
            evidence_report=evidence_report,
            output_dir=args.output_dir,
            min_dataset_rows=args.min_dataset_rows,
            min_walk_forward_splits=args.min_walk_forward_splits,
            min_stress_retention_ratio=args.min_stress_retention_ratio,
            min_research_readiness_score=args.min_research_readiness_score,
        )
    except EvidenceDrilldownError as exc:
        parser.exit(2, f"QRDS Evidence Drilldown failed: {exc}\n")

    print(json.dumps(index, indent=2, sort_keys=True))
    print(f"\n[QRDS 8M] Evidence Drilldown generated: {index['html_path']}")
    print("[QRDS 8M] Scope: research diagnostic only; no signal, no recommendation, no order.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
