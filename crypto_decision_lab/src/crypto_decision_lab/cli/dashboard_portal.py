"""CLI for QRDS Unified Dashboard Portal v1."""
from __future__ import annotations
import sys



import argparse
import json
from pathlib import Path
from typing import Sequence

from crypto_decision_lab.cli.dashboard_charts import run_dashboard_charts_from_fixtures
from crypto_decision_lab.cli.dashboard_guide import write_dashboard_guide
from crypto_decision_lab.cli.dashboard_refresh import parse_symbols
from crypto_decision_lab.cli.dashboard_serve import serve_directory, write_dashboard_serve_plan
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
        output_dir=root,
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
    parser.add_argument("--serve", action="store_true", help="Start local static server after generating portal.")
    parser.add_argument("--plan-only", action="store_true", help="Generate portal and serve plan without starting server.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")

    parser = build_arg_parser()
    args = parser.parse_args(argv)

    index = run_dashboard_portal_from_fixtures(
        output_dir=args.output_dir,
        fixture_dir=args.fixture_dir,
        symbols=parse_symbols(args.symbols),
        portal_name=args.portal_name,
        preferred_port=args.preferred_port,
    )

    print(json.dumps(index, indent=2, sort_keys=True, ensure_ascii=True))
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

    if args.serve and not args.plan_only:
        serve_plan = {
            "schema": "qrds.dashboard_serve_plan.v1",
            "app_mode": "INTERACTIVE_RESEARCH_ONLY",
            "research_allowed": True,
            "operational_decision_allowed": False,
            "api_key_required": False,
            "api_key_present": False,
            "account_connection_required": False,
            "orders_generated": False,
            "real_orders_generated": False,
            "real_capital_used": False,
            "orders_allowed": False,
            "trading_signal_generated": False,
            "executable_signal_generated": False,
            "recommendation_generated": False,
            "html_path": index["html_path"],
            "serve_dir": str(Path(index["html_path"]).parent),
            "preferred_port": args.preferred_port,
            "selected_port": index["selected_port"],
            "port_changed_due_to_conflict": index["selected_port"] != args.preferred_port,
            "serve_host": "0.0.0.0",
            "check_host": "127.0.0.1",
            "serve_command": index["serve_command"],
            "codespaces_port_hint": index["codespaces_port_hint"],
            "stop_server_hint": "Press Ctrl+C in the terminal running the server.",
            "open_preview_hint": "Use the Codespaces Ports panel.",
            "user_visible_layer": True,
            "static_html_only": True,
            "server_required": False,
            "allocation_generated": False,
            "portfolio_decision_generated": False,
        }
        serve_directory(serve_plan)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
