"""CLI for QRDS Research Report Pack v1."""

from __future__ import annotations

import argparse
import json
from typing import Sequence

from crypto_decision_lab.reports.pack import write_research_report_pack


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qrds-report-pack",
        description="Generate a QRDS research report pack from a full_research output directory.",
    )
    parser.add_argument("--full-research-dir", required=True, help="Directory produced by qrds_full_research.sh.")
    parser.add_argument("--output-dir", required=True, help="Output directory for the report pack.")
    parser.add_argument("--pack-name", default="qrds-research-report-pack", help="Report pack name.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    index = write_research_report_pack(
        full_research_dir=args.full_research_dir,
        output_dir=args.output_dir,
        pack_name=args.pack_name,
    )

    print(json.dumps(index, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
