"""CLI for QRDS Research Promotion Gate Matrix."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from crypto_decision_lab.reports.evidence_timeline import EvidenceTimelineError
from crypto_decision_lab.reports.research_promotion import (
    ResearchPromotionError,
    build_fixture_promotion_reports,
    load_report_payloads,
    parse_paths,
    parse_symbols,
    write_research_promotion_matrix,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qrds-research-promotion",
        description="Build a research-only Research Promotion Gate Matrix dashboard.",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/research_promotion",
        help="Output directory for JSON, Markdown and HTML artifacts.",
    )
    parser.add_argument(
        "--reports",
        default=None,
        help="Comma-separated paths to 8L/8M/8N report or index JSON files. If omitted, deterministic fixtures are used.",
    )
    parser.add_argument(
        "--symbols",
        default="BTC-USDT,ETH-USDT,SOL-USDT",
        help="Comma-separated symbols used only when --reports is not supplied.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        report_paths = parse_paths(args.reports)
        if report_paths:
            evidence_reports = load_report_payloads([Path(path) for path in report_paths])
        else:
            evidence_reports = build_fixture_promotion_reports(parse_symbols(args.symbols))

        index = write_research_promotion_matrix(
            evidence_reports=evidence_reports,
            output_dir=args.output_dir,
        )
    except (ResearchPromotionError, EvidenceTimelineError) as exc:  # type: ignore[name-defined]
        parser.exit(2, f"QRDS Research Promotion failed: {exc}\n")
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        parser.exit(2, f"QRDS Research Promotion failed: {exc}\n")

    print(json.dumps(index, indent=2, sort_keys=True))
    print(f"\n[QRDS 8O] Research Promotion Matrix generated: {index['html_path']}")
    print("[QRDS 8O] Scope: research workflow only; no signal, no recommendation, no order.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
