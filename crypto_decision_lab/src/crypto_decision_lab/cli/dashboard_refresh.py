"""Dashboard refresh and locator UX for QRDS.

Offline/research-only.
No API key.
No account connection.
No authenticated exchange access.
No orders.
No real capital.
No operational decisions.

This CLI refreshes the static dashboard and writes a small launch/locator file
so the user can immediately find the HTML dashboard.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from crypto_decision_lab.cli.dashboard import run_dashboard_from_fixtures
from crypto_decision_lab.contracts.research import build_research_safety_stamp, collect_research_contract_issues
from crypto_decision_lab.reports.dashboard import load_static_dashboard

DASHBOARD_LAUNCH_INFO_SCHEMA_VERSION = "qrds.dashboard_launch_info.v1"


class DashboardRefreshError(ValueError):
    """Raised when dashboard refresh/locator generation cannot complete safely."""


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


def parse_symbols(value: str | None) -> tuple[str, ...] | None:
    """Parse comma-separated symbols."""
    if value is None or not value.strip():
        return None
    return tuple(symbol.strip().upper() for symbol in value.split(",") if symbol.strip())


def build_dashboard_launch_info(
    *,
    dashboard_index: dict[str, Any],
    output_dir: str | Path,
    dashboard_name: str,
) -> dict[str, Any]:
    """Build user-facing launch/locator metadata."""
    html_path = Path(dashboard_index["html_path"]).resolve()
    payload_path = Path(dashboard_index["payload_path"]).resolve()
    index_path = Path(dashboard_index["index_path"]).resolve()
    output_root = Path(output_dir).resolve()

    serve_dir = html_path.parent
    serve_command = f"cd {serve_dir} && python -m http.server 8000"

    return {
        "schema": DASHBOARD_LAUNCH_INFO_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "dashboard_name": dashboard_name,
        "output_dir": str(output_root),
        "html_path": str(html_path),
        "payload_path": str(payload_path),
        "dashboard_index_path": str(index_path),
        "open_preview_hint": "In Codespaces: right-click index.html and choose Open Preview.",
        "serve_command": serve_command,
        "serve_url_hint": "After running the serve command, open the forwarded port 8000.",
        "symbols": dashboard_index.get("symbols"),
        "asset_count": dashboard_index.get("asset_count"),
        "user_visible_layer": True,
        "static_html_only": True,
        "allocation_generated": False,
        "portfolio_decision_generated": False,
        **build_research_safety_stamp(),
    }


def validate_dashboard_launch_info(info: dict[str, Any]) -> list[dict[str, Any]]:
    """Return quality issues for dashboard launch info."""
    issues = collect_research_contract_issues(
        info,
        name="dashboard_launch_info",
        require_schema=True,
        require_app_mode=True,
        require_research_allowed=True,
    )

    if info.get("schema") != DASHBOARD_LAUNCH_INFO_SCHEMA_VERSION:
        issues.append(
            {
                "code": "INVALID_DASHBOARD_LAUNCH_INFO_SCHEMA",
                "severity": "error",
                "name": "dashboard_launch_info",
                "message": "Invalid dashboard launch info schema.",
            }
        )

    if not info.get("html_path") or not Path(info["html_path"]).exists():
        issues.append(
            {
                "code": "DASHBOARD_HTML_PATH_MISSING",
                "severity": "error",
                "name": "dashboard_launch_info",
                "message": "Dashboard HTML path is missing.",
            }
        )

    if not info.get("user_visible_layer"):
        issues.append(
            {
                "code": "DASHBOARD_LAUNCH_INFO_NOT_USER_VISIBLE",
                "severity": "error",
                "name": "dashboard_launch_info",
                "message": "Launch info must mark user_visible_layer=True.",
            }
        )

    for flag in ("allocation_generated", "portfolio_decision_generated"):
        if info.get(flag) is True:
            issues.append(
                {
                    "code": "UNSAFE_DASHBOARD_LAUNCH_DECISION_FLAG",
                    "severity": "error",
                    "name": "dashboard_launch_info",
                    "message": f"{flag} must remain False.",
                }
            )

    return issues


def render_open_dashboard_markdown(info: dict[str, Any]) -> str:
    """Render a simple user-facing locator file."""
    return f"""# Open QRDS Dashboard

Dashboard refreshed successfully.

## Main file

```text
{info["html_path"]}
```

## Codespaces preview

Right-click:

```text
index.html
```

Then choose:

```text
Open Preview
```

## Local static server

```bash
{info["serve_command"]}
```

Then open the forwarded port 8000.

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


def run_dashboard_refresh(
    *,
    output_dir: str | Path,
    fixture_dir: str | Path = "data/fixtures/okx_public",
    symbols: tuple[str, ...] | None = None,
    dashboard_name: str = "qrds-static-research-dashboard",
) -> dict[str, Any]:
    """Refresh dashboard and write locator files."""
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    dashboard_index = run_dashboard_from_fixtures(
        fixture_dir=fixture_dir,
        output_dir=output_root,
        symbols=symbols,
        dashboard_name=dashboard_name,
    )

    loaded_dashboard = load_static_dashboard(dashboard_index["index_path"])
    if loaded_dashboard["payload"].get("user_visible_layer") is not True:
        raise DashboardRefreshError("Refreshed dashboard is not marked user_visible_layer=True.")

    launch_info = build_dashboard_launch_info(
        dashboard_index=dashboard_index,
        output_dir=output_root,
        dashboard_name=dashboard_name,
    )

    issues = validate_dashboard_launch_info(launch_info)
    if any(issue["severity"] == "error" for issue in issues):
        raise DashboardRefreshError(f"Dashboard launch info validation errors: {issues}")

    launch_info_path = output_root / "dashboard_launch_info.json"
    open_markdown_path = output_root / "OPEN_DASHBOARD.md"

    _write_json(launch_info_path, launch_info)
    _write_text(open_markdown_path, render_open_dashboard_markdown(launch_info))

    launch_info["launch_info_path"] = str(launch_info_path.resolve())
    launch_info["open_markdown_path"] = str(open_markdown_path.resolve())
    _write_json(launch_info_path, launch_info)

    return launch_info


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qrds-dashboard-refresh",
        description="Refresh QRDS static dashboard and print exactly where to open it.",
    )
    parser.add_argument("--output-dir", default="artifacts/dashboard", help="Output directory.")
    parser.add_argument("--fixture-dir", default="data/fixtures/okx_public", help="OKX public fixture directory.")
    parser.add_argument("--symbols", default="BTC-USDT,ETH-USDT,SOL-USDT", help="Comma-separated symbols.")
    parser.add_argument("--dashboard-name", default="qrds-static-research-dashboard", help="Dashboard name.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    info = run_dashboard_refresh(
        output_dir=args.output_dir,
        fixture_dir=args.fixture_dir,
        symbols=parse_symbols(args.symbols),
        dashboard_name=args.dashboard_name,
    )

    print(json.dumps(info, indent=2, sort_keys=True))
    print()
    print("=== OPEN DASHBOARD ===")
    print(info["html_path"])
    print()
    print("=== OPTIONAL LOCAL SERVER ===")
    print(info["serve_command"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
