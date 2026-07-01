"""CLI for QRDS Evidence Timeline / Gate History Registry."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from crypto_decision_lab.reports.evidence_drilldown import EvidenceDrilldownError
from crypto_decision_lab.reports.evidence_timeline import (
    EvidenceTimelineError,
    build_fixture_evidence_reports,
    load_report_payloads,
    parse_paths,
    parse_symbols,
    write_evidence_timeline,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qrds-evidence-timeline",
        description="Build a research-only Evidence Timeline / Gate History Registry dashboard.",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/evidence_timeline",
        help="Output directory for JSON, Markdown and HTML artifacts.",
    )
    parser.add_argument(
        "--reports",
        default=None,
        help="Comma-separated paths to 8L/8M report or index JSON files. If omitted, deterministic fixtures are used.",
    )
    parser.add_argument(
        "--symbols",
        default="BTC-USDT,ETH-USDT,SOL-USDT",
        help="Comma-separated symbols used only when --reports is not supplied.",
    )
    parser.add_argument("--min-observations", type=int, default=3)
    parser.add_argument("--min-latest-score", type=float, default=0.50)
    parser.add_argument("--min-consistency-rate", type=float, default=0.67)
    parser.add_argument("--max-allowed-regression", type=float, default=0.15)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        report_paths = parse_paths(args.reports)
        if report_paths:
            evidence_reports = load_report_payloads([Path(path) for path in report_paths])
        else:
            evidence_reports = build_fixture_evidence_reports(parse_symbols(args.symbols))

        index = write_evidence_timeline(
            evidence_reports=evidence_reports,
            output_dir=args.output_dir,
            min_observations=args.min_observations,
            min_latest_score=args.min_latest_score,
            min_consistency_rate=args.min_consistency_rate,
            max_allowed_regression=args.max_allowed_regression,
        )
    except (EvidenceTimelineError, EvidenceDrilldownError) as exc:  # type: ignore[name-defined]
        parser.exit(2, f"QRDS Evidence Timeline failed: {exc}\n")
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        parser.exit(2, f"QRDS Evidence Timeline failed: {exc}\n")

    print(json.dumps(index, indent=2, sort_keys=True))
    print(f"\n[QRDS 8N] Evidence Timeline generated: {index['html_path']}")
    print("[QRDS 8N] Scope: research history only; no signal, no recommendation, no order.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
