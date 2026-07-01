"""CLI for QRDS Visual Dashboard Charts v1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from crypto_decision_lab.cli.dashboard_refresh import parse_symbols
from crypto_decision_lab.cli.dashboard_ui import run_dashboard_ui_from_fixtures
from crypto_decision_lab.reports.dashboard_charts import write_visual_dashboard


def run_dashboard_charts_from_fixtures(
    *,
    output_dir: str | Path,
    fixture_dir: str | Path = "data/fixtures/okx_public",
    symbols: tuple[str, ...] | None = ("BTC-USDT", "ETH-USDT", "SOL-USDT"),
    dashboard_name: str = "qrds-visual-dashboard-charts",
) -> dict:
    """Generate interactive dashboard payload and render chart dashboard."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    ui_index = run_dashboard_ui_from_fixtures(
        output_dir=root / "source_ui",
        fixture_dir=fixture_dir,
        symbols=symbols,
        dashboard_name=f"{dashboard_name}-source-ui",
    )
    interactive_payload_path = ui_index["payload_path"]

    return write_visual_dashboard(
        interactive_payload_path=interactive_payload_path,
        output_dir=root / "charts",
        dashboard_name=dashboard_name,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qrds-dashboard-charts",
        description="Generate QRDS visual dashboard charts from research artifacts.",
    )
    parser.add_argument("--output-dir", default="artifacts/dashboard_charts", help="Output directory.")
    parser.add_argument("--fixture-dir", default="data/fixtures/okx_public", help="OKX public fixture directory.")
    parser.add_argument("--symbols", default="BTC-USDT,ETH-USDT,SOL-USDT", help="Comma-separated symbols.")
    parser.add_argument("--dashboard-name", default="qrds-visual-dashboard-charts", help="Dashboard name.")
    parser.add_argument("--interactive-payload-path", default=None, help="Optional existing interactive_dashboard_payload.json.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.interactive_payload_path:
        index = write_visual_dashboard(
            interactive_payload_path=args.interactive_payload_path,
            output_dir=Path(args.output_dir) / "charts",
            dashboard_name=args.dashboard_name,
        )
    else:
        index = run_dashboard_charts_from_fixtures(
            output_dir=args.output_dir,
            fixture_dir=args.fixture_dir,
            symbols=parse_symbols(args.symbols),
            dashboard_name=args.dashboard_name,
        )

    print(json.dumps(index, indent=2, sort_keys=True))
    print()
    print("=== VISUAL DASHBOARD READY ===")
    print(index["html_path"])
    print()
    print("=== OPEN FILE ===")
    print(index["html_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
