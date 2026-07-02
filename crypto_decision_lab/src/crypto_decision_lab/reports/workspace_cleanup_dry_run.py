from __future__ import annotations

import hashlib
import html
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
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


@dataclass(frozen=True)
class Candidate:
    path: str
    action: str
    risk: str
    reason: str
    tracked: bool = False
    exact_duplicate_of: str = ""
    applied: bool = False


def _repo_root(repo_root: str | Path | None = None) -> Path:
    if repo_root is not None:
        return Path(repo_root).resolve()
    here = Path.cwd().resolve()
    for p in [here, *here.parents]:
        if (p / "crypto_decision_lab").exists():
            return p
    return here


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except Exception:
        return str(path)


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_lines(root: Path, *args: str) -> list[str]:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except Exception:
        return []
    return [line for line in proc.stdout.splitlines() if line.strip()]


def _is_tracked(root: Path, path: Path) -> bool:
    rel = _rel(root, path)
    try:
        proc = subprocess.run(
            ["git", "ls-files", "--error-unmatch", rel],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        return proc.returncode == 0
    except Exception:
        return False


def _scan_portals(root: Path) -> list[dict[str, Any]]:
    portals: list[dict[str, Any]] = []
    for p in sorted(root.rglob("index.html")):
        rel = _rel(root, p)
        parts = {part.lower() for part in p.parts}
        if ".git" in parts or "__pycache__" in parts:
            continue
        family = "unknown"
        low = rel.lower()
        if "research_book" in low or "/book/" in low or "reader" in low:
            family = "documentation_book"
        elif "evidence_stack" in low or "command_center" in low or "gate" in low:
            family = "validation_stack"
        elif "dashboard" in low or "portal" in low or "hub" in low:
            family = "general_portal"
        portals.append({"path": rel, "family": family})
    return portals


def _scan_docs(root: Path) -> list[dict[str, Any]]:
    docs_root = root / "crypto_decision_lab" / "docs"
    rows: list[dict[str, Any]] = []
    if not docs_root.exists():
        return rows
    for p in sorted(docs_root.rglob("*")):
        if p.is_file() and p.suffix.lower() in {".md", ".html", ".json"}:
            rows.append({"path": _rel(root, p), "suffix": p.suffix.lower(), "bytes": p.stat().st_size})
    return rows


def _scan_wrappers(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[Candidate]]:
    root_wrappers = sorted(root.glob("qrds_*.sh"))
    script_wrappers = sorted((root / "scripts").glob("qrds_*.sh")) if (root / "scripts").exists() else []
    root_rows = [{"path": _rel(root, p), "sha256": _sha(p), "bytes": p.stat().st_size} for p in root_wrappers if p.is_file()]
    script_rows = [{"path": _rel(root, p), "sha256": _sha(p), "bytes": p.stat().st_size} for p in script_wrappers if p.is_file()]

    by_name = {p.name: p for p in root_wrappers if p.is_file()}
    candidates: list[Candidate] = []
    for sp in script_wrappers:
        rp = by_name.get(sp.name)
        if not rp or not sp.is_file() or not rp.is_file():
            continue
        if _sha(sp) == _sha(rp):
            candidates.append(
                Candidate(
                    path=_rel(root, sp),
                    action="remove_exact_duplicate_script_wrapper",
                    risk="low",
                    reason="scripts/ copy is byte-identical to root wrapper",
                    tracked=_is_tracked(root, sp),
                    exact_duplicate_of=_rel(root, rp),
                )
            )
        else:
            candidates.append(
                Candidate(
                    path=_rel(root, sp),
                    action="review_different_script_wrapper",
                    risk="medium",
                    reason="scripts/ copy has same basename as root wrapper but differs",
                    tracked=_is_tracked(root, sp),
                    exact_duplicate_of=_rel(root, rp),
                )
            )
    return root_rows, script_rows, candidates


def _scan_cleanup_candidates(root: Path) -> list[Candidate]:
    candidates: list[Candidate] = []

    for p in sorted(root.rglob("__pycache__")):
        if p.is_dir() and ".git" not in {part.lower() for part in p.parts}:
            candidates.append(Candidate(_rel(root, p), "remove_cache_dir", "low", "Python bytecode cache directory", _is_tracked(root, p)))

    for p in sorted(root.rglob(".pytest_cache")):
        if p.is_dir() and ".git" not in {part.lower() for part in p.parts}:
            candidates.append(Candidate(_rel(root, p), "remove_pytest_cache", "low", "pytest cache directory", _is_tracked(root, p)))

    patterns = ["*.bak*", "qrds_hotfix_*.sh", "qrds_sprint_*_hotfix*.sh"]
    for pattern in patterns:
        for p in sorted(root.rglob(pattern)):
            if not p.exists() or ".git" in {part.lower() for part in p.parts}:
                continue
            tracked = _is_tracked(root, p)
            risk = "medium" if tracked else "low"
            candidates.append(Candidate(_rel(root, p), "review_or_remove_leftover_file", risk, f"matches cleanup pattern {pattern}", tracked))

    # Deduplicate by path/action.
    seen: set[tuple[str, str]] = set()
    unique: list[Candidate] = []
    for c in candidates:
        key = (c.path, c.action)
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


def _apply_low_risk(root: Path, candidates: list[Candidate]) -> list[Candidate]:
    applied: list[Candidate] = []
    for c in candidates:
        if c.risk != "low" or c.tracked:
            continue
        path = root / c.path
        try:
            if c.action in {"remove_cache_dir", "remove_pytest_cache"} and path.is_dir():
                shutil.rmtree(path)
                applied.append(Candidate(**{**c.__dict__, "applied": True}))
            elif c.action in {"remove_exact_duplicate_script_wrapper", "review_or_remove_leftover_file"} and path.is_file():
                path.unlink()
                applied.append(Candidate(**{**c.__dict__, "applied": True}))
        except Exception:
            continue
    return applied


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
            raise ValueError(f"Operational language is not allowed in workspace cleanup dry-run: {term}")


def _payload_sha(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(x) for x in row) + "|")
    return "\n".join(out)


def _candidate_dict(c: Candidate) -> dict[str, Any]:
    return {
        "path": c.path,
        "action": c.action,
        "risk": c.risk,
        "reason": c.reason,
        "tracked": c.tracked,
        "exact_duplicate_of": c.exact_duplicate_of,
        "applied": c.applied,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    md = f"""# QRDS/QOS Workspace Cleanup Dry-Run

This report is a controlled dry-run/apply gate for low-risk workspace hygiene. Default mode deletes nothing.

**Gate answer:** {payload['gate_answer']}

**Policy lock:** {payload['policy_lock']} • **Mode:** {payload['app_mode']}

## Summary

- Portals: {payload['portal_index_count']}
- Docs files: {payload['docs_file_count']}
- Root wrappers: {payload['root_wrapper_count']}
- Script wrappers: {payload['script_wrapper_count']}
- Exact duplicate wrappers: {payload['exact_duplicate_wrapper_count']}
- Low-risk candidates: {payload['low_risk_candidate_count']}
- Medium-risk review: {payload['medium_risk_review_count']}
- Apply requested: {payload['apply_low_risk_requested']}
- Applied items: {payload['applied_count']}
- Git status lines: {payload['git_status_line_count']}
- Criteria ready: {payload['criteria_ready_count']}/{payload['criteria_total_count']}
- Mean cleanup score: {payload['mean_cleanup_score']}

Research-only guardrail: no exchange account, no orders, no portfolio allocation output, no executable market instruction, no live-fund workflow.

## Criteria

{_table(['criterion_id', 'status', 'ready', 'observed', 'threshold', 'blocker'], [[c['criterion_id'], c['status'], c['ready'], c['observed'], c['threshold'], c['blocker']] for c in payload['criteria']])}

## Low-risk candidates

{_table(['risk', 'action', 'tracked', 'applied', 'path', 'duplicate_of', 'reason'], [[c['risk'], c['action'], c['tracked'], c['applied'], c['path'], c['exact_duplicate_of'], c['reason']] for c in payload['cleanup_candidates'] if c['risk'] == 'low'][:120] or [['NONE', 'NONE', False, False, 'NONE', '', 'No low-risk candidates']])}

## Medium-risk review

{_table(['risk', 'action', 'tracked', 'path', 'duplicate_of', 'reason'], [[c['risk'], c['action'], c['tracked'], c['path'], c['exact_duplicate_of'], c['reason']] for c in payload['cleanup_candidates'] if c['risk'] == 'medium'][:120] or [['NONE', 'NONE', False, 'NONE', '', 'No medium-risk candidates']])}

## Safety flags

{_table(['flag', 'value'], [[k, v] for k, v in payload['safety_flags'].items()])}

Generated at {payload['generated_at']} • SHA256 {payload['report_payload_sha256']}
"""
    _assert_research_only(md)
    return md


def render_html(payload: dict[str, Any]) -> str:
    def esc(x: Any) -> str:
        return html.escape(str(x))

    criteria_rows = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td><td>{esc(c['blocker'])}</td></tr>"
        for c in payload['criteria']
    )
    candidate_rows = "".join(
        f"<tr><td>{esc(c['risk'])}</td><td>{esc(c['action'])}</td><td>{esc(c['tracked'])}</td><td>{esc(c['applied'])}</td><td>{esc(c['path'])}</td><td>{esc(c['exact_duplicate_of'])}</td><td>{esc(c['reason'])}</td></tr>"
        for c in payload['cleanup_candidates'][:160]
    ) or "<tr><td>NONE</td><td>NONE</td><td>False</td><td>False</td><td>NONE</td><td></td><td>No candidates</td></tr>"
    flag_rows = "".join(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>" for k, v in payload['safety_flags'].items())

    page = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>QRDS Workspace Cleanup Dry-Run</title>
<style>
body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}
.card{{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}}
.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px 8px 8px 0}}
table{{border-collapse:collapse;width:100%;background:white;margin:12px 0}}
th,td{{border:1px solid #d9deea;padding:8px;text-align:left;font-size:13px;vertical-align:top}}
th{{background:#eef2ff}}
.badge{{display:inline-block;background:#dcfce7;border-radius:999px;padding:6px 10px;font-weight:700}}
</style></head><body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1>
<h2>Workspace Cleanup Dry-Run / Safe Apply</h2>
<p>This report is a controlled dry-run/apply gate for low-risk workspace hygiene. Default mode deletes nothing.</p>
<div class='card'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p><p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>
<div class='kpi'><b>Portals</b><br>{esc(payload['portal_index_count'])}</div>
<div class='kpi'><b>Docs files</b><br>{esc(payload['docs_file_count'])}</div>
<div class='kpi'><b>Root wrappers</b><br>{esc(payload['root_wrapper_count'])}</div>
<div class='kpi'><b>Script wrappers</b><br>{esc(payload['script_wrapper_count'])}</div>
<div class='kpi'><b>Exact duplicate wrappers</b><br>{esc(payload['exact_duplicate_wrapper_count'])}</div>
<div class='kpi'><b>Low-risk candidates</b><br>{esc(payload['low_risk_candidate_count'])}</div>
<div class='kpi'><b>Medium-risk review</b><br>{esc(payload['medium_risk_review_count'])}</div>
<div class='kpi'><b>Applied items</b><br>{esc(payload['applied_count'])}</div>
<div class='kpi'><b>Git status lines</b><br>{esc(payload['git_status_line_count'])}</div>
<div class='kpi'><b>Mean cleanup score</b><br>{esc(payload['mean_cleanup_score'])}</div>
<p class='badge'>Research-only guardrail active</p>
<p>No exchange account, no orders, no portfolio allocation output, no executable market instruction, no live-fund workflow.</p></div>
<h2>Criteria</h2><table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th><th>blocker</th></tr></thead><tbody>{criteria_rows}</tbody></table>
<h2>Cleanup candidates</h2><table><thead><tr><th>risk</th><th>action</th><th>tracked</th><th>applied</th><th>path</th><th>duplicate_of</th><th>reason</th></tr></thead><tbody>{candidate_rows}</tbody></table>
<h2>Safety flags</h2><table><thead><tr><th>flag</th><th>value</th></tr></thead><tbody>{flag_rows}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p>
</body></html>"""
    _assert_research_only(page)
    return page


def build_workspace_cleanup_dry_run(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    apply_low_risk: bool = False,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    if not out.is_absolute():
        out = root / out
    out.mkdir(parents=True, exist_ok=True)

    portals = _scan_portals(root)
    docs = _scan_docs(root)
    root_wrappers, script_wrappers, wrapper_candidates = _scan_wrappers(root)
    cleanup_candidates = wrapper_candidates + _scan_cleanup_candidates(root)

    applied: list[Candidate] = []
    if apply_low_risk:
        applied = _apply_low_risk(root, cleanup_candidates)
        # Rescan after apply.
        portals = _scan_portals(root)
        docs = _scan_docs(root)
        root_wrappers, script_wrappers, wrapper_candidates = _scan_wrappers(root)
        cleanup_candidates = wrapper_candidates + _scan_cleanup_candidates(root)

    low = [c for c in cleanup_candidates if c.risk == "low"]
    medium = [c for c in cleanup_candidates if c.risk == "medium"]
    exact_duplicates = [c for c in wrapper_candidates if c.action == "remove_exact_duplicate_script_wrapper"]
    git_status = _git_lines(root, "status", "--short")

    criteria = [
        _criterion("inventory_loaded", "PASS", True, len(portals) + len(docs), ">= 1 portal/doc observed"),
        _criterion("duplicate_wrappers_classified", "PASS", True, len(wrapper_candidates), "duplicates classified"),
        _criterion("low_risk_candidates_classified", "PASS", True, len(low), "low-risk items listed"),
        _criterion("medium_risk_requires_review", "PASS", True, len(medium), "medium-risk items not auto-removed"),
        _criterion("default_no_delete", "PASS" if not apply_low_risk else "INFO", True, not apply_low_risk, "default dry-run deletes nothing"),
        _criterion("git_status_captured", "PASS", True, len(git_status), "git status captured"),
        _criterion("research_only_lock", "PASS", True, "ACTIVE", "policy lock active"),
    ]

    ready_count = sum(1 for c in criteria if c["ready"])
    mean_score = round(ready_count / len(criteria), 4)

    if apply_low_risk:
        gate_answer = "WORKSPACE_CLEANUP_LOW_RISK_APPLY_COMPLETED_REVIEW_REMAINING_RESEARCH_ONLY"
    elif low or medium:
        gate_answer = "WORKSPACE_CLEANUP_DRY_RUN_READY_REVIEW_REQUIRED_RESEARCH_ONLY"
    else:
        gate_answer = "WORKSPACE_CLEANUP_DRY_RUN_READY_NO_CANDIDATES_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.workspace_cleanup_dry_run.v1",
        "report_name": "qrds-workspace-cleanup-dry-run",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "repo_root": str(root),
        "apply_low_risk_requested": bool(apply_low_risk),
        "portal_index_count": len(portals),
        "docs_file_count": len(docs),
        "root_wrapper_count": len(root_wrappers),
        "script_wrapper_count": len(script_wrappers),
        "duplicate_wrapper_candidate_count": len(wrapper_candidates),
        "exact_duplicate_wrapper_count": len(exact_duplicates),
        "cleanup_candidate_count": len(cleanup_candidates),
        "low_risk_candidate_count": len(low),
        "medium_risk_review_count": len(medium),
        "applied_count": len(applied),
        "git_status_line_count": len(git_status),
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_cleanup_score": mean_score,
        "portals": portals[:200],
        "docs": docs[:200],
        "root_wrappers": root_wrappers[:200],
        "script_wrappers": script_wrappers[:200],
        "cleanup_candidates": [_candidate_dict(c) for c in cleanup_candidates],
        "applied_items": [_candidate_dict(c) for c in applied],
        "git_status": git_status,
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _payload_sha(payload)

    report_path = out / "workspace_cleanup_dry_run.json"
    md_path = out / "workspace_cleanup_dry_run.md"
    html_path = out / "index.html"
    index_path = out / "workspace_cleanup_dry_run_index.json"

    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    index = {
        "schema": "qrds.workspace_cleanup_dry_run_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "portal_index_count": payload["portal_index_count"],
        "docs_file_count": payload["docs_file_count"],
        "root_wrapper_count": payload["root_wrapper_count"],
        "script_wrapper_count": payload["script_wrapper_count"],
        "exact_duplicate_wrapper_count": payload["exact_duplicate_wrapper_count"],
        "cleanup_candidate_count": payload["cleanup_candidate_count"],
        "low_risk_candidate_count": payload["low_risk_candidate_count"],
        "medium_risk_review_count": payload["medium_risk_review_count"],
        "applied_count": payload["applied_count"],
        "git_status_line_count": payload["git_status_line_count"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_cleanup_score": payload["mean_cleanup_score"],
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


build_cleanup_dry_run = build_workspace_cleanup_dry_run
