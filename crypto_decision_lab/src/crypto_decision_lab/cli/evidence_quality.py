"""CLI for QRDS Evidence Quality Gate v1."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from crypto_decision_lab.reports.evidence_quality import (
    EvidenceQualityError,
    load_multi_asset_report_payload,
    load_stress_report_payload,
    write_evidence_quality_gate,
    write_fixture_upstream_inputs,
)


def _parse_symbols(value: str) -> list[str]:
    symbols = [item.strip() for item in value.split(",") if item.strip()]
    if not symbols:
        raise argparse.ArgumentTypeError("--symbols must include at least one symbol")
    return symbols


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate QRDS Evidence Quality Gate v1 artifacts. Research-only; no signals, orders or recommendations.",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/evidence_quality",
        help="Output directory for Evidence Quality Gate artifacts.",
    )
    parser.add_argument(
        "--symbols",
        type=_parse_symbols,
        default=_parse_symbols("BTC-USDT,ETH-USDT,SOL-USDT"),
        help="Comma-separated symbols used when fixture upstream inputs are generated.",
    )
    parser.add_argument(
        "--multi-asset-index",
        default=None,
        help="Optional existing multi-asset report/index JSON. If omitted, deterministic offline fixture inputs are used.",
    )
    parser.add_argument(
        "--stress-index",
        default=None,
        help="Optional existing scenario stress report/index JSON. If omitted, deterministic offline fixture inputs are used.",
    )
    parser.add_argument("--report-name", default="qrds-evidence-quality-gate")
    parser.add_argument("--min-dataset-rows", type=int, default=1000)
    parser.add_argument("--min-walk-forward-splits", type=int, default=3)
    parser.add_argument("--pass-threshold", type=float, default=0.75)
    parser.add_argument("--watch-threshold", type=float, default=0.50)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    output_dir = Path(args.output_dir)

    if args.multi_asset_index:
        multi_asset_report = load_multi_asset_report_payload(args.multi_asset_index)
        if args.stress_index:
            stress_report = load_stress_report_payload(args.stress_index)
        else:
            fixture = write_fixture_upstream_inputs(output_dir / "upstream_research_inputs", args.symbols)
            stress_report = fixture["stress_report"]
    else:
        fixture = write_fixture_upstream_inputs(output_dir / "upstream_research_inputs", args.symbols)
        multi_asset_report = fixture["multi_asset_report"]
        if args.stress_index:
            stress_report = load_stress_report_payload(args.stress_index)
        else:
            stress_report = fixture["stress_report"]

    try:
        index = write_evidence_quality_gate(
            multi_asset_report=multi_asset_report,
            stress_report=stress_report,
            output_dir=output_dir,
            report_name=args.report_name,
            min_dataset_rows=args.min_dataset_rows,
            min_walk_forward_splits=args.min_walk_forward_splits,
            pass_threshold=args.pass_threshold,
            watch_threshold=args.watch_threshold,
        )
    except EvidenceQualityError as exc:
        parser.exit(2, f"QRDS Evidence Quality Gate failed: {exc}\n")

    print(json.dumps(index, indent=2, sort_keys=True))
    print(f"\n[QRDS 8L] Evidence Quality Gate generated: {index['html_path']}")
    print("[QRDS 8L] Scope: research readiness only; no signal, no recommendation, no order.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
