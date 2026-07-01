"""CLI for the QRDS evidence remediation plan."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from crypto_decision_lab.reports.evidence_remediation import (
    SAFETY_FLAGS,
    build_remediation_plan,
    default_report_paths,
    write_outputs,
)


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build QRDS evidence remediation plan (research-only).")
    parser.add_argument("--output-dir", default="artifacts/evidence_remediation", help="Output directory for JSON/Markdown/HTML artifacts.")
    parser.add_argument("--symbols", default="BTC-USDT", help="Comma-separated symbols for display metadata.")
    parser.add_argument("--reports", default="", help="Comma-separated prior gate JSON reports. If omitted, known artifact paths are auto-discovered.")
    parser.add_argument("--no-autodiscover", action="store_true", help="Disable default artifact discovery when --reports is omitted.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    symbols = _split_csv(args.symbols) or ["BTC-USDT"]
    report_paths = _split_csv(args.reports)
    if not report_paths and not args.no_autodiscover:
        report_paths = default_report_paths(Path.cwd())

    payload = build_remediation_plan(symbols=symbols, report_paths=report_paths)
    paths = write_outputs(payload, args.output_dir)

    index = {
        "schema": "qrds.evidence_remediation_index.v1",
        "report_name": payload["report_name"],
        "gate_answer": payload["gate_answer"],
        "symbols": payload["symbols"],
        "input_report_count": payload["input_report_count"],
        "ready_gate_count": payload["ready_gate_count"],
        "high_priority_gap_count": payload["high_priority_gap_count"],
        "policy_lock": payload["policy_lock"],
        "html_path": paths["html_path"],
        "report_path": paths["report_path"],
        "markdown_path": paths["markdown_path"],
        "index_path": paths["index_path"],
        "serve_entrypoint": paths["html_path"],
        "report_payload_sha256": payload["report_payload_sha256"],
        **SAFETY_FLAGS,
    }
    print(json.dumps(index, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
