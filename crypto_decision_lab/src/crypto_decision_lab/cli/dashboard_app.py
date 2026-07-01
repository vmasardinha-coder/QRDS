"""Local Dashboard App Launcher for QRDS.

Offline/research-only.
No API key.
No account connection.
No authenticated exchange access.
No orders.
No real capital.
No operational decisions.

This CLI refreshes the dashboard and produces app-style launch instructions.
Optional --serve starts a local static server, but the default testable mode is
non-blocking and only writes/prints instructions.
"""

from __future__ import annotations

import argparse
import http.server
import json
import socketserver
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from crypto_decision_lab.cli.dashboard_refresh import (
    DASHBOARD_LAUNCH_INFO_SCHEMA_VERSION,
    parse_symbols,
    run_dashboard_refresh,
    validate_dashboard_launch_info,
)
from crypto_decision_lab.contracts.research import build_research_safety_stamp, collect_research_contract_issues

DASHBOARD_APP_LAUNCH_SCHEMA_VERSION = "qrds.dashboard_app_launch.v1"


class DashboardAppLauncherError(ValueError):
    """Raised when dashboard app launcher cannot complete safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return str(path)


def _write_text(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return str(path)


def build_dashboard_app_launch(
    *,
    refresh_info: dict[str, Any],
    port: int = 8000,
    host: str = "0.0.0.0",
) -> dict[str, Any]:
    """Build app-style dashboard launch metadata."""
    refresh_issues = validate_dashboard_launch_info(refresh_info)
    if any(issue["severity"] == "error" for issue in refresh_issues):
        raise DashboardAppLauncherError(f"Invalid refresh info: {refresh_issues}")

    html_path = Path(refresh_info["html_path"]).resolve()
    serve_dir = html_path.parent
    serve_command = f"cd {serve_dir} && python -m http.server {port}"

    return {
        "schema": DASHBOARD_APP_LAUNCH_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "dashboard_launch_info_schema": DASHBOARD_LAUNCH_INFO_SCHEMA_VERSION,
        "dashboard_name": refresh_info["dashboard_name"],
        "html_path": str(html_path),
        "serve_dir": str(serve_dir),
        "serve_host": host,
        "serve_port": port,
        "serve_command": serve_command,
        "codespaces_port_hint": f"Ports → {port} → Open in Browser / Open Preview",
        "direct_preview_hint": "Right-click index.html and choose Open Preview.",
        "open_file_hint": str(html_path),
        "asset_count": refresh_info.get("asset_count"),
        "symbols": refresh_info.get("symbols"),
        "user_visible_layer": True,
        "static_html_only": True,
        "server_required": False,
        "serve_mode_available": True,
        "allocation_generated": False,
        "portfolio_decision_generated": False,
        **build_research_safety_stamp(),
    }


def validate_dashboard_app_launch(launch: dict[str, Any]) -> list[dict[str, Any]]:
    """Return quality issues for dashboard app launch payload."""
    issues = collect_research_contract_issues(
        launch,
        name="dashboard_app_launch",
        require_schema=True,
        require_app_mode=True,
        require_research_allowed=True,
    )

    if launch.get("schema") != DASHBOARD_APP_LAUNCH_SCHEMA_VERSION:
        issues.append(
            {
                "code": "INVALID_DASHBOARD_APP_LAUNCH_SCHEMA",
                "severity": "error",
                "name": "dashboard_app_launch",
                "message": "Invalid dashboard app launch schema.",
            }
        )

    html_path = launch.get("html_path")
    if not html_path or not Path(str(html_path)).exists():
        issues.append(
            {
                "code": "DASHBOARD_APP_HTML_MISSING",
                "severity": "error",
                "name": "dashboard_app_launch",
                "message": "Dashboard app HTML path is missing.",
            }
        )

    if launch.get("user_visible_layer") is not True:
        issues.append(
            {
                "code": "DASHBOARD_APP_NOT_USER_VISIBLE",
                "severity": "error",
                "name": "dashboard_app_launch",
                "message": "Dashboard app must mark user_visible_layer=True.",
            }
        )

    for flag in ("allocation_generated", "portfolio_decision_generated"):
        if launch.get(flag) is True:
            issues.append(
                {
                    "code": "UNSAFE_DASHBOARD_APP_DECISION_FLAG",
                    "severity": "error",
                    "name": "dashboard_app_launch",
                    "message": f"{flag} must remain False.",
                }
            )

    return issues


def render_app_ready_markdown(launch: dict[str, Any]) -> str:
    """Render app-ready instructions."""
    return f"""# QRDS Dashboard App Ready

The static research dashboard is ready.

## Open directly

```text
{launch["html_path"]}
```

## Codespaces Preview

Right-click:

```text
index.html
```

Choose:

```text
Open Preview
```

## Start local static server

```bash
{launch["serve_command"]}
```

Then use:

```text
{launch["codespaces_port_hint"]}
```

## Safety

```text
allocation_generated = False
portfolio_decision_generated = False
operational_decision_allowed = False
orders_generated = False
real_capital_used = False
trading_signal_generated = False
executable_signal_generated = False
recommendation_generated = False
```
"""


def run_dashboard_app(
    *,
    output_dir: str | Path = "artifacts/dashboard",
    fixture_dir: str | Path = "data/fixtures/okx_public",
    symbols: tuple[str, ...] | None = ("BTC-USDT", "ETH-USDT", "SOL-USDT"),
    dashboard_name: str = "qrds-static-research-dashboard",
    port: int = 8000,
) -> dict[str, Any]:
    """Refresh dashboard and write app launch files."""
    if port <= 0 or port > 65_535:
        raise DashboardAppLauncherError("port must be between 1 and 65535.")

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    refresh_info = run_dashboard_refresh(
        output_dir=output_root,
        fixture_dir=fixture_dir,
        symbols=symbols,
        dashboard_name=dashboard_name,
    )
    launch = build_dashboard_app_launch(refresh_info=refresh_info, port=port)

    issues = validate_dashboard_app_launch(launch)
    if any(issue["severity"] == "error" for issue in issues):
        raise DashboardAppLauncherError(f"Dashboard app launch validation errors: {issues}")

    app_launch_path = output_root / "dashboard_app_launch.json"
    app_ready_path = output_root / "APP_READY.md"

    _write_json(app_launch_path, launch)
    _write_text(app_ready_path, render_app_ready_markdown(launch))

    launch["app_launch_path"] = str(app_launch_path.resolve())
    launch["app_ready_path"] = str(app_ready_path.resolve())
    _write_json(app_launch_path, launch)

    return launch


def serve_dashboard(launch: dict[str, Any]) -> None:
    """Serve dashboard HTML directory with a local static server."""
    issues = validate_dashboard_app_launch(launch)
    if any(issue["severity"] == "error" for issue in issues):
        raise DashboardAppLauncherError(f"Cannot serve invalid dashboard launch: {issues}")

    serve_dir = Path(launch["serve_dir"])
    port = int(launch["serve_port"])

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            print(format % args)

    with socketserver.TCPServer(("", port), QuietHandler) as httpd:
        print("=== QRDS DASHBOARD SERVER ===")
        print(f"Serving directory: {serve_dir}")
        print(f"Port: {port}")
        print(f"Codespaces: Ports -> {port} -> Open in Browser / Open Preview")
        print("Press Ctrl+C to stop.")
        old_cwd = Path.cwd()
        try:
            import os

            os.chdir(serve_dir)
            httpd.serve_forever()
        finally:
            os.chdir(old_cwd)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qrds-dashboard-app",
        description="Refresh QRDS dashboard and print app-style launch instructions.",
    )
    parser.add_argument("--output-dir", default="artifacts/dashboard", help="Output directory.")
    parser.add_argument("--fixture-dir", default="data/fixtures/okx_public", help="OKX public fixture directory.")
    parser.add_argument("--symbols", default="BTC-USDT,ETH-USDT,SOL-USDT", help="Comma-separated symbols.")
    parser.add_argument("--dashboard-name", default="qrds-static-research-dashboard", help="Dashboard name.")
    parser.add_argument("--port", type=int, default=8000, help="Optional local static server port.")
    parser.add_argument("--serve", action="store_true", help="Start blocking local static server after refresh.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    launch = run_dashboard_app(
        output_dir=args.output_dir,
        fixture_dir=args.fixture_dir,
        symbols=parse_symbols(args.symbols),
        dashboard_name=args.dashboard_name,
        port=args.port,
    )

    print(json.dumps(launch, indent=2, sort_keys=True))
    print()
    print("=== DASHBOARD APP READY ===")
    print(launch["html_path"])
    print()
    print("=== SERVE COMMAND ===")
    print(launch["serve_command"])
    print()
    print("=== CODESPACES PORT HINT ===")
    print(launch["codespaces_port_hint"])

    if args.serve:
        serve_dashboard(launch)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
