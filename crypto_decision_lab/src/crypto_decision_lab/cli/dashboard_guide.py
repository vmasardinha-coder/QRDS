"""CLI for QRDS Dashboard Interpretation Guide v1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from crypto_decision_lab.reports.dashboard_guide import write_dashboard_guide


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qrds-dashboard-guide",
        description="Generate QRDS dashboard interpretation guide.",
    )
    parser.add_argument("--output-dir", default="artifacts/dashboard_guide", help="Output directory.")
    parser.add_argument("--guide-name", default="qrds-dashboard-interpretation-guide", help="Guide name.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    index = write_dashboard_guide(
        output_dir=Path(args.output_dir) / "guide",
        guide_name=args.guide_name,
    )

    print(json.dumps(index, indent=2, sort_keys=True, ensure_ascii=False))
    print()
    print("=== DASHBOARD GUIDE READY ===")
    print(index["html_path"])
    print()
    print("=== OPEN FILE ===")
    print(index["html_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
