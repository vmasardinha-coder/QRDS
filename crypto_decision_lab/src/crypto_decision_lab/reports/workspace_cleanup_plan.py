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
    "cleanup_actions_executed": False,
    "files_deleted": False,
}

GENERATED_ARTIFACT_DIRS = {
    ".pytest_cache",
    "__pycache__",
}

BACKUP_SUFFIXES = (
    ".bak",
    ".backup",
    ".orig",
    ".tmp",
    ".swp",
)

INSTALLER_PREFIXES = (
    "qrds_sprint_",
    "qrds_hotfix_",
)

KEEP_ROOT_WRAPPER_PREFIXES = (
    "qrds_",
)


@dataclass(frozen=True)
class FileRecord:
    path: str
    kind: str
    size_bytes: int
    sha256: str


def _repo_root() -> Path:
    here = Path.cwd().resolve()
    for p in [here, *here.parents]:
        if (p / "crypto_decision_lab").exists():
            return p
    return here


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return "UNREADABLE"


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except Exception:
        return str(path)


def _is_inside_any(path: Path, names: Iterable[str]) -> bool:
    lowered = {part.lower() for part in path.parts}
    return any(name.lower() in lowered for name in names)


def _file_record(root: Path, path: Path, kind: str) -> FileRecord:
    return FileRecord(
        path=_rel(root, path),
        kind=kind,
        size_bytes=path.stat().st_size if path.exists() else 0,
        sha256=_sha(path)[:16],
    )


def _find_root_wrappers(root: Path) -> list[FileRecord]:
    rows: list[FileRecord] = []
    for path in sorted(root.glob("*.sh")):
        if path.is_file() and path.name.startswith(KEEP_ROOT_WRAPPER_PREFIXES):
            rows.append(_file_record(root, path, "root_wrapper"))
    return rows


def _find_script_wrappers(root: Path) -> list[FileRecord]:
    rows: list[FileRecord] = []
    scripts_dir = root / "scripts"
    if not scripts_dir.exists():
        return rows
    for path in sorted(scripts_dir.glob("*.sh")):
        if path.is_file():
            rows.append(_file_record(root, path, "script_wrapper"))
    return rows


def _find_portal_indexes(root: Path) -> list[FileRecord]:
    rows: list[FileRecord] = []
    roots = [root / "artifacts", root / "crypto_decision_lab" / "artifacts"]
    for base in roots:
        if not base.exists():
            continue
        for path in sorted(base.rglob("index.html")):
            if path.is_file():
                rows.append(_file_record(root, path, "portal_index"))
    return rows


def _find_docs(root: Path) -> list[FileRecord]:
    docs_root = root / "crypto_decision_lab" / "docs"
    rows: list[FileRecord] = []
    if not docs_root.exists():
        return rows
    for path in sorted(docs_root.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".md", ".html", ".json"}:
            rows.append(_file_record(root, path, "doc_surface"))
    return rows


def _duplicate_wrapper_plan(root: Path, root_wrappers: list[FileRecord], script_wrappers: list[FileRecord]) -> list[dict[str, Any]]:
    root_by_name = {Path(r.path).name: r for r in root_wrappers}
    plan: list[dict[str, Any]] = []
    for sr in script_wrappers:
        name = Path(sr.path).name
        rr = root_by_name.get(name)
        if not rr:
            continue
        same = rr.sha256 == sr.sha256 and rr.sha256 != "UNREADABLE"
        plan.append(
            {
                "category": "duplicate_wrapper",
                "root_path": rr.path,
                "script_path": sr.path,
                "same_content": same,
                "recommended_action": "remove_script_copy_after_review" if same else "manual_review_different_content",
                "risk_level": "low" if same else "medium",
                "reason": "Root wrapper and scripts wrapper share the same basename.",
            }
        )
    return plan


def _cleanup_candidate_plan(root: Path) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []

    # Safe generated caches. This is a plan only; no deletion is performed.
    for cache_name in GENERATED_ARTIFACT_DIRS:
        for path in sorted(root.rglob(cache_name)):
            if path.exists():
                plan.append(
                    {
                        "category": "generated_cache",
                        "path": _rel(root, path),
                        "recommended_action": "remove_generated_cache_after_review",
                        "risk_level": "low",
                        "reason": "Generated cache directory; can be recreated by tests or Python runtime.",
                    }
                )

    # Backup and temporary files.
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = _rel(root, path)
        lname = path.name.lower()
        if any(lname.endswith(suffix) for suffix in BACKUP_SUFFIXES) or ".bak_" in lname:
            plan.append(
                {
                    "category": "backup_or_temp_file",
                    "path": rel,
                    "recommended_action": "remove_backup_after_review",
                    "risk_level": "low",
                    "reason": "Backup/temp artifact left by previous patching flow.",
                }
            )
        elif path.parent == root and lname.endswith(".sh") and lname.startswith(INSTALLER_PREFIXES):
            plan.append(
                {
                    "category": "local_installer_or_hotfix",
                    "path": rel,
                    "recommended_action": "keep_out_of_repo_or_archive_outside_main_tree",
                    "risk_level": "low",
                    "reason": "Local sprint/hotfix installer is useful for transfer but should not accumulate in the repo root.",
                }
            )
    return plan


def _git_status(root: Path) -> list[str]:
    try:
        import subprocess

        proc = subprocess.run(["git", "status", "--short"], cwd=root, text=True, capture_output=True, check=False)
        return [line for line in proc.stdout.splitlines() if line.strip()]
    except Exception as exc:
        return [f"UNAVAILABLE: {exc}"]


def _criterion(criterion_id: str, status: str, ready: bool, observed: Any, threshold: str, blocker: str = "") -> dict[str, Any]:
    return {
        "criterion_id": criterion_id,
        "status": status,
        "ready": bool(ready),
        "observed": observed,
        "threshold": threshold,
        "blocker": blocker,
    }


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(x) for x in row) + "|")
    return "\n".join(out)


def _payload_sha(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _assert_research_only(rendered: str) -> None:
    low = rendered.lower()
    forbidden = (
        "api key required: true",
        "orders_allowed: true",
        "orders_generated: true",
        "real_capital_used: true",
        "recommendation_generated: true",
        "allocation_generated: true",
    )
    for term in forbidden:
        if term in low:
            raise ValueError(f"Unsafe cleanup plan rendering: {term}")


def render_markdown(payload: dict[str, Any]) -> str:
    duplicate_rows = [
        [p["risk_level"], p["recommended_action"], p["root_path"], p["script_path"], p["same_content"]]
        for p in payload["duplicate_wrapper_plan"][:80]
    ]
    cleanup_rows = [
        [p["risk_level"], p["category"], p["recommended_action"], p["path"], p["reason"]]
        for p in payload["cleanup_candidate_plan"][:120]
    ]
    criteria_rows = [[c["criterion_id"], c["status"], c["ready"], c["observed"], c["threshold"], c["blocker"]] for c in payload["criteria"]]
    flag_rows = [[k, v] for k, v in payload["safety_flags"].items()]
    portal_rows = [[r["path"], r["size_bytes"], r["sha256"]] for r in payload["portal_indexes"][:80]]
    doc_rows = [[r["path"], r["size_bytes"], r["sha256"]] for r in payload["doc_surfaces"][:80]]

    md = f"""# QRDS/QOS • Gate BTC • Research-only
## Controlled Workspace Cleanup Plan

This artifact converts the workspace/portal/docs inventory into a reviewed cleanup plan. It is a plan only: no files are deleted by this report.

**Gate answer:** {payload['gate_answer']}

**Policy lock:** {payload['policy_lock']} • **Mode:** {payload['app_mode']}

## Summary

- Portal indexes: {payload['portal_index_count']}
- Docs files: {payload['doc_surface_count']}
- Root wrappers: {payload['root_wrapper_count']}
- Script wrappers: {payload['script_wrapper_count']}
- Duplicate wrapper plan items: {payload['duplicate_wrapper_count']}
- Cleanup candidate plan items: {payload['cleanup_candidate_count']}
- Low-risk cleanup candidates: {payload['low_risk_cleanup_count']}
- Medium-risk review candidates: {payload['medium_risk_cleanup_count']}
- Git status lines: {payload['git_status_line_count']}
- Criteria ready: {payload['criteria_ready_count']}/{payload['criteria_total_count']}
- Mean cleanup score: {payload['mean_cleanup_score']}

Research-only guardrail: no exchange account, no orders, no portfolio allocation output, no executable instruction, no live-fund workflow.

## Criteria

{_table(['criterion_id', 'status', 'ready', 'observed', 'threshold', 'blocker'], criteria_rows)}

## Duplicate wrapper review plan

{_table(['risk', 'recommended_action', 'root_path', 'script_path', 'same_content'], duplicate_rows or [['NONE', 'NONE', 'NONE', 'NONE', 'NONE']])}

## Cleanup candidate review plan

{_table(['risk', 'category', 'recommended_action', 'path', 'reason'], cleanup_rows or [['NONE', 'NONE', 'NONE', 'NONE', 'NONE']])}

## Portal indexes sampled

{_table(['path', 'size_bytes', 'sha256'], portal_rows or [['NONE', 0, 'NONE']])}

## Documentation surfaces sampled

{_table(['path', 'size_bytes', 'sha256'], doc_rows or [['NONE', 0, 'NONE']])}

## Safety flags

{_table(['flag', 'value'], flag_rows)}

Generated at {payload['generated_at']} • SHA256 {payload['report_payload_sha256']}
"""
    _assert_research_only(md)
    return md


def render_html(payload: dict[str, Any]) -> str:
    def esc(x: Any) -> str:
        return html.escape(str(x))

    def rows(items: list[dict[str, Any]], fields: list[str]) -> str:
        return "\n".join("<tr>" + "".join(f"<td>{esc(item.get(field, ''))}</td>" for field in fields) + "</tr>" for item in items)

    criteria_rows = rows(payload["criteria"], ["criterion_id", "status", "ready", "observed", "threshold", "blocker"])
    dup_rows = rows(payload["duplicate_wrapper_plan"][:100], ["risk_level", "recommended_action", "root_path", "script_path", "same_content"]) or "<tr><td>NONE</td><td>NONE</td><td>NONE</td><td>NONE</td><td>NONE</td></tr>"
    cleanup_rows = rows(payload["cleanup_candidate_plan"][:140], ["risk_level", "category", "recommended_action", "path", "reason"]) or "<tr><td>NONE</td><td>NONE</td><td>NONE</td><td>NONE</td><td>NONE</td></tr>"
    flags = "\n".join(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>" for k, v in payload["safety_flags"].items())

    page = f"""<!doctype html><html><head><meta charset='utf-8'><title>QRDS Controlled Cleanup Plan</title>
<style>
body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}
.card{{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}}
.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px 8px 8px 0}}
table{{border-collapse:collapse;width:100%;background:white;margin:14px 0}}
th,td{{border:1px solid #d9deea;padding:8px;text-align:left;font-size:13px;vertical-align:top}}
th{{background:#eef2ff}}
.warn{{background:#fff7ed}}
.badge{{display:inline-block;background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}}
</style></head><body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1>
<h2>Controlled Workspace Cleanup Plan</h2>
<p>This artifact converts the workspace/portal/docs inventory into a reviewed cleanup plan. It is a plan only: no files are deleted by this report.</p>
<div class='card warn'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p><p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>
<div class='kpi'><b>Portal indexes</b><br>{esc(payload['portal_index_count'])}</div>
<div class='kpi'><b>Docs files</b><br>{esc(payload['doc_surface_count'])}</div>
<div class='kpi'><b>Root wrappers</b><br>{esc(payload['root_wrapper_count'])}</div>
<div class='kpi'><b>Script wrappers</b><br>{esc(payload['script_wrapper_count'])}</div>
<div class='kpi'><b>Duplicate wrapper plan</b><br>{esc(payload['duplicate_wrapper_count'])}</div>
<div class='kpi'><b>Cleanup candidates</b><br>{esc(payload['cleanup_candidate_count'])}</div>
<div class='kpi'><b>Git status lines</b><br>{esc(payload['git_status_line_count'])}</div>
<div class='kpi'><b>Mean cleanup score</b><br>{esc(payload['mean_cleanup_score'])}</div>
<p class='badge'>Research-only guardrail active</p><p>No exchange account, no orders, no portfolio allocation output, no executable instruction, no live-fund workflow.</p></div>
<h2>Criteria</h2><table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th><th>blocker</th></tr></thead><tbody>{criteria_rows}</tbody></table>
<h2>Duplicate wrapper review plan</h2><table><thead><tr><th>risk</th><th>recommended_action</th><th>root_path</th><th>script_path</th><th>same_content</th></tr></thead><tbody>{dup_rows}</tbody></table>
<h2>Cleanup candidate review plan</h2><table><thead><tr><th>risk</th><th>category</th><th>recommended_action</th><th>path</th><th>reason</th></tr></thead><tbody>{cleanup_rows}</tbody></table>
<h2>Safety flags</h2><table><thead><tr><th>flag</th><th>value</th></tr></thead><tbody>{flags}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"""
    _assert_research_only(page)
    return page


def build_workspace_cleanup_plan(output_dir: str | Path = "artifacts/workspace_cleanup_plan") -> dict[str, Any]:
    root = _repo_root()
    out = Path(output_dir)
    if not out.is_absolute():
        out = root / "crypto_decision_lab" / out if not str(out).startswith("crypto_decision_lab") else root / out
    out.mkdir(parents=True, exist_ok=True)

    root_wrappers = _find_root_wrappers(root)
    script_wrappers = _find_script_wrappers(root)
    portals = _find_portal_indexes(root)
    docs = _find_docs(root)
    duplicate_plan = _duplicate_wrapper_plan(root, root_wrappers, script_wrappers)
    cleanup_plan = _cleanup_candidate_plan(root)
    git_status = _git_status(root)

    low_risk = sum(1 for p in [*duplicate_plan, *cleanup_plan] if p.get("risk_level") == "low")
    medium_risk = sum(1 for p in [*duplicate_plan, *cleanup_plan] if p.get("risk_level") == "medium")
    high_risk = sum(1 for p in [*duplicate_plan, *cleanup_plan] if p.get("risk_level") == "high")

    criteria = [
        _criterion("inventory_present", "PASS" if portals or docs or root_wrappers else "WARN", bool(portals or docs or root_wrappers), len(portals) + len(docs) + len(root_wrappers), "> 0 mapped surfaces", ""),
        _criterion("duplicate_wrappers_mapped", "PASS", True, len(duplicate_plan), "all duplicate basenames classified", ""),
        _criterion("cleanup_candidates_mapped", "PASS", True, len(cleanup_plan), "candidate plan generated", ""),
        _criterion("no_cleanup_executed", "PASS", True, False, "report must not delete files", ""),
        _criterion("git_status_clean_at_start", "PASS" if not git_status else "WARN", not bool(git_status), len(git_status), "0 preferred", "Workspace has pending changes; review before cleanup." if git_status else ""),
        _criterion("documentation_surface_present", "PASS" if docs else "WARN", bool(docs), len(docs), "> 0 docs", "Documentation surfaces not found." if not docs else ""),
        _criterion("research_only_lock", "PASS", True, "ACTIVE", "policy lock active", ""),
    ]
    ready_count = sum(1 for c in criteria if c["ready"])
    mean_score = round(ready_count / len(criteria), 4)

    if high_risk:
        gate_answer = "WORKSPACE_CLEANUP_PLAN_REVIEW_REQUIRED_HIGH_RISK_ITEMS_RESEARCH_ONLY"
    elif duplicate_plan or cleanup_plan:
        gate_answer = "WORKSPACE_CLEANUP_PLAN_READY_REVIEW_REQUIRED_RESEARCH_ONLY"
    else:
        gate_answer = "WORKSPACE_CLEANUP_PLAN_READY_NO_CLEANUP_NEEDED_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.workspace_cleanup_plan.v1",
        "report_name": "qrds-workspace-cleanup-plan",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "portal_indexes": [r.__dict__ for r in portals],
        "doc_surfaces": [r.__dict__ for r in docs],
        "root_wrappers": [r.__dict__ for r in root_wrappers],
        "script_wrappers": [r.__dict__ for r in script_wrappers],
        "duplicate_wrapper_plan": duplicate_plan,
        "cleanup_candidate_plan": cleanup_plan,
        "git_status": git_status,
        "portal_index_count": len(portals),
        "doc_surface_count": len(docs),
        "root_wrapper_count": len(root_wrappers),
        "script_wrapper_count": len(script_wrappers),
        "duplicate_wrapper_count": len(duplicate_plan),
        "cleanup_candidate_count": len(cleanup_plan),
        "low_risk_cleanup_count": low_risk,
        "medium_risk_cleanup_count": medium_risk,
        "high_risk_cleanup_count": high_risk,
        "git_status_line_count": len(git_status),
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_cleanup_score": mean_score,
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _payload_sha(payload)

    report_path = out / "workspace_cleanup_plan.json"
    markdown_path = out / "workspace_cleanup_plan.md"
    html_path = out / "index.html"
    index_path = out / "workspace_cleanup_plan_index.json"

    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    index = {
        "schema": "qrds.workspace_cleanup_plan_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "portal_index_count": payload["portal_index_count"],
        "doc_surface_count": payload["doc_surface_count"],
        "root_wrapper_count": payload["root_wrapper_count"],
        "script_wrapper_count": payload["script_wrapper_count"],
        "duplicate_wrapper_count": payload["duplicate_wrapper_count"],
        "cleanup_candidate_count": payload["cleanup_candidate_count"],
        "low_risk_cleanup_count": payload["low_risk_cleanup_count"],
        "medium_risk_cleanup_count": payload["medium_risk_cleanup_count"],
        "high_risk_cleanup_count": payload["high_risk_cleanup_count"],
        "git_status_line_count": payload["git_status_line_count"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_cleanup_score": payload["mean_cleanup_score"],
        "report_path": str(report_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "index_path": str(index_path),
        "serve_entrypoint": str(html_path),
        "report_payload_sha256": payload["report_payload_sha256"],
        "payload": payload,
        **SAFETY_FLAGS,
    }
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    return index


build_cleanup_plan = build_workspace_cleanup_plan
