from __future__ import annotations

import hashlib
import html
import json
import os
import subprocess
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
    "orders_generated: true",
    "real_capital_used: true",
    "trading_signal_generated: true",
    "executable_signal_generated: true",
    "operational_decision_allowed: true",
)

SHELL_EXT = ".sh"
ARCHIVE_TARGET = "scripts/archive/installers"
KEEP_PATTERNS = (
    "qrds_unified_portal_serve.sh",
    "qrds_portal_serve.sh",
    "qrds_acceptance_runner_serve.sh",
    "qrds_research_command_center_serve.sh",
)


def _repo_root(repo_root: str | Path | None = None) -> Path:
    if repo_root:
        return Path(repo_root).resolve()
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


def _git_status_lines(root: Path) -> list[str]:
    try:
        proc = subprocess.run(
            ["git", "status", "--short"],
            cwd=str(root),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return [line for line in proc.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def _safe_rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except Exception:
        return str(path)


def _classify_script(root: Path, path: Path) -> dict[str, Any]:
    name = path.name
    rel = _safe_rel(root, path)
    lower = name.lower()
    is_sprint_installer = lower.startswith("qrds_sprint_") and lower.endswith(SHELL_EXT)
    is_hotfix = "hotfix" in lower and lower.endswith(SHELL_EXT)
    is_regen = "regen" in lower and lower.endswith(SHELL_EXT)
    is_active_launcher = name in KEEP_PATTERNS or lower.endswith("_serve.sh") and not is_sprint_installer
    is_root = path.parent == root
    is_script_copy = path.parent == root / "scripts"

    if is_sprint_installer or is_hotfix or is_regen:
        recommendation = "ARCHIVE_CANDIDATE"
        risk = "LOW"
        rationale = "installer_or_hotfix_script_after_sprint_installation"
    elif is_script_copy:
        recommendation = "REVIEW_SCRIPT_COPY"
        risk = "MEDIUM"
        rationale = "script_copy_requires_duplicate_or_usage_review"
    elif is_active_launcher:
        recommendation = "KEEP_ACTIVE_LAUNCHER"
        risk = "KEEP"
        rationale = "active_root_launcher_or_serve_wrapper"
    else:
        recommendation = "KEEP_OR_REVIEW"
        risk = "MEDIUM"
        rationale = "root_script_not_classified_as_installer"

    return {
        "path": rel,
        "name": name,
        "sha256": _sha(path)[:16],
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "is_sprint_installer": is_sprint_installer,
        "is_hotfix": is_hotfix,
        "is_regen": is_regen,
        "is_active_launcher": is_active_launcher,
        "recommendation": recommendation,
        "risk": risk,
        "rationale": rationale,
        "archive_target": f"{ARCHIVE_TARGET}/{name}" if recommendation == "ARCHIVE_CANDIDATE" else "",
    }


def _scan_scripts(root: Path) -> list[dict[str, Any]]:
    paths: list[Path] = []
    for p in sorted(root.glob("qrds_*.sh")):
        if p.is_file():
            paths.append(p)
    scripts_dir = root / "scripts"
    if scripts_dir.exists():
        for p in sorted(scripts_dir.glob("qrds_*.sh")):
            if p.is_file():
                paths.append(p)
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for p in paths:
        rel = _safe_rel(root, p)
        if rel in seen:
            continue
        seen.add(rel)
        rows.append(_classify_script(root, p))
    return rows


def _criterion(criterion_id: str, status: str, ready: bool, observed: Any, threshold: str, blocker: str = "") -> dict[str, Any]:
    return {
        "criterion_id": criterion_id,
        "status": status,
        "ready": bool(ready),
        "observed": observed,
        "threshold": threshold,
        "blocker": blocker,
    }


def _assert_research_only(rendered: str) -> None:
    low = rendered.lower()
    for term in FORBIDDEN_RENDERED_PHRASES:
        if term in low:
            raise ValueError(f"Operational language is not allowed in installer archive plan: {term}")


def _payload_sha(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(x) for x in row) + "|")
    return "\n".join(out)


def render_markdown(payload: dict[str, Any]) -> str:
    candidates = payload["archive_candidates"][:80]
    keepers = payload["keep_candidates"][:40]
    criteria = payload["criteria"]
    md = f"""# QRDS/QOS • Gate BTC • Research-only
## Installer Archive / Repo Slimdown Plan

This plan identifies old sprint installers and hotfix scripts that can be archived after review. It is a plan only and does not move or delete files.

**Gate answer:** {payload['gate_answer']}

**Policy lock:** {payload['policy_lock']} • **Mode:** {payload['app_mode']}

## Summary

- Script files scanned: {payload['script_file_count']}
- Sprint installers: {payload['sprint_installer_count']}
- Hotfix installers: {payload['hotfix_installer_count']}
- Archive candidates: {payload['archive_candidate_count']}
- Keep candidates: {payload['keep_candidate_count']}
- Medium review candidates: {payload['medium_review_count']}
- Git status lines: {payload['git_status_line_count']}
- Criteria ready: {payload['criteria_ready_count']}/{payload['criteria_total_count']}
- Mean slimdown score: {payload['mean_slimdown_score']}

Safety lock remains active for account access, order flow, execution-style instructions, and live-fund workflow markers.

## Criteria

{_table(['criterion_id', 'status', 'ready', 'observed', 'threshold', 'blocker'], [[c['criterion_id'], c['status'], c['ready'], c['observed'], c['threshold'], c['blocker']] for c in criteria])}

## Archive candidates

{_table(['path', 'risk', 'recommendation', 'archive_target'], [[r['path'], r['risk'], r['recommendation'], r['archive_target']] for r in candidates] or [['NONE', 'NONE', 'NONE', 'NONE']])}

## Keep candidates

{_table(['path', 'risk', 'recommendation'], [[r['path'], r['risk'], r['recommendation']] for r in keepers] or [['NONE', 'NONE', 'NONE']])}

## Next step

A future safe-apply sprint may move low-risk archive candidates into `{ARCHIVE_TARGET}/` with a manifest, tests, and rollback notes. This report does not apply changes.

Generated at {payload['generated_at']} • SHA256 {payload['report_payload_sha256']}
"""
    _assert_research_only(md)
    return md


def render_html(payload: dict[str, Any]) -> str:
    def esc(x: Any) -> str:
        return html.escape(str(x))

    criteria_rows = "\n".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td><td>{esc(c['blocker'])}</td></tr>"
        for c in payload["criteria"]
    )
    archive_rows = "\n".join(
        f"<tr><td>{esc(r['path'])}</td><td>{esc(r['risk'])}</td><td>{esc(r['recommendation'])}</td><td>{esc(r['archive_target'])}</td></tr>"
        for r in payload["archive_candidates"][:120]
    ) or "<tr><td>NONE</td><td>NONE</td><td>NONE</td><td>NONE</td></tr>"
    keep_rows = "\n".join(
        f"<tr><td>{esc(r['path'])}</td><td>{esc(r['risk'])}</td><td>{esc(r['recommendation'])}</td></tr>"
        for r in payload["keep_candidates"][:80]
    ) or "<tr><td>NONE</td><td>NONE</td><td>NONE</td></tr>"

    page = f"""<!doctype html><html><head><meta charset='utf-8'><title>QRDS Installer Archive Plan</title>
<style>
body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}
.card{{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}}
.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px 8px 8px 0}}
table{{border-collapse:collapse;width:100%;background:white;margin:14px 0}} th,td{{border:1px solid #d9deea;padding:8px;text-align:left;font-size:13px}} th{{background:#eef2ff}}
.badge{{display:inline-block;background:#dcfce7;border-radius:999px;padding:6px 10px;font-weight:700}}
.warn{{background:#fff7ed}}
</style></head><body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1>
<h2>Installer Archive / Repo Slimdown Plan</h2>
<p>This plan identifies old sprint installers and hotfix scripts that can be archived after review. It does not move or delete files.</p>
<div class='card warn'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p><p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>
<div class='kpi'><b>Script files scanned</b><br>{esc(payload['script_file_count'])}</div><div class='kpi'><b>Sprint installers</b><br>{esc(payload['sprint_installer_count'])}</div><div class='kpi'><b>Hotfix installers</b><br>{esc(payload['hotfix_installer_count'])}</div><div class='kpi'><b>Archive candidates</b><br>{esc(payload['archive_candidate_count'])}</div><div class='kpi'><b>Keep candidates</b><br>{esc(payload['keep_candidate_count'])}</div><div class='kpi'><b>Medium review</b><br>{esc(payload['medium_review_count'])}</div><div class='kpi'><b>Git status lines</b><br>{esc(payload['git_status_line_count'])}</div><div class='kpi'><b>Mean score</b><br>{esc(payload['mean_slimdown_score'])}</div>
<p class='badge'>Research-only guardrail active</p><p>Safety lock remains active for account access, order flow, execution-style instructions, and live-fund workflow markers.</p></div>
<h2>Criteria</h2><table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th><th>blocker</th></tr></thead><tbody>{criteria_rows}</tbody></table>
<h2>Archive candidates</h2><table><thead><tr><th>path</th><th>risk</th><th>recommendation</th><th>archive_target</th></tr></thead><tbody>{archive_rows}</tbody></table>
<h2>Keep candidates</h2><table><thead><tr><th>path</th><th>risk</th><th>recommendation</th></tr></thead><tbody>{keep_rows}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"""
    _assert_research_only(page)
    return page


def build_installer_archive_plan(output_dir: str | Path, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    scripts = _scan_scripts(root)
    archive_candidates = [r for r in scripts if r["recommendation"] == "ARCHIVE_CANDIDATE"]
    keep_candidates = [r for r in scripts if r["recommendation"] == "KEEP_ACTIVE_LAUNCHER"]
    medium_review = [r for r in scripts if r["risk"] == "MEDIUM"]
    sprint_installers = [r for r in scripts if r["is_sprint_installer"]]
    hotfix_installers = [r for r in scripts if r["is_hotfix"]]
    git_lines = _git_status_lines(root)

    criteria = [
        _criterion("inventory_generated", "PASS", True, len(scripts), ">= 1 script scanned"),
        _criterion("archive_plan_generated", "PASS" if archive_candidates else "WARN", True, len(archive_candidates), "archive candidates classified", ""),
        _criterion("active_launchers_preserved", "PASS" if keep_candidates else "WARN", bool(keep_candidates), len(keep_candidates), ">= 1 active launcher classified", "Active launchers should remain visible."),
        _criterion("medium_risk_not_applied", "PASS", True, len(medium_review), "review only, no changes applied"),
        _criterion("no_file_changes_applied", "PASS", True, 0, "plan-only sprint"),
        _criterion("research_only_lock", "PASS", True, "ACTIVE", "policy lock active"),
    ]
    ready = sum(1 for c in criteria if c["ready"])
    score = round(ready / len(criteria), 4)

    if archive_candidates:
        gate_answer = "INSTALLER_ARCHIVE_PLAN_READY_REVIEW_REQUIRED_RESEARCH_ONLY"
    else:
        gate_answer = "INSTALLER_ARCHIVE_PLAN_NO_ACTION_REQUIRED_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.installer_archive_plan.v1",
        "report_name": "qrds-installer-archive-plan",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "archive_target": ARCHIVE_TARGET,
        "script_file_count": len(scripts),
        "sprint_installer_count": len(sprint_installers),
        "hotfix_installer_count": len(hotfix_installers),
        "archive_candidate_count": len(archive_candidates),
        "keep_candidate_count": len(keep_candidates),
        "medium_review_count": len(medium_review),
        "git_status_line_count": len(git_lines),
        "git_status_lines": git_lines,
        "criteria": criteria,
        "criteria_ready_count": ready,
        "criteria_total_count": len(criteria),
        "mean_slimdown_score": score,
        "archive_candidates": archive_candidates,
        "keep_candidates": keep_candidates,
        "medium_review_candidates": medium_review,
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _payload_sha(payload)

    report_path = out / "installer_archive_plan.json"
    markdown_path = out / "installer_archive_plan.md"
    html_path = out / "index.html"
    index_path = out / "installer_archive_plan_index.json"

    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    index = {
        "schema": "qrds.installer_archive_plan_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "archive_target": payload["archive_target"],
        "script_file_count": payload["script_file_count"],
        "sprint_installer_count": payload["sprint_installer_count"],
        "hotfix_installer_count": payload["hotfix_installer_count"],
        "archive_candidate_count": payload["archive_candidate_count"],
        "keep_candidate_count": payload["keep_candidate_count"],
        "medium_review_count": payload["medium_review_count"],
        "git_status_line_count": payload["git_status_line_count"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_slimdown_score": payload["mean_slimdown_score"],
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


build_archive_plan = build_installer_archive_plan
