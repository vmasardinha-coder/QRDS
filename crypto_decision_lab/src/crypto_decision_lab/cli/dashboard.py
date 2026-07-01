"""CLI for QRDS Static Research Dashboard v1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from crypto_decision_lab.cli.multi_asset_report import run_multi_asset_report_from_fixtures
from crypto_decision_lab.reports.dashboard import write_static_dashboard
from crypto_decision_lab.reports.stress import write_scenario_stress_pack


def _parse_symbols(value: str | None) -> tuple[str, ...] | None:
    if value is None or not value.strip():
        return None
    return tuple(symbol.strip().upper() for symbol in value.split(",") if symbol.strip())


def run_dashboard_from_fixtures(
    *,
    fixture_dir: str | Path,
    output_dir: str | Path,
    symbols: tuple[str, ...] | None = None,
    dashboard_name: str = "qrds-static-research-dashboard",
) -> dict:
    """Run multi-asset + stress pipeline and render dashboard."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    multi_index = run_multi_asset_report_from_fixtures(
        fixture_dir=fixture_dir,
        output_dir=root / "sources" / "multi_asset",
        symbols=symbols,
        report_name=f"{dashboard_name}-multi-asset-source",
    )

    stress_index = write_scenario_stress_pack(
        multi_asset_index_path=multi_index["index_path"],
        output_dir=root / "sources" / "scenario_stress",
        pack_name=f"{dashboard_name}-stress-source",
    )

    return write_static_dashboard(
        multi_asset_index_path=multi_index["index_path"],
        scenario_stress_index_path=stress_index["index_path"],
        output_dir=root / "dashboard",
        dashboard_name=dashboard_name,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qrds-dashboard",
        description="Generate a static offline QRDS research dashboard.",
    )
    parser.add_argument("--output-dir", required=True, help="Output directory.")
    parser.add_argument("--fixture-dir", default="data/fixtures/okx_public", help="OKX public fixture directory.")
    parser.add_argument("--symbols", default=None, help="Optional comma-separated symbols.")
    parser.add_argument("--dashboard-name", default="qrds-static-research-dashboard", help="Dashboard name.")
    parser.add_argument("--multi-asset-index", default=None, help="Optional existing multi-asset index path.")
    parser.add_argument("--scenario-stress-index", default=None, help="Optional existing scenario stress index path.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.multi_asset_index and args.scenario_stress_index:
        index = write_static_dashboard(
            multi_asset_index_path=args.multi_asset_index,
            scenario_stress_index_path=args.scenario_stress_index,
            output_dir=Path(args.output_dir) / "dashboard",
            dashboard_name=args.dashboard_name,
        )
    else:
        index = run_dashboard_from_fixtures(
            fixture_dir=args.fixture_dir,
            output_dir=args.output_dir,
            symbols=_parse_symbols(args.symbols),
            dashboard_name=args.dashboard_name,
        )

    print(json.dumps(index, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
