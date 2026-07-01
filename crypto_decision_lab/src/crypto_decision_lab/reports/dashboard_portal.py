"""Unified Dashboard Portal v1 for QRDS.

Offline/research-only.
No API key.
No account connection.
No authenticated exchange access.
No orders.
No real capital.
No operational decisions.

This module creates a single local portal home that links:
- interpretation guide
- interactive dashboard
- visual charts
- JSON artifacts
- server/open instructions
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

DASHBOARD_PORTAL_SCHEMA_VERSION = "qrds.unified_dashboard_portal.v1"
DASHBOARD_PORTAL_INDEX_SCHEMA_VERSION = "qrds.unified_dashboard_portal_index.v1"


class DashboardPortalError(ValueError):
    """Raised when dashboard portal generation cannot complete safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise DashboardPortalError(f"JSON artifact not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise DashboardPortalError(f"JSON artifact must contain an object: {file_path}")

    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
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
        raise DashboardPortalError(f"{name} violates research-only contract: {errors}")


def _relpath(target: str | Path, *, start: str | Path) -> str:
    try:
        return os.path.relpath(Path(target).resolve(), Path(start).resolve())
    except ValueError:
        return str(Path(target).resolve())


def build_dashboard_portal_payload(
    *,
    guide_index: dict[str, Any],
    interactive_index: dict[str, Any],
    visual_index: dict[str, Any],
    output_dir: str | Path,
    portal_name: str = "qrds-unified-dashboard-portal",
) -> dict[str, Any]:
    """Build unified portal payload."""
    _assert_research_payload(guide_index, name="guide_index")
    _assert_research_payload(interactive_index, name="interactive_index")
    _assert_research_payload(visual_index, name="visual_index")

    for label, index in {
        "guide": guide_index,
        "interactive": interactive_index,
        "visual": visual_index,
    }.items():
        if not Path(index["html_path"]).exists():
            raise DashboardPortalError(f"{label} HTML not found: {index['html_path']}")
        if not Path(index["payload_path"]).exists():
            raise DashboardPortalError(f"{label} payload not found: {index['payload_path']}")

    out = Path(output_dir).resolve()
    symbols = sorted(set(interactive_index.get("symbols", [])) | set(visual_index.get("symbols", [])))

    pages = [
        {
            "page_id": "read_first",
            "title": "1. Guia de interpretação",
            "description": "Comece aqui: explica status, score, stress, filtros e limites.",
            "html_path": str(Path(guide_index["html_path"]).resolve()),
            "html_relpath": _relpath(guide_index["html_path"], start=out),
            "payload_path": str(Path(guide_index["payload_path"]).resolve()),
            "payload_relpath": _relpath(guide_index["payload_path"], start=out),
            "priority": 1,
            "recommended_first": True,
        },
        {
            "page_id": "interactive_dashboard",
            "title": "2. Dashboard interativo",
            "description": "Busca, filtros e ordenação client-side para navegar os ativos.",
            "html_path": str(Path(interactive_index["html_path"]).resolve()),
            "html_relpath": _relpath(interactive_index["html_path"], start=out),
            "payload_path": str(Path(interactive_index["payload_path"]).resolve()),
            "payload_relpath": _relpath(interactive_index["payload_path"], start=out),
            "priority": 2,
            "recommended_first": False,
            "asset_count": interactive_index.get("asset_count"),
        },
        {
            "page_id": "visual_charts",
            "title": "3. Gráficos visuais",
            "description": "Barras de edge score, pior stress e cenários.",
            "html_path": str(Path(visual_index["html_path"]).resolve()),
            "html_relpath": _relpath(visual_index["html_path"], start=out),
            "payload_path": str(Path(visual_index["payload_path"]).resolve()),
            "payload_relpath": _relpath(visual_index["payload_path"], start=out),
            "priority": 3,
            "recommended_first": False,
            "asset_count": visual_index.get("asset_count"),
        },
    ]

    return {
        "schema": DASHBOARD_PORTAL_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "portal_name": portal_name,
        "page_count": len(pages),
        "asset_count": max(
            int(interactive_index.get("asset_count", 0) or 0),
            int(visual_index.get("asset_count", 0) or 0),
        ),
        "symbols": symbols,
        "pages": pages,
        "recommended_reading_order": [page["page_id"] for page in sorted(pages, key=lambda item: item["priority"])],
        "interpretation_first": True,
        "source_indexes": {
            "guide_index_path": str(Path(guide_index.get("index_path", "")).resolve()) if guide_index.get("index_path") else None,
            "interactive_index_path": str(Path(interactive_index.get("index_path", "")).resolve()) if interactive_index.get("index_path") else None,
            "visual_index_path": str(Path(visual_index.get("index_path", "")).resolve()) if visual_index.get("index_path") else None,
        },
        "user_visible_layer": True,
        "static_html_only": True,
        "unified_portal_only": True,
        "allocation_generated": False,
        "portfolio_decision_generated": False,
        "hypothetical_only": True,
        **build_research_safety_stamp(),
    }


def validate_dashboard_portal_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return quality issues for portal payload."""
    issues = collect_research_contract_issues(
        payload,
        name="dashboard_portal_payload",
        require_schema=True,
        require_app_mode=True,
        require_research_allowed=True,
    )

    if payload.get("schema") != DASHBOARD_PORTAL_SCHEMA_VERSION:
        issues.append(
            {
                "code": "INVALID_DASHBOARD_PORTAL_SCHEMA",
                "severity": "error",
                "name": "dashboard_portal_payload",
                "message": "Invalid dashboard portal schema.",
            }
        )

    if int(payload.get("page_count", 0) or 0) < 3:
        issues.append(
            {
                "code": "DASHBOARD_PORTAL_TOO_FEW_PAGES",
                "severity": "error",
                "name": "dashboard_portal_payload",
                "message": "Dashboard portal must include guide, interactive dashboard and visual charts.",
            }
        )

    if payload.get("interpretation_first") is not True:
        issues.append(
            {
                "code": "DASHBOARD_PORTAL_INTERPRETATION_NOT_FIRST",
                "severity": "error",
                "name": "dashboard_portal_payload",
                "message": "Portal must guide user to interpretation first.",
            }
        )

    if payload.get("user_visible_layer") is not True:
        issues.append(
            {
                "code": "DASHBOARD_PORTAL_NOT_USER_VISIBLE",
                "severity": "error",
                "name": "dashboard_portal_payload",
                "message": "Portal must mark user_visible_layer=True.",
            }
        )

    for flag in ("allocation_generated", "portfolio_decision_generated"):
        if payload.get(flag) is True:
            issues.append(
                {
                    "code": "UNSAFE_DASHBOARD_PORTAL_DECISION_FLAG",
                    "severity": "error",
                    "name": "dashboard_portal_payload",
                    "message": f"{flag} must remain False.",
                }
            )

    return issues


def render_dashboard_portal_html(payload: dict[str, Any]) -> str:
    """Render unified portal HTML."""
    issues = validate_dashboard_portal_payload(payload)
    if any(issue["severity"] == "error" for issue in issues):
        raise DashboardPortalError(f"Dashboard portal validation errors: {issues}")

    title = html.escape(str(payload.get("portal_name")))
    symbols = ", ".join(str(symbol) for symbol in payload.get("symbols", [])) or "—"

    cards = "\n".join(
        f"""
        <a class="card {'primary' if page.get('recommended_first') else ''}" href="{html.escape(str(page.get("html_relpath")))}">
          <div class="step">{html.escape(str(page.get("priority")))}</div>
          <div>
            <div class="label">{html.escape(str(page.get("page_id")))}</div>
            <h2>{html.escape(str(page.get("title")))}</h2>
            <p>{html.escape(str(page.get("description")))}</p>
            <div class="meta"><code>{html.escape(str(page.get("html_relpath")))}</code></div>
          </div>
        </a>
        """
        for page in sorted(payload.get("pages", []), key=lambda item: item.get("priority", 99))
    )

    artifact_rows = "\n".join(
        f"""
        <tr>
          <td>{html.escape(str(page.get("title")))}</td>
          <td><code>{html.escape(str(page.get("html_relpath")))}</code></td>
          <td><code>{html.escape(str(page.get("payload_relpath")))}</code></td>
        </tr>
        """
        for page in sorted(payload.get("pages", []), key=lambda item: item.get("priority", 99))
    )

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
      --bg: #060a13;
      --panel: #111827;
      --panel2: #172033;
      --text: #eef4ff;
      --muted: #aab6c8;
      --border: #2b3954;
      --blue: #58a6ff;
      --purple: #d2a8ff;
      --yellow: #f2cc60;
      --green: #7ee787;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: radial-gradient(circle at 18% 0%, rgba(88,166,255,.24), transparent 30%),
                  radial-gradient(circle at 82% 8%, rgba(210,168,255,.20), transparent 24%),
                  linear-gradient(180deg, var(--bg) 0%, #0d1117 100%);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.55;
    }}
    header {{
      padding: 38px 30px;
      border-bottom: 1px solid var(--border);
      background: rgba(17,24,39,.88);
      backdrop-filter: blur(10px);
    }}
    h1 {{ margin: 0 0 8px; font-size: 36px; }}
    h2 {{ margin: 0 0 8px; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 28px; }}
    .muted {{ color: var(--muted); }}
    .warning {{
      border-left: 4px solid var(--yellow);
      padding: 12px 14px;
      background: rgba(242,204,96,.10);
      border-radius: 12px;
      margin-bottom: 18px;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(310px, 1fr));
      gap: 18px;
      margin-bottom: 22px;
    }}
    .card {{
      display: grid;
      grid-template-columns: 48px 1fr;
      gap: 16px;
      text-decoration: none;
      color: var(--text);
      background: rgba(17,24,39,.92);
      border: 1px solid var(--border);
      border-radius: 22px;
      padding: 22px;
      box-shadow: 0 16px 50px rgba(0,0,0,.28);
      transition: transform .12s ease, border-color .12s ease;
    }}
    .card:hover {{
      transform: translateY(-2px);
      border-color: var(--blue);
    }}
    .card.primary {{
      border-color: rgba(126,231,135,.55);
      background: linear-gradient(180deg, rgba(126,231,135,.10), rgba(17,24,39,.92));
    }}
    .step {{
      width: 42px;
      height: 42px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      background: var(--panel2);
      border: 1px solid var(--border);
      color: var(--green);
      font-weight: 900;
      font-size: 18px;
    }}
    .label {{
      color: var(--purple);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .08em;
      font-weight: 800;
      margin-bottom: 8px;
    }}
    .meta {{ color: var(--muted); font-size: 13px; margin-top: 12px; }}
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
  </style>
</head>
<body>
  <header>
    <h1>QRDS Unified Portal</h1>
    <div class="muted">Leia primeiro o guia · {html.escape(str(payload.get("asset_count")))} ativos · {html.escape(symbols)} · {html.escape(str(payload.get("generated_at")))}</div>
  </header>
  <main>
    <div class="warning">
      Ordem recomendada: guia → dashboard interativo → gráficos. Portal de pesquisa, não decisão operacional.
    </div>

    <section class="cards">
      {cards}
    </section>

    <section class="section">
      <h2>Arquivos e payloads</h2>
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
      <h2>Travas de segurança</h2>
      <pre>{html.escape(safety_text)}</pre>
    </section>
  </main>
</body>
</html>
"""


def write_dashboard_portal(
    *,
    guide_index_path: str | Path,
    interactive_index_path: str | Path,
    visual_index_path: str | Path,
    output_dir: str | Path,
    portal_name: str = "qrds-unified-dashboard-portal",
) -> dict[str, Any]:
    """Write unified portal artifacts."""
    guide_index = _read_json(guide_index_path)
    interactive_index = _read_json(interactive_index_path)
    visual_index = _read_json(visual_index_path)

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    payload = build_dashboard_portal_payload(
        guide_index=guide_index,
        interactive_index=interactive_index,
        visual_index=visual_index,
        output_dir=root,
        portal_name=portal_name,
    )

    issues = validate_dashboard_portal_payload(payload)
    if any(issue["severity"] == "error" for issue in issues):
        raise DashboardPortalError(f"Dashboard portal validation errors: {issues}")

    html_path = root / "index.html"
    payload_path = root / "dashboard_portal_payload.json"
    index_path = root / "dashboard_portal_index.json"

    _write_text(html_path, render_dashboard_portal_html(payload))
    _write_json(payload_path, payload)

    index = {
        "schema": DASHBOARD_PORTAL_INDEX_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "portal_name": portal_name,
        "html_path": str(html_path),
        "payload_path": str(payload_path),
        "source_guide_index_path": str(guide_index_path),
        "source_interactive_index_path": str(interactive_index_path),
        "source_visual_index_path": str(visual_index_path),
        "html_file_sha256": compute_file_sha256(html_path),
        "payload_file_sha256": compute_file_sha256(payload_path),
        "page_count": payload["page_count"],
        "asset_count": payload["asset_count"],
        "symbols": payload["symbols"],
        "interpretation_first": True,
        "user_visible_layer": True,
        "static_html_only": True,
        "unified_portal_only": True,
        "allocation_generated": False,
        "portfolio_decision_generated": False,
        **build_research_safety_stamp(),
    }
    _write_json(index_path, index)

    index["index_path"] = str(index_path)
    _write_json(index_path, index)

    return index


def load_dashboard_portal(index_path: str | Path) -> dict[str, Any]:
    """Load dashboard portal from index."""
    index = _read_json(index_path)
    if index.get("schema") != DASHBOARD_PORTAL_INDEX_SCHEMA_VERSION:
        raise DashboardPortalError("Invalid dashboard portal index schema.")

    payload = _read_json(index["payload_path"])
    html_text = Path(index["html_path"]).read_text(encoding="utf-8")

    issues = validate_dashboard_portal_payload(payload)
    if any(issue["severity"] == "error" for issue in issues):
        raise DashboardPortalError(f"Loaded dashboard portal validation errors: {issues}")

    return {
        "index": index,
        "payload": payload,
        "html": html_text,
        **build_research_safety_stamp(),
    }
