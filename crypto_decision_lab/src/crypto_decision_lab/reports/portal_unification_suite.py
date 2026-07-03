from __future__ import annotations

import hashlib
import html
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"
SAFETY_FLAGS: dict[str, Any] = {
    "app_mode": APP_MODE,
    "research_allowed": True,
    "hypothetical_only": True,
    "api_key_required": False,
    "api_key_present": False,
    "account_connection_required": False,
    "authenticated_connection_used": False,
    "orders_allowed": False,
    "orders_generated": False,
    "real_orders_generated": False,
    "real_capital_used": False,
    "trading_signal_generated": False,
    "executable_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "portfolio_decision_generated": False,
    "operational_decision_allowed": False,
}

FORBIDDEN_RENDERED_PHRASES = (
    "buy now",
    "sell now",
    "go long",
    "go short",
    "open a position",
    "close the position",
    "place a trade",
    "execute a trade",
    "submit an order",
    "send an order",
    "use real money",
    "use live capital",
    "connect exchange account",
    "api key required",
    "authenticated exchange used",
    "real orders generated: true",
    "orders_generated: true",
    "real_capital_used: true",
    "trading_signal_generated: true",
    "executable_signal_generated: true",
    "operational_decision_allowed: true",
)

PRIMARY_FAMILIES = {
    "dashboard_hub": ("dashboard", "hub", "portal"),
    "validation_stack": ("evidence_stack", "command_center", "acceptance", "gate"),
    "documentation_book": ("research_book", "book", "reader", "chronicle", "documentation"),
    "data_foundation": ("data_", "dataset_", "coverage", "quality", "schema", "contract"),
}

SECONDARY_FAMILIES = {
    "cleanup_inventory": ("cleanup", "inventory", "reconciliation", "workspace"),
    "risk_security": ("risk", "security", "policy", "human_review"),
    "scenario_stress": ("stress", "scenario", "benchmark", "slippage", "cost"),
}

@dataclass(frozen=True)
class Surface:
    kind: str
    path: str
    family: str
    title: str
    exists: bool = True


def _repo_root(start: str | Path | None = None) -> Path:
    here = Path(start or os.getcwd()).resolve()
    for p in [here, *here.parents]:
        if (p / "crypto_decision_lab").exists():
            return p
    return here


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except Exception:
        return str(path)


def _family_for(text: str) -> str:
    low = text.lower().replace("-", "_")
    for family, needles in PRIMARY_FAMILIES.items():
        if any(n in low for n in needles):
            return family
    for family, needles in SECONDARY_FAMILIES.items():
        if any(n in low for n in needles):
            return family
    return "other"


def _title_from_path(path: str) -> str:
    name = Path(path).stem.replace("_", " ").replace("-", " ").strip()
    return " ".join(w.capitalize() for w in name.split()) or path


def _scan_portal_indexes(root: Path) -> list[Surface]:
    roots = [root / "crypto_decision_lab" / "artifacts", root / "artifacts"]
    out: list[Surface] = []
    seen: set[str] = set()
    for base in roots:
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            low = p.name.lower()
            if low == "index.html" or low.endswith("_index.json") or "portal" in low:
                rel = _rel(p, root)
                if rel in seen:
                    continue
                seen.add(rel)
                out.append(Surface("portal_index", rel, _family_for(rel), _title_from_path(rel)))
    return out


def _scan_docs(root: Path) -> list[Surface]:
    base = root / "crypto_decision_lab" / "docs"
    out: list[Surface] = []
    if not base.exists():
        return out
    for p in sorted(base.rglob("*")):
        if p.is_file() and p.suffix.lower() in {".md", ".html", ".pdf"}:
            rel = _rel(p, root)
            out.append(Surface("doc", rel, _family_for(rel), _title_from_path(rel)))
    return out


def _scan_wrappers(root: Path) -> tuple[list[Surface], list[Surface]]:
    root_wrappers: list[Surface] = []
    script_wrappers: list[Surface] = []
    for p in sorted(root.glob("qrds*.sh")):
        if p.is_file():
            rel = _rel(p, root)
            root_wrappers.append(Surface("root_wrapper", rel, _family_for(rel), _title_from_path(rel)))
    scripts = root / "scripts"
    if scripts.exists():
        for p in sorted(scripts.glob("qrds*.sh")):
            if p.is_file():
                rel = _rel(p, root)
                script_wrappers.append(Surface("script_wrapper", rel, _family_for(rel), _title_from_path(rel)))
    return root_wrappers, script_wrappers


def _launcher_candidates(surfaces: Iterable[Surface]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for s in surfaces:
        low = s.path.lower()
        if s.kind.endswith("wrapper") and ("serve" in low or "portal" in low or "dashboard" in low or "book" in low):
            rows.append({"family": s.family, "kind": s.kind, "path": s.path, "title": s.title})
    return sorted(rows, key=lambda r: (r["family"], r["path"]))


def _family_rows(surfaces: list[Surface]) -> list[dict[str, Any]]:
    families = sorted({s.family for s in surfaces})
    rows: list[dict[str, Any]] = []
    for family in families:
        fs = [s for s in surfaces if s.family == family]
        rows.append({
            "family": family,
            "portal_indexes": sum(1 for s in fs if s.kind == "portal_index"),
            "docs": sum(1 for s in fs if s.kind == "doc"),
            "root_wrappers": sum(1 for s in fs if s.kind == "root_wrapper"),
            "script_wrappers": sum(1 for s in fs if s.kind == "script_wrapper"),
            "ready": family in PRIMARY_FAMILIES and any(s.kind == "portal_index" for s in fs) and any(s.kind == "root_wrapper" for s in fs),
            "examples": [s.path for s in fs[:8]],
        })
    return rows


def _candidate_url(path: str) -> str:
    # qrds_unified_portal_serve.sh serves the repo root, so repo-relative links work.
    return "/" + path.replace("\\", "/")


def _sha_payload(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _criterion(criterion_id: str, status: str, ready: bool, observed: Any, threshold: str, blocker: str = "") -> dict[str, Any]:
    return {
        "criterion_id": criterion_id,
        "status": status,
        "ready": bool(ready),
        "observed": observed,
        "threshold": threshold,
        "blocker": blocker,
    }


def _git_status_lines(root: Path) -> int:
    try:
        import subprocess
        proc = subprocess.run(["git", "status", "--short"], cwd=root, text=True, capture_output=True, check=False)
        return len([line for line in proc.stdout.splitlines() if line.strip()])
    except Exception:
        return -1


def _assert_research_only(rendered: str) -> None:
    low = rendered.lower()
    for term in FORBIDDEN_RENDERED_PHRASES:
        if term in low:
            raise ValueError(f"Operational language is not allowed in portal unification suite: {term}")


def render_markdown(payload: dict[str, Any]) -> str:
    def table(headers: list[str], rows: list[list[Any]]) -> str:
        out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
        for row in rows:
            out.append("|" + "|".join(str(x) for x in row) + "|")
        return "\n".join(out)

    md = f"""# QRDS/QOS • Gate BTC • Research-only
## Unified Portal Launcher Suite

This page reconciles portal, validation, data, and documentation surfaces into one launcher map. It is navigation only and cannot unlock operational use.

**Gate answer:** {payload['gate_answer']}

**Policy lock:** {payload['policy_lock']} • **Mode:** {payload['app_mode']}

## Summary

- Portal indexes: {payload['portal_index_count']}
- Docs files: {payload['docs_file_count']}
- Root wrappers: {payload['root_wrapper_count']}
- Script wrappers: {payload['script_wrapper_count']}
- Families found: {payload['families_found_count']}
- Primary families ready: {payload['primary_families_ready']}/{payload['primary_families_total']}
- Launcher candidates: {payload['launcher_candidate_count']}
- Git status lines: {payload['git_status_lines']}
- Criteria ready: {payload['criteria_ready_count']}/{payload['criteria_total_count']}
- Mean launcher score: {payload['mean_launcher_score']}

Research-only guardrail active. No exchange account, no orders, no reference page, no execution-style instruction, no live-fund workflow marker.

## Family map

{table(['family', 'portal_indexes', 'docs', 'root_wrappers', 'script_wrappers', 'ready'], [[r['family'], r['portal_indexes'], r['docs'], r['root_wrappers'], r['script_wrappers'], r['ready']] for r in payload['family_rows']])}

## Launcher candidates

{table(['family', 'kind', 'path'], [[r['family'], r['kind'], r['path']] for r in payload['launcher_candidates'][:80]])}

## Criteria

{table(['criterion_id', 'status', 'ready', 'observed', 'threshold', 'blocker'], [[c['criterion_id'], c['status'], c['ready'], c['observed'], c['threshold'], c['blocker']] for c in payload['criteria']])}

Generated at {payload['generated_at']} • SHA256 {payload['report_payload_sha256']}
"""
    _assert_research_only(md)
    return md


def render_html(payload: dict[str, Any]) -> str:
    def esc(x: Any) -> str:
        return html.escape(str(x))

    family_cards = []
    for row in payload["family_rows"]:
        examples = "".join(f"<li><a href='{esc(_candidate_url(p))}'>{esc(p)}</a></li>" for p in row.get("examples", [])[:8])
        family_cards.append(
            f"<div class='card'><h3>{esc(row['family'])}</h3>"
            f"<p>Portals: {esc(row['portal_indexes'])} • Docs: {esc(row['docs'])} • Root wrappers: {esc(row['root_wrappers'])} • Script wrappers: {esc(row['script_wrappers'])} • Ready: {esc(row['ready'])}</p>"
            f"<ul>{examples}</ul></div>"
        )

    launch_rows = "\n".join(
        f"<tr><td>{esc(r['family'])}</td><td>{esc(r['kind'])}</td><td><a href='{esc(_candidate_url(r['path']))}'>{esc(r['path'])}</a></td></tr>"
        for r in payload["launcher_candidates"][:160]
    ) or "<tr><td>NONE</td><td>MISSING</td><td>MISSING</td></tr>"

    criteria_rows = "\n".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td><td>{esc(c['blocker'])}</td></tr>"
        for c in payload["criteria"]
    )

    page = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>QRDS Unified Portal Launcher Suite</title>
<style>
body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}
.card{{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}}
.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px 8px 8px 0}}
table{{border-collapse:collapse;width:100%;background:white;margin-top:10px}}
th,td{{border:1px solid #d9deea;padding:8px;text-align:left;font-size:14px}}
th{{background:#eef2ff}}
a{{color:#1d4ed8}}
.badge{{display:inline-block;background:#dcfce7;border-radius:999px;padding:6px 10px;font-weight:700}}
</style></head><body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1>
<h2>Unified Portal Launcher Suite</h2>
<p>This page reconciles portal, validation, data, and documentation surfaces into one navigation map. It cannot unlock operational use.</p>
<div class='card'>
<p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p>
<p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>
<div class='kpi'><b>Portal indexes</b><br>{esc(payload['portal_index_count'])}</div>
<div class='kpi'><b>Docs files</b><br>{esc(payload['docs_file_count'])}</div>
<div class='kpi'><b>Root wrappers</b><br>{esc(payload['root_wrapper_count'])}</div>
<div class='kpi'><b>Script wrappers</b><br>{esc(payload['script_wrapper_count'])}</div>
<div class='kpi'><b>Families found</b><br>{esc(payload['families_found_count'])}</div>
<div class='kpi'><b>Primary families ready</b><br>{esc(payload['primary_families_ready'])}/{esc(payload['primary_families_total'])}</div>
<div class='kpi'><b>Launcher candidates</b><br>{esc(payload['launcher_candidate_count'])}</div>
<div class='kpi'><b>Git status lines</b><br>{esc(payload['git_status_lines'])}</div>
<div class='kpi'><b>Criteria ready</b><br>{esc(payload['criteria_ready_count'])}/{esc(payload['criteria_total_count'])}</div>
<div class='kpi'><b>Mean launcher score</b><br>{esc(payload['mean_launcher_score'])}</div>
<p class='badge'>Research-only guardrail active</p>
<p>Safety lock remains active for account access, order flow, execution-style instructions, and live-fund workflow markers.</p>
</div>
<h2>Primary portal families</h2>
{''.join(family_cards)}
<h2>Launcher candidates</h2>
<table><thead><tr><th>family</th><th>kind</th><th>path</th></tr></thead><tbody>{launch_rows}</tbody></table>
<h2>Criteria</h2>
<table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th><th>blocker</th></tr></thead><tbody>{criteria_rows}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p>
</body></html>"""
    _assert_research_only(page)
    return page


def build_portal_unification_suite(output_dir: str | Path, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    if not out.is_absolute():
        out = root / "crypto_decision_lab" / out if str(out).startswith("artifacts/") else out
    out.mkdir(parents=True, exist_ok=True)

    portal_indexes = _scan_portal_indexes(root)
    docs = _scan_docs(root)
    root_wrappers, script_wrappers = _scan_wrappers(root)
    all_surfaces = portal_indexes + docs + root_wrappers + script_wrappers
    family_rows = _family_rows(all_surfaces)
    launchers = _launcher_candidates(all_surfaces)

    primary_ready = sum(1 for r in family_rows if r["family"] in PRIMARY_FAMILIES and r["ready"])
    primary_total = len(PRIMARY_FAMILIES)
    git_lines = _git_status_lines(root)

    criteria = [
        _criterion("portal_indexes_present", "PASS" if portal_indexes else "FAIL", bool(portal_indexes), len(portal_indexes), ">= 1 portal index", "" if portal_indexes else "Need at least one generated portal index."),
        _criterion("docs_present", "PASS" if docs else "FAIL", bool(docs), len(docs), ">= 1 docs file", "" if docs else "Need documentation surfaces."),
        _criterion("primary_families_ready", "PASS" if primary_ready == primary_total else "WARN", primary_ready >= 3, f"{primary_ready}/{primary_total}", ">= 3 primary families ready", "" if primary_ready >= 3 else "Need dashboard/validation/docs/data launchers."),
        _criterion("launcher_candidates_present", "PASS" if launchers else "FAIL", bool(launchers), len(launchers), ">= 1 launcher", "" if launchers else "Need serve wrappers or launchers."),
        _criterion("git_status_observed", "PASS" if git_lines >= 0 else "WARN", git_lines >= 0, git_lines, "git status readable", "" if git_lines >= 0 else "Git status unavailable."),
        _criterion("research_only_lock", "PASS", True, "ACTIVE", "policy lock active"),
    ]
    ready_count = sum(1 for c in criteria if c["ready"])
    mean_score = round(ready_count / len(criteria), 4)

    gate_answer = "PORTAL_UNIFICATION_SUITE_READY_RESEARCH_ONLY" if primary_ready >= 3 and launchers else "PORTAL_UNIFICATION_SUITE_PARTIAL_REVIEW_REQUIRED_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.portal_unification_suite.v1",
        "report_name": "qrds-portal-unification-suite",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "portal_index_count": len(portal_indexes),
        "docs_file_count": len(docs),
        "root_wrapper_count": len(root_wrappers),
        "script_wrapper_count": len(script_wrappers),
        "families_found_count": len({s.family for s in all_surfaces}),
        "primary_families_ready": primary_ready,
        "primary_families_total": primary_total,
        "launcher_candidate_count": len(launchers),
        "git_status_lines": git_lines,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_launcher_score": mean_score,
        "criteria": criteria,
        "family_rows": family_rows,
        "launcher_candidates": launchers,
        "portal_indexes": [s.__dict__ for s in portal_indexes],
        "docs": [s.__dict__ for s in docs],
        "root_wrappers": [s.__dict__ for s in root_wrappers],
        "script_wrappers": [s.__dict__ for s in script_wrappers],
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    report_path = out / "portal_unification_suite.json"
    markdown_path = out / "portal_unification_suite.md"
    html_path = out / "index.html"
    index_path = out / "portal_unification_suite_index.json"
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    def out_rel(p: Path) -> str:
        return _rel(p, root)

    index = {
        "schema": "qrds.portal_unification_suite_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "portal_index_count": payload["portal_index_count"],
        "docs_file_count": payload["docs_file_count"],
        "root_wrapper_count": payload["root_wrapper_count"],
        "script_wrapper_count": payload["script_wrapper_count"],
        "families_found_count": payload["families_found_count"],
        "primary_families_ready": payload["primary_families_ready"],
        "primary_families_total": payload["primary_families_total"],
        "launcher_candidate_count": payload["launcher_candidate_count"],
        "git_status_lines": payload["git_status_lines"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_launcher_score": payload["mean_launcher_score"],
        "report_path": out_rel(report_path),
        "markdown_path": out_rel(markdown_path),
        "html_path": out_rel(html_path),
        "index_path": out_rel(index_path),
        "serve_entrypoint": out_rel(html_path),
        "report_payload_sha256": payload["report_payload_sha256"],
        "payload": payload,
        **SAFETY_FLAGS,
    }
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    return index


build_unified_portal_launcher = build_portal_unification_suite
