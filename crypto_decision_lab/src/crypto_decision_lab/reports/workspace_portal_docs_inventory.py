from __future__ import annotations

import hashlib
import html
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
    "position sizing",
    "use real capital",
    "execute trade",
    "trading signal:",
    "buy signal",
    "sell signal",
)


def _repo_root(start: str | Path | None = None) -> Path:
    base = Path(start or os.getcwd()).resolve()
    for p in [base, *base.parents]:
        if (p / "crypto_decision_lab").exists():
            return p
    return base


def _sha_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()[:16]
    except Exception:
        return "UNREADABLE"


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except Exception:
        return str(path)


def _is_ignored_path(path: Path) -> bool:
    parts = {p.lower() for p in path.parts}
    return bool({".git", "__pycache__", ".pytest_cache", ".mypy_cache"} & parts)


def _classify_artifact_dir(path: Path) -> str:
    name = path.name.lower()
    text = str(path).lower()
    if "research_book" in text or "book" in name or "chronicle" in name or "reader" in name:
        return "documentation_book_portal"
    if "command_center" in text or "evidence_stack" in text or "acceptance" in text or "gate" in name:
        return "validation_gate_portal"
    if "dashboard" in text or "portal" in name or "hub" in name:
        return "general_dashboard_portal"
    if "data" in name or "dataset" in name or "source" in name:
        return "data_foundation_artifact"
    return "other_artifact"


def _find_files(root: Path, base: Path, suffixes: set[str] | None = None, max_items: int = 500) -> list[dict[str, Any]]:
    if not base.exists():
        return []
    out: list[dict[str, Any]] = []
    for p in sorted(base.rglob("*")):
        if len(out) >= max_items:
            break
        if not p.is_file() or _is_ignored_path(p):
            continue
        if suffixes and p.suffix.lower() not in suffixes:
            continue
        out.append({"path": _rel(root, p), "size_bytes": p.stat().st_size, "sha256": _sha_file(p)})
    return out


def _root_wrappers(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for p in sorted(root.glob("qrds*.sh")):
        if p.is_file():
            rows.append({"path": _rel(root, p), "size_bytes": p.stat().st_size, "sha256": _sha_file(p)})
    return rows


def _script_wrappers(root: Path) -> list[dict[str, Any]]:
    return _find_files(root, root / "scripts", {".sh"}, 500)


def _duplicate_wrappers(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    scripts_dir = root / "scripts"
    if not scripts_dir.exists():
        return rows
    for sp in sorted(scripts_dir.glob("qrds*.sh")):
        rp = root / sp.name
        if rp.exists() and rp.is_file():
            same = _sha_file(sp) == _sha_file(rp)
            rows.append({"script_path": _rel(root, sp), "root_path": _rel(root, rp), "same_content": same})
    return rows


def _portal_indexes(root: Path, max_items: int = 500) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    candidates = [root / "artifacts", root / "crypto_decision_lab" / "artifacts"]
    for base in candidates:
        if not base.exists():
            continue
        for p in sorted(base.rglob("index.html")):
            if len(rows) >= max_items:
                break
            if _is_ignored_path(p):
                continue
            rows.append({
                "path": _rel(root, p),
                "family": _classify_artifact_dir(p.parent),
                "artifact_dir": _rel(root, p.parent),
                "size_bytes": p.stat().st_size,
                "sha256": _sha_file(p),
            })
    return rows


def _artifact_dirs(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for base in [root / "artifacts", root / "crypto_decision_lab" / "artifacts"]:
        if not base.exists():
            continue
        for p in sorted(base.iterdir()):
            if p.is_dir() and not _is_ignored_path(p):
                files = [x for x in p.rglob("*") if x.is_file() and not _is_ignored_path(x)]
                rows.append({
                    "path": _rel(root, p),
                    "family": _classify_artifact_dir(p),
                    "file_count": len(files),
                    "has_index_html": (p / "index.html").exists(),
                })
    return rows


def _docs_inventory(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for base in [root / "crypto_decision_lab" / "docs", root / "docs"]:
        for item in _find_files(root, base, {".md", ".html", ".json", ".pdf"}, 1000):
            path = str(item["path"])
            if "/book/" in path or "research_book" in path.lower():
                family = "book_docs"
            elif "/reports/" in path:
                family = "report_docs"
            else:
                family = "other_docs"
            item["family"] = family
            rows.append(item)
    return rows


def _cleanup_candidates(root: Path) -> list[dict[str, Any]]:
    patterns = ["*.bak*", "*.tmp", "*.orig", "qrds_hotfix*.sh", "qrds_sprint_*_hotfix*.sh"]
    rows: list[dict[str, Any]] = []
    for pattern in patterns:
        for p in sorted(root.rglob(pattern)):
            if p.is_file() and not _is_ignored_path(p):
                rows.append({"path": _rel(root, p), "reason": f"matches {pattern}", "size_bytes": p.stat().st_size})
    seen: set[str] = set()
    uniq: list[dict[str, Any]] = []
    for r in rows:
        if r["path"] not in seen:
            seen.add(r["path"])
            uniq.append(r)
    return uniq[:500]


def _git_status(root: Path) -> list[str]:
    import subprocess

    try:
        proc = subprocess.run(["git", "status", "--short"], cwd=root, check=False, capture_output=True, text=True, timeout=20)
        return [line for line in proc.stdout.splitlines() if line.strip()]
    except Exception as exc:
        return [f"GIT_STATUS_UNAVAILABLE: {exc}"]


def _criterion(criterion_id: str, status: str, ready: bool, observed: Any, threshold: str, blocker: str = "") -> dict[str, Any]:
    return {"criterion_id": criterion_id, "status": status, "ready": bool(ready), "observed": observed, "threshold": threshold, "blocker": blocker}


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(x) for x in row) + "|")
    return "\n".join(out)


def _assert_research_only(rendered: str) -> None:
    low = rendered.lower()
    for term in FORBIDDEN_RENDERED_PHRASES:
        if term in low:
            raise ValueError(f"Operational language is not allowed in Workspace Portal Docs Inventory: {term}")


def render_markdown(payload: dict[str, Any]) -> str:
    git_snapshot = "\n".join(payload["git_status"]) if payload["git_status"] else "CLEAN"
    md = f"""# QRDS/QOS • Gate BTC • Research-only
## Workspace / Portal / Docs Inventory Map

This artifact maps the current workspace, portal families, documentation surfaces, wrappers, generated artifacts, and cleanup candidates. It is an inventory and cannot unlock operational use.

**Gate answer:** {payload['gate_answer']}

**Policy lock:** {payload['policy_lock']} • **Mode:** {payload['app_mode']}

## Summary

- Portal indexes: {payload['portal_index_count']}
- Artifact dirs: {payload['artifact_dir_count']}
- Docs files: {payload['docs_file_count']}
- Root wrappers: {payload['root_wrapper_count']}
- Script wrappers: {payload['script_wrapper_count']}
- Duplicate wrappers: {payload['duplicate_wrapper_count']}
- Cleanup candidates: {payload['cleanup_candidate_count']}
- Git status lines: {payload['git_status_count']}
- Criteria ready: {payload['criteria_ready_count']}/{payload['criteria_total_count']}
- Mean inventory score: {payload['mean_inventory_score']}

Research-only guardrail: no exchange account, no orders, no portfolio allocation output, no executable instruction, no live-fund workflow.

## Portal families

{_table(['family', 'count'], [[k, v] for k, v in payload['portal_family_counts'].items()] or [['NONE', 0]])}

## Portal indexes

{_table(['family', 'path'], [[r['family'], r['path']] for r in payload['portal_indexes'][:80]] or [['NONE', 'MISSING']])}

## Documentation files

{_table(['family', 'path'], [[r['family'], r['path']] for r in payload['docs_files'][:120]] or [['NONE', 'MISSING']])}

## Duplicate wrappers

{_table(['same_content', 'script_path', 'root_path'], [[r['same_content'], r['script_path'], r['root_path']] for r in payload['duplicate_wrappers'][:80]] or [['NONE', 'NONE', 'NONE']])}

## Cleanup candidates review list

{_table(['reason', 'path'], [[r['reason'], r['path']] for r in payload['cleanup_candidates'][:120]] or [['NONE', 'NONE']])}

## Criteria

{_table(['criterion_id', 'status', 'ready', 'observed', 'threshold', 'blocker'], [[c['criterion_id'], c['status'], c['ready'], c['observed'], c['threshold'], c['blocker']] for c in payload['criteria']])}

## Git status snapshot

```text
{git_snapshot}
```

Generated at {payload['generated_at']} • SHA256 {payload['report_payload_sha256']}
"""
    _assert_research_only(md)
    return md


def render_html(payload: dict[str, Any]) -> str:
    def esc(x: Any) -> str:
        return html.escape(str(x))

    family_rows = "".join(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>" for k, v in payload["portal_family_counts"].items()) or "<tr><td>NONE</td><td>0</td></tr>"
    portal_rows = "".join(f"<tr><td>{esc(r['family'])}</td><td>{esc(r['path'])}</td></tr>" for r in payload["portal_indexes"][:100]) or "<tr><td>NONE</td><td>MISSING</td></tr>"
    docs_rows = "".join(f"<tr><td>{esc(r['family'])}</td><td>{esc(r['path'])}</td></tr>" for r in payload["docs_files"][:160]) or "<tr><td>NONE</td><td>MISSING</td></tr>"
    dup_rows = "".join(f"<tr><td>{esc(r['same_content'])}</td><td>{esc(r['script_path'])}</td><td>{esc(r['root_path'])}</td></tr>" for r in payload["duplicate_wrappers"][:100]) or "<tr><td>NONE</td><td>NONE</td><td>NONE</td></tr>"
    cleanup_rows = "".join(f"<tr><td>{esc(r['reason'])}</td><td>{esc(r['path'])}</td></tr>" for r in payload["cleanup_candidates"][:160]) or "<tr><td>NONE</td><td>NONE</td></tr>"
    crit_rows = "".join(f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td><td>{esc(c['blocker'])}</td></tr>" for c in payload["criteria"])
    git_text = "\n".join(payload["git_status"]) if payload["git_status"] else "CLEAN"

    page = f"""<!doctype html><html><head><meta charset='utf-8'><title>QRDS Workspace Portal Docs Inventory</title>
<style>body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}.card{{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}}.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px 8px 8px 0}}table{{border-collapse:collapse;width:100%;background:white;margin:14px 0}}th,td{{border:1px solid #d9deea;padding:8px;text-align:left;font-size:14px}}th{{background:#eef2ff}}pre{{background:#111827;color:#e5e7eb;padding:16px;border-radius:10px;overflow:auto}}.badge{{display:inline-block;background:#dbeafe;border-radius:999px;padding:6px 10px;font-weight:700}}</style></head><body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Workspace / Portal / Docs Inventory Map</h2>
<p>This artifact maps portal families, documentation surfaces, wrappers, generated artifacts, and cleanup candidates. It is an inventory and cannot unlock operational use.</p>
<div class='card'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p><p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>
<div class='kpi'><b>Portal indexes</b><br>{esc(payload['portal_index_count'])}</div><div class='kpi'><b>Docs files</b><br>{esc(payload['docs_file_count'])}</div><div class='kpi'><b>Root wrappers</b><br>{esc(payload['root_wrapper_count'])}</div><div class='kpi'><b>Script wrappers</b><br>{esc(payload['script_wrapper_count'])}</div><div class='kpi'><b>Duplicate wrappers</b><br>{esc(payload['duplicate_wrapper_count'])}</div><div class='kpi'><b>Cleanup candidates</b><br>{esc(payload['cleanup_candidate_count'])}</div><div class='kpi'><b>Git status lines</b><br>{esc(payload['git_status_count'])}</div><div class='kpi'><b>Mean score</b><br>{esc(payload['mean_inventory_score'])}</div>
<p class='badge'>Research-only guardrail active</p><p>No exchange account, no orders, no portfolio allocation output, no executable instruction, no live-fund workflow.</p></div>
<h2>Portal families</h2><table><thead><tr><th>family</th><th>count</th></tr></thead><tbody>{family_rows}</tbody></table>
<h2>Portal indexes</h2><table><thead><tr><th>family</th><th>path</th></tr></thead><tbody>{portal_rows}</tbody></table>
<h2>Documentation files</h2><table><thead><tr><th>family</th><th>path</th></tr></thead><tbody>{docs_rows}</tbody></table>
<h2>Duplicate wrappers</h2><table><thead><tr><th>same_content</th><th>script_path</th><th>root_path</th></tr></thead><tbody>{dup_rows}</tbody></table>
<h2>Cleanup candidates review list</h2><table><thead><tr><th>reason</th><th>path</th></tr></thead><tbody>{cleanup_rows}</tbody></table>
<h2>Criteria</h2><table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th><th>blocker</th></tr></thead><tbody>{crit_rows}</tbody></table>
<h2>Git status snapshot</h2><pre>{esc(git_text)}</pre>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"""
    _assert_research_only(page)
    return page


def build_workspace_portal_docs_inventory(output_dir: str | Path, repo_root: str | Path | None = None, max_items: int = 500) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    portal_indexes = _portal_indexes(root, max_items=max_items)
    artifact_dirs = _artifact_dirs(root)
    docs_files = _docs_inventory(root)
    root_wrappers = _root_wrappers(root)
    script_wrappers = _script_wrappers(root)
    duplicate_wrappers = _duplicate_wrappers(root)
    cleanup_candidates = _cleanup_candidates(root)
    git_status = _git_status(root)

    family_counts: dict[str, int] = {}
    for row in portal_indexes:
        family_counts[row["family"]] = family_counts.get(row["family"], 0) + 1

    has_general = family_counts.get("general_dashboard_portal", 0) > 0
    has_validation = family_counts.get("validation_gate_portal", 0) > 0
    has_docs = family_counts.get("documentation_book_portal", 0) > 0 or any(d.get("family") == "book_docs" for d in docs_files)

    criteria = [
        _criterion("portal_inventory_present", "PASS" if portal_indexes else "WARN", bool(portal_indexes), len(portal_indexes), ">= 1 portal index", "No portal index found." if not portal_indexes else ""),
        _criterion("general_portal_seen", "PASS" if has_general else "WARN", has_general, family_counts.get("general_dashboard_portal", 0), ">= 1 general dashboard/hub portal", "General portal not clearly identified." if not has_general else ""),
        _criterion("validation_portal_seen", "PASS" if has_validation else "WARN", has_validation, family_counts.get("validation_gate_portal", 0), ">= 1 validation/gate portal", "Validation portal not clearly identified." if not has_validation else ""),
        _criterion("documentation_portal_seen", "PASS" if has_docs else "WARN", has_docs, family_counts.get("documentation_book_portal", 0), ">= 1 docs/book portal or docs/book files", "Documentation portal not clearly identified." if not has_docs else ""),
        _criterion("docs_inventory_present", "PASS" if docs_files else "WARN", bool(docs_files), len(docs_files), ">= 1 docs file", "Docs files not found." if not docs_files else ""),
        _criterion("cleanup_review_available", "PASS", True, len(cleanup_candidates), "review list generated"),
        _criterion("git_snapshot_available", "PASS", True, len(git_status), "git status snapshot generated"),
        _criterion("research_only_lock", "PASS", True, "ACTIVE", "policy lock active"),
    ]

    ready_count = sum(1 for c in criteria if c["ready"])
    mean_score = round(ready_count / len(criteria), 4)

    if ready_count == len(criteria) and not cleanup_candidates and not duplicate_wrappers and not git_status:
        gate_answer = "WORKSPACE_PORTAL_DOCS_INVENTORY_READY_CLEAN_RESEARCH_ONLY"
    elif ready_count >= 6:
        gate_answer = "WORKSPACE_PORTAL_DOCS_INVENTORY_READY_CLEANUP_REVIEW_RESEARCH_ONLY"
    else:
        gate_answer = "WORKSPACE_PORTAL_DOCS_INVENTORY_INCOMPLETE_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.workspace_portal_docs_inventory.v1",
        "report_name": "qrds-workspace-portal-docs-inventory",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "repo_root": str(root),
        "portal_indexes": portal_indexes,
        "portal_index_count": len(portal_indexes),
        "portal_family_counts": family_counts,
        "artifact_dirs": artifact_dirs,
        "artifact_dir_count": len(artifact_dirs),
        "docs_files": docs_files,
        "docs_file_count": len(docs_files),
        "root_wrappers": root_wrappers,
        "root_wrapper_count": len(root_wrappers),
        "script_wrappers": script_wrappers,
        "script_wrapper_count": len(script_wrappers),
        "duplicate_wrappers": duplicate_wrappers,
        "duplicate_wrapper_count": len(duplicate_wrappers),
        "cleanup_candidates": cleanup_candidates,
        "cleanup_candidate_count": len(cleanup_candidates),
        "git_status": git_status,
        "git_status_count": len(git_status),
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_inventory_score": mean_score,
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    report_path = out / "workspace_portal_docs_inventory.json"
    md_path = out / "workspace_portal_docs_inventory.md"
    html_path = out / "index.html"
    index_path = out / "workspace_portal_docs_inventory_index.json"

    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    index = {
        "schema": "qrds.workspace_portal_docs_inventory_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "portal_index_count": payload["portal_index_count"],
        "docs_file_count": payload["docs_file_count"],
        "duplicate_wrapper_count": payload["duplicate_wrapper_count"],
        "cleanup_candidate_count": payload["cleanup_candidate_count"],
        "git_status_count": payload["git_status_count"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_inventory_score": payload["mean_inventory_score"],
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

    docs_dir = root / "crypto_decision_lab" / "docs" / "reports"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "WORKSPACE_PORTAL_DOCS_INVENTORY.md").write_text(
        "# QRDS/QOS Workspace / Portal / Docs Inventory Map\n\n"
        "Sprint 9P maps portal families, documentation surfaces, generated artifact directories, shell wrappers, duplicate wrappers, cleanup candidates, and git status.\n\n"
        "This is an inventory and review artifact. It does not delete files and cannot unlock operational use.\n\n"
        "Primary generated artifact: `crypto_decision_lab/artifacts/workspace_portal_docs_inventory/index.html`.\n",
        encoding="utf-8",
    )

    return index


build_inventory = build_workspace_portal_docs_inventory
