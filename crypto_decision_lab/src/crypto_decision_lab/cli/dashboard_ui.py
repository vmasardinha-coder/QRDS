"""CLI for QRDS Interactive Static Dashboard UX."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from crypto_decision_lab.cli.dashboard_app import run_dashboard_app
from crypto_decision_lab.cli.dashboard_refresh import parse_symbols
from crypto_decision_lab.reports.dashboard_ui import write_interactive_dashboard


def run_dashboard_ui_from_fixtures(
    *,
    output_dir: str | Path,
    fixture_dir: str | Path = "data/fixtures/okx_public",
    symbols: tuple[str, ...] | None = ("BTC-USDT", "ETH-USDT", "SOL-USDT"),
    dashboard_name: str = "qrds-interactive-static-dashboard",
) -> dict:
    """Refresh base dashboard and write interactive dashboard."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    base_launch = run_dashboard_app(
        output_dir=root / "base",
        fixture_dir=fixture_dir,
        symbols=symbols,
        dashboard_name=f"{dashboard_name}-base",
    )
    static_payload_path = Path(base_launch["html_path"]).with_name("dashboard_payload.json")

    return write_interactive_dashboard(
        static_payload_path=static_payload_path,
        output_dir=root / "interactive",
        dashboard_name=dashboard_name,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qrds-dashboard-ui",
        description="Generate QRDS interactive static dashboard with client-side filters.",
    )
    parser.add_argument("--output-dir", default="artifacts/dashboard_ui", help="Output directory.")
    parser.add_argument("--fixture-dir", default="data/fixtures/okx_public", help="OKX public fixture directory.")
    parser.add_argument("--symbols", default="BTC-USDT,ETH-USDT,SOL-USDT", help="Comma-separated symbols.")
    parser.add_argument("--dashboard-name", default="qrds-interactive-static-dashboard", help="Dashboard name.")
    parser.add_argument("--static-payload-path", default=None, help="Optional existing dashboard_payload.json.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.static_payload_path:
        index = write_interactive_dashboard(
            static_payload_path=args.static_payload_path,
            output_dir=Path(args.output_dir) / "interactive",
            dashboard_name=args.dashboard_name,
        )
    else:
        index = run_dashboard_ui_from_fixtures(
            output_dir=args.output_dir,
            fixture_dir=args.fixture_dir,
            symbols=parse_symbols(args.symbols),
            dashboard_name=args.dashboard_name,
        )

    print(json.dumps(index, indent=2, sort_keys=True))
    print()
    print("=== INTERACTIVE DASHBOARD READY ===")
    print(index["html_path"])
    print()
    print("=== OPEN FILE ===")
    print(index["html_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
