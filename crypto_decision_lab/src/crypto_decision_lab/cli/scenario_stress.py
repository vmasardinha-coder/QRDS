"""CLI for QRDS Scenario Stress Pack."""

from __future__ import annotations

import argparse
import json
from typing import Sequence

from crypto_decision_lab.reports.stress import write_scenario_stress_pack


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qrds-scenario-stress",
        description="Generate a QRDS scenario stress pack from a multi-asset report index.",
    )
    parser.add_argument("--multi-asset-index", required=True, help="Path to multi_asset_research_index.json.")
    parser.add_argument("--output-dir", required=True, help="Output directory for scenario stress artifacts.")
    parser.add_argument("--pack-name", default="qrds-scenario-stress-pack", help="Stress pack name.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    index = write_scenario_stress_pack(
        multi_asset_index_path=args.multi_asset_index,
        output_dir=args.output_dir,
        pack_name=args.pack_name,
    )

    print(json.dumps(index, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
