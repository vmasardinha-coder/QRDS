"""Dashboard Hub v1 for QRDS.

Offline/research-only.
No API key.
No account connection.
No authenticated exchange access.
No orders.
No real capital.
No operational decisions.

This module creates a local static dashboard hub that links the user-facing
dashboard pages and their machine-readable artifacts.
"""

from __future__ import annotations

import html
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.contracts.research import build_research_safety_stamp, collect_research_contract_issues
from crypto_decision_lab.reports.export import compute_file_sha256

DASHBOARD_HUB_SCHEMA_VERSION = "qrds.dashboard_hub.v1"
DASHBOARD_HUB_INDEX_SCHEMA_VERSION = "qrds.dashboard_hub_index.v1"


class DashboardHubError(ValueError):
    """Raised when dashboard hub generation cannot complete safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise DashboardHubError(f"JSON artifact not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise DashboardHubError(f"JSON artifact must contain an object: {file_path}")

    return payload


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


def _assert_research_payload(payload: dict[str, Any], *, name: str) -> None:
    issues = collect_research_contract_issues(
        payload,
        name=name,
        require_schema=False,
        require_app_mode=False,
        require_research_allowed=False,
    )
    errors = [issue for issue in issues if issue["severity"] == "error"]
    if errors:
        raise DashboardHubError(f"{name} violates research-only contract: {errors}")


def _relpath(target: str | Path, *, start: str | Path) -> str:
    try:
        return os.path.relpath(Path(target).resolve(), Path(start).resolve())
    except ValueError:
        return str(Path(target).resolve())


def build_dashboard_hub_payload(
    *,
    interactive_index: dict[str, Any],
    visual_index: dict[str, Any],
    output_dir: str | Path,
    hub_name: str = "qrds-dashboard-hub",
) -> dict[str, Any]:
    """Build dashboard hub payload."""
    _assert_research_payload(interactive_index, name="interactive_dashboard_index")
    _assert_research_payload(visual_index, name="visual_dashboard_index")

    if not Path(interactive_index["html_path"]).exists():
        raise DashboardHubError(f"Interactive dashboard HTML not found: {interactive_index['html_path']}")
    if not Path(visual_index["html_path"]).exists():
        raise DashboardHubError(f"Visual dashboard HTML not found: {visual_index['html_path']}")

    out = Path(output_dir).resolve()
    symbols = sorted(set(interactive_index.get("symbols", [])) | set(visual_index.get("symbols", [])))

    pages = [
        {
            "page_id": "interactive_dashboard",
            "title": "Interactive Dashboard",
            "description": "Busca, filtros e ordenação client-side.",
            "html_path": str(Path(interactive_index["html_path"]).resolve()),
            "html_relpath": _relpath(interactive_index["html_path"], start=out),
            "payload_path": str(Path(interactive_index["payload_path"]).resolve()),
            "payload_relpath": _relpath(interactive_index["payload_path"], start=out),
            "asset_count": interactive_index.get("asset_count"),
            "symbols": interactive_index.get("symbols"),
        },
        {
            "page_id": "visual_charts",
            "title": "Visual Charts",
            "description": "Barras de edge score, stress score e cenários.",
            "html_path": str(Path(visual_index["html_path"]).resolve()),
            "html_relpath": _relpath(visual_index["html_path"], start=out),
            "payload_path": str(Path(visual_index["payload_path"]).resolve()),
            "payload_relpath": _relpath(visual_index["payload_path"], start=out),
            "asset_count": visual_index.get("asset_count"),
            "symbols": visual_index.get("symbols"),
        },
    ]

    return {
        "schema": DASHBOARD_HUB_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "hub_name": hub_name,
        "asset_count": max(
            int(interactive_index.get("asset_count", 0) or 0),
            int(visual_index.get("asset_count", 0) or 0),
        ),
        "symbols": symbols,
        "page_count": len(pages),
        "pages": pages,
        "source_indexes": {
            "interactive_index_path": str(Path(interactive_index.get("index_path", "")).resolve())
            if interactive_index.get("index_path")
            else None,
            "visual_index_path": str(Path(visual_index.get("index_path", "")).resolve())
            if visual_index.get("index_path")
            else None,
        },
        "user_visible_layer": True,
        "static_html_only": True,
        "dashboard_hub_only": True,
        "allocation_generated": False,
        "portfolio_decision_generated": False,
        "hypothetical_only": True,
        **build_research_safety_stamp(),
    }


def validate_dashboard_hub_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return quality issues for dashboard hub payload."""
    issues = collect_research_contract_issues(
        payload,
        name="dashboard_hub_payload",
        require_schema=True,
        require_app_mode=True,
        require_research_allowed=True,
    )

    if payload.get("schema") != DASHBOARD_HUB_SCHEMA_VERSION:
        issues.append(
            {
                "code": "INVALID_DASHBOARD_HUB_SCHEMA",
                "severity": "error",
                "name": "dashboard_hub_payload",
                "message": "Invalid dashboard hub schema.",
            }
        )

    if int(payload.get("page_count", 0) or 0) < 2:
        issues.append(
            {
                "code": "DASHBOARD_HUB_TOO_FEW_PAGES",
                "severity": "error",
                "name": "dashboard_hub_payload",
                "message": "Dashboard hub must include at least two pages.",
            }
        )

    if payload.get("user_visible_layer") is not True:
        issues.append(
            {
                "code": "DASHBOARD_HUB_NOT_USER_VISIBLE",
                "severity": "error",
                "name": "dashboard_hub_payload",
                "message": "Dashboard hub must mark user_visible_layer=True.",
            }
        )

    for flag in ("allocation_generated", "portfolio_decision_generated"):
        if payload.get(flag) is True:
            issues.append(
                {
                    "code": "UNSAFE_DASHBOARD_HUB_DECISION_FLAG",
                    "severity": "error",
                    "name": "dashboard_hub_payload",
                    "message": f"{flag} must remain False.",
                }
            )

    return issues


def render_dashboard_hub_html(payload: dict[str, Any]) -> str:
    """Render dashboard hub HTML."""
    issues = validate_dashboard_hub_payload(payload)
    if any(issue["severity"] == "error" for issue in issues):
        raise DashboardHubError(f"Dashboard hub validation errors: {issues}")

    title = html.escape(str(payload.get("hub_name")))
    page_cards = "\n".join(
        f"""
        <a class="card" href="{html.escape(str(page.get("html_relpath")))}">
          <div class="card-label">{html.escape(str(page.get("page_id")))}</div>
          <h2>{html.escape(str(page.get("title")))}</h2>
          <p>{html.escape(str(page.get("description")))}</p>
          <div class="meta">Ativos: {html.escape(str(page.get("asset_count")))} · Arquivo: <code>{html.escape(str(page.get("html_relpath")))}</code></div>
        </a>
        """
        for page in payload.get("pages", [])
    )

    artifact_rows = "\n".join(
        f"""
        <tr>
          <td>{html.escape(str(page.get("title")))}</td>
          <td><code>{html.escape(str(page.get("html_relpath")))}</code></td>
          <td><code>{html.escape(str(page.get("payload_relpath")))}</code></td>
        </tr>
        """
        for page in payload.get("pages", [])
    )

    symbols = ", ".join(str(symbol) for symbol in payload.get("symbols", []))
    safety_text = """allocation_generated = False
portfolio_decision_generated = False
operational_decision_allowed = False
orders_generated = False
real_capital_used = False
trading_signal_generated = False
executable_signal_generated = False
recommendation_generated = False"""

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #070b14;
      --panel: #111827;
      --panel2: #172033;
      --text: #eef4ff;
      --muted: #aab6c8;
      --border: #2b3954;
      --blue: #58a6ff;
      --purple: #d2a8ff;
      --yellow: #f2cc60;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: radial-gradient(circle at 20% 0%, rgba(88,166,255,.24), transparent 32%),
                  radial-gradient(circle at 78% 10%, rgba(210,168,255,.20), transparent 25%),
                  linear-gradient(180deg, var(--bg) 0%, #0d1117 100%);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }}
    header {{
      padding: 36px 30px;
      border-bottom: 1px solid var(--border);
      background: rgba(17,24,39,.86);
      backdrop-filter: blur(10px);
    }}
    h1 {{ margin: 0 0 8px; font-size: 34px; }}
    h2 {{ margin: 0 0 10px; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 28px; }}
    .muted {{ color: var(--muted); }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 18px;
      margin: 20px 0 26px;
    }}
    .card {{
      display: block;
      text-decoration: none;
      color: var(--text);
      background: rgba(17,24,39,.92);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 22px;
      box-shadow: 0 16px 50px rgba(0,0,0,.30);
      transition: transform .12s ease, border-color .12s ease;
    }}
    .card:hover {{
      transform: translateY(-2px);
      border-color: var(--blue);
    }}
    .card-label {{
      color: var(--purple);
      font-weight: 700;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .08em;
      margin-bottom: 10px;
    }}
    .meta {{ color: var(--muted); font-size: 13px; margin-top: 14px; }}
    .section {{
      background: rgba(17,24,39,.92);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 20px;
      margin-top: 18px;
      box-shadow: 0 16px 50px rgba(0,0,0,.25);
    }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid var(--border); padding: 10px; text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); }}
    pre, code {{ background: var(--panel2); border: 1px solid var(--border); border-radius: 10px; }}
    code {{ padding: 2px 5px; }}
    pre {{ padding: 14px; overflow-x: auto; }}
    .warning {{
      border-left: 4px solid var(--yellow);
      padding: 12px 14px;
      background: rgba(242,204,96,.10);
      border-radius: 12px;
      margin: 18px 0;
    }}
  </style>
</head>
<body>
  <header>
    <h1>QRDS Dashboard Hub</h1>
    <div class="muted">Hub local offline · {html.escape(str(payload.get("asset_count")))} ativos · {html.escape(symbols)} · {html.escape(str(payload.get("generated_at")))}</div>
  </header>
  <main>
    <div class="warning">Hub de pesquisa. Não é recomendação, alocação, sinal, ordem ou decisão operacional.</div>

    <section class="cards">
      {page_cards}
    </section>

    <section class="section">
      <h2>Arquivos gerados</h2>
      <table>
        <thead>
          <tr><th>Página</th><th>HTML</th><th>Payload</th></tr>
        </thead>
        <tbody>
          {artifact_rows}
        </tbody>
      </table>
    </section>

    <section class="section">
      <h2>Como abrir</h2>
      <p>Abra este arquivo <code>index.html</code> pelo preview do Codespaces ou use os cards acima.</p>
      <p>Se usar servidor local, abra a porta indicada no painel <code>Ports</code>.</p>
    </section>

    <section class="section">
      <h2>Travas de segurança</h2>
      <pre>{html.escape(safety_text)}</pre>
    </section>
  </main>
</body>
</html>
"""


def write_dashboard_hub(
    *,
    interactive_index_path: str | Path,
    visual_index_path: str | Path,
    output_dir: str | Path,
    hub_name: str = "qrds-dashboard-hub",
) -> dict[str, Any]:
    """Write dashboard hub artifacts."""
    interactive_index = _read_json(interactive_index_path)
    visual_index = _read_json(visual_index_path)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    payload = build_dashboard_hub_payload(
        interactive_index=interactive_index,
        visual_index=visual_index,
        output_dir=root,
        hub_name=hub_name,
    )

    issues = validate_dashboard_hub_payload(payload)
    if any(issue["severity"] == "error" for issue in issues):
        raise DashboardHubError(f"Dashboard hub validation errors: {issues}")

    html_path = root / "index.html"
    payload_path = root / "dashboard_hub_payload.json"
    index_path = root / "dashboard_hub_index.json"

    _write_text(html_path, render_dashboard_hub_html(payload))
    _write_json(payload_path, payload)

    index = {
        "schema": DASHBOARD_HUB_INDEX_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "hub_name": hub_name,
        "html_path": str(html_path),
        "payload_path": str(payload_path),
        "source_interactive_index_path": str(interactive_index_path),
        "source_visual_index_path": str(visual_index_path),
        "html_file_sha256": compute_file_sha256(html_path),
        "payload_file_sha256": compute_file_sha256(payload_path),
        "page_count": payload["page_count"],
        "asset_count": payload["asset_count"],
        "symbols": payload["symbols"],
        "user_visible_layer": True,
        "static_html_only": True,
        "dashboard_hub_only": True,
        "allocation_generated": False,
        "portfolio_decision_generated": False,
        **build_research_safety_stamp(),
    }
    _write_json(index_path, index)

    index["index_path"] = str(index_path)
    _write_json(index_path, index)

    return index


def load_dashboard_hub(index_path: str | Path) -> dict[str, Any]:
    """Load dashboard hub from index."""
    index = _read_json(index_path)
    if index.get("schema") != DASHBOARD_HUB_INDEX_SCHEMA_VERSION:
        raise DashboardHubError("Invalid dashboard hub index schema.")

    payload = _read_json(index["payload_path"])
    html_text = Path(index["html_path"]).read_text(encoding="utf-8")

    issues = validate_dashboard_hub_payload(payload)
    if any(issue["severity"] == "error" for issue in issues):
        raise DashboardHubError(f"Loaded dashboard hub validation errors: {issues}")

    return {
        "index": index,
        "payload": payload,
        "html": html_text,
        **build_research_safety_stamp(),
    }
