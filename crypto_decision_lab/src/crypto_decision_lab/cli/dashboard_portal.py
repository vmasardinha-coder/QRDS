"""CLI for QRDS Unified Dashboard Portal v1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from crypto_decision_lab.cli.dashboard_charts import run_dashboard_charts_from_fixtures
from crypto_decision_lab.cli.dashboard_guide import write_dashboard_guide
from crypto_decision_lab.cli.dashboard_refresh import parse_symbols
from crypto_decision_lab.cli.dashboard_serve import write_dashboard_serve_plan
from crypto_decision_lab.cli.dashboard_ui import run_dashboard_ui_from_fixtures
from crypto_decision_lab.reports.dashboard_portal import write_dashboard_portal


def run_dashboard_portal_from_fixtures(
    *,
    output_dir: str | Path,
    fixture_dir: str | Path = "data/fixtures/okx_public",
    symbols: tuple[str, ...] | None = ("BTC-USDT", "ETH-USDT", "SOL-USDT"),
    portal_name: str = "qrds-unified-dashboard-portal",
    preferred_port: int = 8000,
) -> dict:
    """Generate guide, dashboard pages, portal and smart serve plan."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    guide_index = write_dashboard_guide(
        output_dir=root / "guide_page" / "guide",
        guide_name=f"{portal_name}-guide",
    )

    ui_index = run_dashboard_ui_from_fixtures(
        output_dir=root / "interactive_page",
        fixture_dir=fixture_dir,
        symbols=symbols,
        dashboard_name=f"{portal_name}-interactive",
    )

    charts_index = run_dashboard_charts_from_fixtures(
        output_dir=root / "visual_page",
        fixture_dir=fixture_dir,
        symbols=symbols,
        dashboard_name=f"{portal_name}-charts",
    )

    portal_index = write_dashboard_portal(
        guide_index_path=guide_index["index_path"],
        interactive_index_path=ui_index["index_path"],
        visual_index_path=charts_index["index_path"],
        output_dir=root / "portal",
        portal_name=portal_name,
    )

    serve_plan = write_dashboard_serve_plan(
        html_path=portal_index["html_path"],
        output_dir=root,
        preferred_port=preferred_port,
    )

    portal_index["serve_plan_path"] = serve_plan["serve_plan_path"]
    portal_index["selected_port"] = serve_plan["selected_port"]
    portal_index["serve_command"] = serve_plan["serve_command"]
    portal_index["codespaces_port_hint"] = serve_plan["codespaces_port_hint"]

    return portal_index


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qrds-dashboard-portal",
        description="Generate unified QRDS portal with guide, dashboards and smart serve plan.",
    )
    parser.add_argument("--output-dir", default="artifacts/dashboard_portal", help="Output directory.")
    parser.add_argument("--fixture-dir", default="data/fixtures/okx_public", help="OKX public fixture directory.")
    parser.add_argument("--symbols", default="BTC-USDT,ETH-USDT,SOL-USDT", help="Comma-separated symbols.")
    parser.add_argument("--portal-name", default="qrds-unified-dashboard-portal", help="Portal name.")
    parser.add_argument("--preferred-port", type=int, default=8000, help="Preferred server port.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    index = run_dashboard_portal_from_fixtures(
        output_dir=args.output_dir,
        fixture_dir=args.fixture_dir,
        symbols=parse_symbols(args.symbols),
        portal_name=args.portal_name,
        preferred_port=args.preferred_port,
    )

    print(json.dumps(index, indent=2, sort_keys=True, ensure_ascii=False))
    print()
    print("=== UNIFIED PORTAL READY ===")
    print(index["html_path"])
    print()
    print("=== SELECTED PORT ===")
    print(index["selected_port"])
    print()
    print("=== SERVE COMMAND ===")
    print(index["serve_command"])
    print()
    print("=== CODESPACES PORT HINT ===")
    print(index["codespaces_port_hint"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
