"""CLI for QRDS Dashboard Hub v1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from crypto_decision_lab.cli.dashboard_charts import run_dashboard_charts_from_fixtures
from crypto_decision_lab.cli.dashboard_refresh import parse_symbols
from crypto_decision_lab.cli.dashboard_ui import run_dashboard_ui_from_fixtures
from crypto_decision_lab.reports.dashboard_hub import write_dashboard_hub


def run_dashboard_hub_from_fixtures(
    *,
    output_dir: str | Path,
    fixture_dir: str | Path = "data/fixtures/okx_public",
    symbols: tuple[str, ...] | None = ("BTC-USDT", "ETH-USDT", "SOL-USDT"),
    hub_name: str = "qrds-dashboard-hub",
) -> dict:
    """Generate dashboard pages and hub from fixtures."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    ui_index = run_dashboard_ui_from_fixtures(
        output_dir=root / "interactive_page",
        fixture_dir=fixture_dir,
        symbols=symbols,
        dashboard_name=f"{hub_name}-interactive",
    )

    charts_index = run_dashboard_charts_from_fixtures(
        output_dir=root / "visual_page",
        fixture_dir=fixture_dir,
        symbols=symbols,
        dashboard_name=f"{hub_name}-charts",
    )

    return write_dashboard_hub(
        interactive_index_path=ui_index["index_path"],
        visual_index_path=charts_index["index_path"],
        output_dir=root / "hub",
        hub_name=hub_name,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qrds-dashboard-hub",
        description="Generate QRDS dashboard hub linking interactive and visual dashboard pages.",
    )
    parser.add_argument("--output-dir", default="artifacts/dashboard_hub", help="Output directory.")
    parser.add_argument("--fixture-dir", default="data/fixtures/okx_public", help="OKX public fixture directory.")
    parser.add_argument("--symbols", default="BTC-USDT,ETH-USDT,SOL-USDT", help="Comma-separated symbols.")
    parser.add_argument("--hub-name", default="qrds-dashboard-hub", help="Dashboard hub name.")
    parser.add_argument("--interactive-index-path", default=None, help="Optional existing interactive_dashboard_index.json.")
    parser.add_argument("--visual-index-path", default=None, help="Optional existing visual_dashboard_index.json.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.interactive_index_path and args.visual_index_path:
        index = write_dashboard_hub(
            interactive_index_path=args.interactive_index_path,
            visual_index_path=args.visual_index_path,
            output_dir=Path(args.output_dir) / "hub",
            hub_name=args.hub_name,
        )
    else:
        index = run_dashboard_hub_from_fixtures(
            output_dir=args.output_dir,
            fixture_dir=args.fixture_dir,
            symbols=parse_symbols(args.symbols),
            hub_name=args.hub_name,
        )

    print(json.dumps(index, indent=2, sort_keys=True))
    print()
    print("=== DASHBOARD HUB READY ===")
    print(index["html_path"])
    print()
    print("=== OPEN FILE ===")
    print(index["html_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
