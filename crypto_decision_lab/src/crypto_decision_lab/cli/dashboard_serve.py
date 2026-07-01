"""Smart Dashboard Server Port UX for QRDS.

Offline/research-only.
No API key.
No account connection.
No authenticated exchange access.
No orders.
No real capital.
No operational decisions.

This CLI locates/generates the interactive dashboard and chooses an available
local port automatically, avoiding the common "port already in use" UX issue.
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
import socket
import socketserver
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from crypto_decision_lab.cli.dashboard_refresh import parse_symbols
from crypto_decision_lab.cli.dashboard_ui import run_dashboard_ui_from_fixtures
from crypto_decision_lab.contracts.research import build_research_safety_stamp, collect_research_contract_issues

DASHBOARD_SERVE_PLAN_SCHEMA_VERSION = "qrds.dashboard_serve_plan.v1"


class DashboardServeError(ValueError):
    """Raised when dashboard serve planning cannot complete safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return str(path)


def is_port_available(port: int, *, host: str = "127.0.0.1") -> bool:
    """Return True if a TCP port appears available."""
    if port <= 0 or port > 65_535:
        return False

    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((host, port)) != 0


def find_available_port(
    *,
    preferred_port: int = 8000,
    max_tries: int = 50,
    host: str = "127.0.0.1",
) -> int:
    """Find the first available port starting at preferred_port."""
    if preferred_port <= 0 or preferred_port > 65_535:
        raise DashboardServeError("preferred_port must be between 1 and 65535.")
    if max_tries <= 0:
        raise DashboardServeError("max_tries must be positive.")

    for port in range(preferred_port, min(65_535, preferred_port + max_tries - 1) + 1):
        if is_port_available(port, host=host):
            return port

    raise DashboardServeError(f"No available port found from {preferred_port} within {max_tries} tries.")


def build_dashboard_serve_plan(
    *,
    html_path: str | Path,
    preferred_port: int = 8000,
    host: str = "0.0.0.0",
    check_host: str = "127.0.0.1",
    max_tries: int = 50,
) -> dict[str, Any]:
    """Build a serve plan with an available port."""
    html = Path(html_path).resolve()
    if not html.exists() or not html.is_file():
        raise DashboardServeError(f"Dashboard HTML not found: {html}")

    port = find_available_port(preferred_port=preferred_port, max_tries=max_tries, host=check_host)
    serve_dir = html.parent
    serve_command = f"cd {serve_dir} && python -m http.server {port}"

    return {
        "schema": DASHBOARD_SERVE_PLAN_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "html_path": str(html),
        "serve_dir": str(serve_dir),
        "preferred_port": preferred_port,
        "selected_port": port,
        "port_changed_due_to_conflict": port != preferred_port,
        "serve_host": host,
        "check_host": check_host,
        "serve_command": serve_command,
        "codespaces_port_hint": f"Ports → {port} → Open in Browser / Open Preview",
        "stop_server_hint": "Press Ctrl+C in the terminal running the server.",
        "open_preview_hint": "Right-click index.html and choose Open Preview.",
        "user_visible_layer": True,
        "static_html_only": True,
        "server_required": False,
        "allocation_generated": False,
        "portfolio_decision_generated": False,
        **build_research_safety_stamp(),
    }


def validate_dashboard_serve_plan(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Return quality issues for a dashboard serve plan."""
    issues = collect_research_contract_issues(
        plan,
        name="dashboard_serve_plan",
        require_schema=True,
        require_app_mode=True,
        require_research_allowed=True,
    )

    if plan.get("schema") != DASHBOARD_SERVE_PLAN_SCHEMA_VERSION:
        issues.append(
            {
                "code": "INVALID_DASHBOARD_SERVE_PLAN_SCHEMA",
                "severity": "error",
                "name": "dashboard_serve_plan",
                "message": "Invalid dashboard serve plan schema.",
            }
        )

    html_path = plan.get("html_path")
    if not html_path or not Path(str(html_path)).exists():
        issues.append(
            {
                "code": "DASHBOARD_SERVE_HTML_MISSING",
                "severity": "error",
                "name": "dashboard_serve_plan",
                "message": "Dashboard HTML file is missing.",
            }
        )

    selected_port = int(plan.get("selected_port", 0) or 0)
    if selected_port <= 0 or selected_port > 65_535:
        issues.append(
            {
                "code": "DASHBOARD_SERVE_INVALID_PORT",
                "severity": "error",
                "name": "dashboard_serve_plan",
                "message": "Selected port must be valid.",
            }
        )

    for flag in ("allocation_generated", "portfolio_decision_generated"):
        if plan.get(flag) is True:
            issues.append(
                {
                    "code": "UNSAFE_DASHBOARD_SERVE_DECISION_FLAG",
                    "severity": "error",
                    "name": "dashboard_serve_plan",
                    "message": f"{flag} must remain False.",
                }
            )

    return issues


def write_dashboard_serve_plan(
    *,
    html_path: str | Path,
    output_dir: str | Path,
    preferred_port: int = 8000,
) -> dict[str, Any]:
    """Write dashboard serve plan JSON."""
    plan = build_dashboard_serve_plan(
        html_path=html_path,
        preferred_port=preferred_port,
    )
    issues = validate_dashboard_serve_plan(plan)
    if any(issue["severity"] == "error" for issue in issues):
        raise DashboardServeError(f"Dashboard serve plan validation errors: {issues}")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    plan_path = out / "dashboard_serve_plan.json"
    _write_json(plan_path, plan)
    plan["serve_plan_path"] = str(plan_path.resolve())
    _write_json(plan_path, plan)
    return plan


def generate_dashboard_and_plan(
    *,
    output_dir: str | Path = "artifacts/dashboard_ui",
    fixture_dir: str | Path = "data/fixtures/okx_public",
    symbols: tuple[str, ...] | None = ("BTC-USDT", "ETH-USDT", "SOL-USDT"),
    preferred_port: int = 8000,
    dashboard_name: str = "qrds-interactive-static-dashboard",
) -> dict[str, Any]:
    """Generate interactive dashboard and serve plan."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    index = run_dashboard_ui_from_fixtures(
        output_dir=out,
        fixture_dir=fixture_dir,
        symbols=symbols,
        dashboard_name=dashboard_name,
    )
    html_path = index["html_path"]

    return write_dashboard_serve_plan(
        html_path=html_path,
        output_dir=out,
        preferred_port=preferred_port,
    )


def serve_directory(plan: dict[str, Any]) -> None:
    """Serve the dashboard directory using the selected available port."""
    issues = validate_dashboard_serve_plan(plan)
    if any(issue["severity"] == "error" for issue in issues):
        raise DashboardServeError(f"Cannot serve invalid plan: {issues}")

    serve_dir = Path(plan["serve_dir"])
    port = int(plan["selected_port"])

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            print(format % args)

    old_cwd = Path.cwd()
    os.chdir(serve_dir)
    try:
        with socketserver.TCPServer(("", port), QuietHandler) as httpd:
            print("=== QRDS SMART DASHBOARD SERVER ===")
            print(f"Serving directory: {serve_dir}")
            print(f"Selected port: {port}")
            if plan.get("port_changed_due_to_conflict"):
                print(f"Preferred port {plan.get('preferred_port')} was busy; using {port}.")
            print(plan["codespaces_port_hint"])
            print("Press Ctrl+C to stop.")
            httpd.serve_forever()
    finally:
        os.chdir(old_cwd)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qrds-dashboard-serve",
        description="Generate QRDS dashboard and choose an available local port.",
    )
    parser.add_argument("--output-dir", default="artifacts/dashboard_ui", help="Output directory.")
    parser.add_argument("--fixture-dir", default="data/fixtures/okx_public", help="OKX public fixture directory.")
    parser.add_argument("--symbols", default="BTC-USDT,ETH-USDT,SOL-USDT", help="Comma-separated symbols.")
    parser.add_argument("--preferred-port", type=int, default=8000, help="Preferred local static server port.")
    parser.add_argument("--dashboard-name", default="qrds-interactive-static-dashboard", help="Dashboard name.")
    parser.add_argument("--serve", action="store_true", help="Start blocking local static server after generating plan.")
    parser.add_argument("--plan-only", action="store_true", help="Only generate and print plan; do not serve.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    plan = generate_dashboard_and_plan(
        output_dir=args.output_dir,
        fixture_dir=args.fixture_dir,
        symbols=parse_symbols(args.symbols),
        preferred_port=args.preferred_port,
        dashboard_name=args.dashboard_name,
    )

    print(json.dumps(plan, indent=2, sort_keys=True))
    print()
    print("=== SMART DASHBOARD READY ===")
    print(plan["html_path"])
    print()
    print("=== SELECTED PORT ===")
    print(plan["selected_port"])
    if plan.get("port_changed_due_to_conflict"):
        print(f"Preferred port {plan['preferred_port']} was busy; using {plan['selected_port']}.")
    print()
    print("=== SERVE COMMAND ===")
    print(plan["serve_command"])
    print()
    print("=== CODESPACES PORT HINT ===")
    print(plan["codespaces_port_hint"])

    if args.serve and not args.plan_only:
        serve_directory(plan)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
