from __future__ import annotations

import hashlib
import html
import json
import subprocess
from collections import Counter, defaultdict
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
    "buy signal",
    "sell signal",
    "execute trade",
    "use real capital",
    "position sizing",
)

PORTAL_HINTS = (
    "portal",
    "dashboard",
    "hub",
    "reader",
    "chronicle",
    "command_center",
    "evidence_stack",
    "acceptance",
    "book",
    "guide",
)


def _repo_root(repo_root: str | Path | None = None) -> Path:
    if repo_root is not None:
        return Path(repo_root).resolve()
    here = Path.cwd().resolve()
    for p in [here, *here.parents]:
        if (p / "crypto_decision_lab").exists():
            return p
    return here


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except Exception:
        return str(path)


def _sha_payload(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _git_status_lines(root: Path) -> list[str]:
    try:
        proc = subprocess.run(
            ["git", "status", "--short"],
            cwd=str(root),
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        if proc.returncode != 0:
            return ["GIT_STATUS_UNAVAILABLE"]
        return [line for line in proc.stdout.splitlines() if line.strip()]
    except Exception:
        return ["GIT_STATUS_UNAVAILABLE"]


def _family(path_text: str) -> str:
    low = path_text.lower().replace("-", "_")
    if any(k in low for k in ("research_book", "book_reader", "book_chronicle", "chapter", "reader_portal")):
        return "documentation_book"
    if any(k in low for k in ("evidence_stack", "command_center", "acceptance", "promotion", "human_review", "paper_trading", "oos", "risk_model", "security_review")):
        return "validation_stack"
    if any(k in low for k in ("data_", "dataset_", "schema", "source_contract", "acquisition", "coverage", "quality", "audit", "readiness", "remediation")):
        return "data_foundation"
    if any(k in low for k in ("dashboard_hub", "unified_portal", "portal", "dashboard", "hub")):
        return "general_portal"
    if any(k in low for k in ("guide", "interpretation")):
        return "guide"
    return "other"


def _scan_files(root: Path) -> dict[str, list[Path]]:
    project = root / "crypto_decision_lab"
    files: dict[str, list[Path]] = {
        "portal_indexes": [],
        "docs_files": [],
        "root_wrappers": [],
        "script_wrappers": [],
    }

    for base in (project / "artifacts", root / "artifacts"):
        if base.exists():
            files["portal_indexes"].extend(sorted(base.rglob("index.html")))

    docs_root = project / "docs"
    if docs_root.exists():
        files["docs_files"].extend(sorted(docs_root.rglob("*.md")))

    files["root_wrappers"].extend(sorted(root.glob("qrds_*.sh")))
    scripts_root = root / "scripts"
    if scripts_root.exists():
        files["script_wrappers"].extend(sorted(scripts_root.glob("qrds_*.sh")))

    return files


def _row(path: Path, root: Path, item_type: str) -> dict[str, Any]:
    rel = _rel(path, root)
    return {
        "type": item_type,
        "path": rel,
        "family": _family(rel),
        "exists": path.exists(),
    }


def _pick_primary(items: list[dict[str, Any]], family: str) -> list[dict[str, Any]]:
    ranked: list[tuple[int, dict[str, Any]]] = []
    for item in items:
        if item.get("family") != family:
            continue
        low = str(item.get("path", "")).lower()
        score = 0
        if "index.html" in low:
            score += 2
        if "serve" in low:
            score += 2
        if family == "general_portal" and any(k in low for k in ("unified", "hub", "portal")):
            score += 5
        if family == "validation_stack" and any(k in low for k in ("evidence_stack", "command_center", "acceptance")):
            score += 5
        if family == "documentation_book" and any(k in low for k in ("book_reader", "research_book", "chronicle")):
            score += 5
        if family == "data_foundation" and any(k in low for k in ("data_source_contract", "data_acquisition", "dataset_depth")):
            score += 4
        ranked.append((score, item))
    ranked.sort(key=lambda x: (x[0], x[1].get("path", "")), reverse=True)
    return [x[1] for x in ranked[:6]]


def _launcher_candidates(root: Path, all_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    launchers = [x for x in all_items if x["type"] in {"root_wrapper", "script_wrapper"}]
    for item in launchers:
        name = Path(str(item["path"])).name
        item["command"] = f"bash {item['path']}" if "/" in item["path"] else f"bash {name}"
        item["serve_like"] = "serve" in name.lower()
    return sorted(launchers, key=lambda r: (not r.get("serve_like"), r.get("family", ""), r.get("path", "")))


def _criterion(criterion_id: str, status: str, ready: bool, observed: Any, threshold: str, blocker: str = "") -> dict[str, Any]:
    return {
        "criterion_id": criterion_id,
        "status": status,
        "ready": bool(ready),
        "observed": observed,
        "threshold": threshold,
        "blocker": blocker,
    }


def _table_md(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(x) for x in row) + "|")
    return "\n".join(out)


def _assert_research_only(rendered: str) -> None:
    low = rendered.lower()
    for phrase in FORBIDDEN_RENDERED_PHRASES:
        if phrase in low:
            raise ValueError(f"Operational language is not allowed in Portal Reconciliation: {phrase}")


def render_markdown(payload: dict[str, Any]) -> str:
    family_rows = [[k, v] for k, v in sorted(payload["family_counts"].items())]
    primary_rows = [
        [family, item.get("type"), item.get("path")]
        for family, rows in payload["primary_surfaces"].items()
        for item in rows[:4]
    ] or [["NONE", "MISSING", "MISSING"]]
    launcher_rows = [
        [x.get("family"), x.get("type"), x.get("path"), x.get("command")]
        for x in payload["launcher_candidates"][:60]
    ] or [["NONE", "MISSING", "MISSING", "MISSING"]]
    criteria_rows = [[c["criterion_id"], c["status"], c["ready"], c["observed"], c["threshold"], c["blocker"]] for c in payload["criteria"]]
    flag_rows = [[k, v] for k, v in payload["safety_flags"].items()]

    md = f"""# QRDS/QOS • Gate BTC • Research-only
## Portal Reconciliation / Unified Launcher Map

This artifact reconciles the workspace portal surfaces, documentation portals, validation portals, and launcher scripts into a single research-only map. It is an inventory and navigation layer only; it cannot unlock operational use.

**Gate answer:** {payload['gate_answer']}

**Policy lock:** {payload['policy_lock']} • **Mode:** {payload['app_mode']}

## Summary

- Portal indexes: {payload['portal_index_count']}
- Docs files: {payload['docs_file_count']}
- Root wrappers: {payload['root_wrapper_count']}
- Script wrappers: {payload['script_wrapper_count']}
- Families found: {payload['family_count']}
- Primary families ready: {payload['primary_family_ready_count']}/{payload['primary_family_total_count']}
- Launcher candidates: {payload['launcher_candidate_count']}
- Git status lines: {payload['git_status_line_count']}
- Criteria ready: {payload['criteria_ready_count']}/{payload['criteria_total_count']}
- Mean reconciliation score: {payload['mean_reconciliation_score']}

Research-only guardrail: no exchange account, no orders, no portfolio allocation output, no executable market instruction, no live-fund workflow.

## Family counts

{_table_md(['family', 'count'], family_rows)}

## Primary surfaces

{_table_md(['family', 'type', 'path'], primary_rows)}

## Launcher candidates

{_table_md(['family', 'type', 'path', 'command'], launcher_rows)}

## Criteria

{_table_md(['criterion_id', 'status', 'ready', 'observed', 'threshold', 'blocker'], criteria_rows)}

## Safety flags

{_table_md(['flag', 'value'], flag_rows)}

Generated at {payload['generated_at']} • SHA256 {payload['report_payload_sha256']}
"""
    _assert_research_only(md)
    return md


def render_html(payload: dict[str, Any]) -> str:
    def esc(x: Any) -> str:
        return html.escape(str(x))

    def rows(data: Iterable[Iterable[Any]]) -> str:
        return "\n".join("<tr>" + "".join(f"<td>{esc(v)}</td>" for v in row) + "</tr>" for row in data)

    family_rows = rows([[k, v] for k, v in sorted(payload["family_counts"].items())])
    primary_rows = rows(
        [[family, item.get("type"), item.get("path")] for family, surfaces in payload["primary_surfaces"].items() for item in surfaces[:6]]
    ) or "<tr><td>NONE</td><td>MISSING</td><td>MISSING</td></tr>"
    launcher_rows = rows([[x.get("family"), x.get("type"), x.get("path"), x.get("command")] for x in payload["launcher_candidates"][:80]])
    criteria_rows = rows([[c["criterion_id"], c["status"], c["ready"], c["observed"], c["threshold"], c["blocker"]] for c in payload["criteria"]])
    flag_rows = rows([[k, v] for k, v in payload["safety_flags"].items()])

    page = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>QRDS Portal Reconciliation</title>
<style>
body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}
.card{{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}}
.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px 8px 8px 0}}
table{{border-collapse:collapse;width:100%;background:white;margin:12px 0}}
th,td{{border:1px solid #d9deea;padding:8px;text-align:left;font-size:14px;vertical-align:top}}
th{{background:#eef2ff}}
.badge{{display:inline-block;background:#dcfce7;border-radius:999px;padding:6px 10px;font-weight:700}}
code{{background:#f1f5f9;padding:2px 5px;border-radius:5px}}
</style></head><body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1>
<h2>Portal Reconciliation / Unified Launcher Map</h2>
<p>This artifact reconciles portal surfaces, docs, validation portals, and launchers into one research-only map. It cannot unlock operational use.</p>
<div class='card'>
<p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p>
<p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>
<div class='kpi'><b>Portal indexes</b><br>{esc(payload['portal_index_count'])}</div>
<div class='kpi'><b>Docs files</b><br>{esc(payload['docs_file_count'])}</div>
<div class='kpi'><b>Root wrappers</b><br>{esc(payload['root_wrapper_count'])}</div>
<div class='kpi'><b>Script wrappers</b><br>{esc(payload['script_wrapper_count'])}</div>
<div class='kpi'><b>Families found</b><br>{esc(payload['family_count'])}</div>
<div class='kpi'><b>Primary families ready</b><br>{esc(payload['primary_family_ready_count'])}/{esc(payload['primary_family_total_count'])}</div>
<div class='kpi'><b>Launcher candidates</b><br>{esc(payload['launcher_candidate_count'])}</div>
<div class='kpi'><b>Git status lines</b><br>{esc(payload['git_status_line_count'])}</div>
<div class='kpi'><b>Mean score</b><br>{esc(payload['mean_reconciliation_score'])}</div>
<p class='badge'>Research-only guardrail active</p>
<p>No exchange account, no orders, no portfolio allocation output, no executable market instruction, no live-fund workflow.</p>
</div>
<h2>Family counts</h2><table><thead><tr><th>family</th><th>count</th></tr></thead><tbody>{family_rows}</tbody></table>
<h2>Primary surfaces</h2><table><thead><tr><th>family</th><th>type</th><th>path</th></tr></thead><tbody>{primary_rows}</tbody></table>
<h2>Launcher candidates</h2><table><thead><tr><th>family</th><th>type</th><th>path</th><th>command</th></tr></thead><tbody>{launcher_rows}</tbody></table>
<h2>Criteria</h2><table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th><th>blocker</th></tr></thead><tbody>{criteria_rows}</tbody></table>
<h2>Safety flags</h2><table><thead><tr><th>flag</th><th>value</th></tr></thead><tbody>{flag_rows}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p>
</body></html>"""
    _assert_research_only(page)
    return page


def build_portal_reconciliation(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    if not out.is_absolute():
        out = (root / "crypto_decision_lab" / out).resolve() if str(out).startswith("artifacts") else (Path.cwd() / out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    scanned = _scan_files(root)
    items: list[dict[str, Any]] = []
    for key, item_type in (
        ("portal_indexes", "portal_index"),
        ("docs_files", "docs_file"),
        ("root_wrappers", "root_wrapper"),
        ("script_wrappers", "script_wrapper"),
    ):
        items.extend(_row(path, root, item_type) for path in scanned[key])

    family_counts = Counter(item["family"] for item in items)
    launcher_candidates = _launcher_candidates(root, items)
    primary_families = ["general_portal", "validation_stack", "documentation_book", "data_foundation"]
    primary_surfaces = {family: _pick_primary(items, family) for family in primary_families}
    primary_ready_count = sum(1 for rows in primary_surfaces.values() if rows)

    portal_index_count = len(scanned["portal_indexes"])
    docs_file_count = len(scanned["docs_files"])
    root_wrapper_count = len(scanned["root_wrappers"])
    script_wrapper_count = len(scanned["script_wrappers"])
    family_count = len([k for k, v in family_counts.items() if v > 0])
    git_lines = _git_status_lines(root)

    criteria = [
        _criterion("portal_indexes_present", "PASS" if portal_index_count else "FAIL", portal_index_count > 0, portal_index_count, ">= 1 portal index", "" if portal_index_count else "Need generated portal indexes."),
        _criterion("documentation_surfaces_present", "PASS" if docs_file_count else "FAIL", docs_file_count > 0, docs_file_count, ">= 1 docs file", "" if docs_file_count else "Need documentation files."),
        _criterion("launcher_wrappers_present", "PASS" if root_wrapper_count else "FAIL", root_wrapper_count > 0, root_wrapper_count, ">= 1 root launcher", "" if root_wrapper_count else "Need launcher wrappers."),
        _criterion("primary_families_mapped", "PASS" if primary_ready_count >= 3 else "WARN", primary_ready_count >= 3, f"{primary_ready_count}/{len(primary_families)}", ">= 3 primary families", "" if primary_ready_count >= 3 else "Some portal families need reconciliation."),
        _criterion("validation_stack_visible", "PASS" if primary_surfaces["validation_stack"] else "WARN", bool(primary_surfaces["validation_stack"]), len(primary_surfaces["validation_stack"]), ">= 1 validation portal surface", "" if primary_surfaces["validation_stack"] else "Validation portal not found."),
        _criterion("documentation_book_visible", "PASS" if primary_surfaces["documentation_book"] else "WARN", bool(primary_surfaces["documentation_book"]), len(primary_surfaces["documentation_book"]), ">= 1 documentation/book surface", "" if primary_surfaces["documentation_book"] else "Documentation/book portal not found."),
        _criterion("research_only_lock", "PASS", True, "ACTIVE", "policy lock active", ""),
    ]

    ready_count = sum(1 for c in criteria if c["ready"])
    mean_score = round(ready_count / len(criteria), 4)

    if portal_index_count == 0 and docs_file_count == 0:
        gate_answer = "NO_PORTAL_RECONCILIATION_SURFACES_FOUND_RESEARCH_ONLY"
    elif primary_ready_count >= 3 and root_wrapper_count > 0:
        gate_answer = "PORTAL_RECONCILIATION_READY_RESEARCH_ONLY"
    else:
        gate_answer = "PORTAL_RECONCILIATION_PARTIAL_MAP_REVIEW_REQUIRED_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.portal_reconciliation.v1",
        "report_name": "qrds-portal-reconciliation-unified-launcher-map",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "portal_index_count": portal_index_count,
        "docs_file_count": docs_file_count,
        "root_wrapper_count": root_wrapper_count,
        "script_wrapper_count": script_wrapper_count,
        "family_counts": dict(sorted(family_counts.items())),
        "family_count": family_count,
        "primary_family_ready_count": primary_ready_count,
        "primary_family_total_count": len(primary_families),
        "primary_surfaces": primary_surfaces,
        "launcher_candidate_count": len(launcher_candidates),
        "launcher_candidates": launcher_candidates,
        "portal_indexes": [_row(p, root, "portal_index") for p in scanned["portal_indexes"]],
        "docs_files": [_row(p, root, "docs_file") for p in scanned["docs_files"]],
        "git_status_lines": git_lines,
        "git_status_line_count": len(git_lines),
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_reconciliation_score": mean_score,
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    report_path = out / "portal_reconciliation.json"
    md_path = out / "portal_reconciliation.md"
    html_path = out / "index.html"
    index_path = out / "portal_reconciliation_index.json"

    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    index = {
        "schema": "qrds.portal_reconciliation_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "portal_index_count": payload["portal_index_count"],
        "docs_file_count": payload["docs_file_count"],
        "root_wrapper_count": payload["root_wrapper_count"],
        "script_wrapper_count": payload["script_wrapper_count"],
        "family_count": payload["family_count"],
        "primary_family_ready_count": payload["primary_family_ready_count"],
        "primary_family_total_count": payload["primary_family_total_count"],
        "launcher_candidate_count": payload["launcher_candidate_count"],
        "git_status_line_count": payload["git_status_line_count"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_reconciliation_score": payload["mean_reconciliation_score"],
        "report_path": str(report_path),
        "markdown_path": str(md_path),
        "html_path": str(html_path),
        "index_path": str(index_path),
        "serve_entrypoint": str(html_path),
        "report_payload_sha256": payload["report_payload_sha256"],
        "payload": payload,
        **SAFETY_FLAGS,
    }
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    return index


build_unified_launcher_map = build_portal_reconciliation
