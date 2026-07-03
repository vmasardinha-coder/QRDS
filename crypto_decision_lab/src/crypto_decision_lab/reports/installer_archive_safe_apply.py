from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shutil
import subprocess
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
    "orders_generated: true",
    "real_capital_used: true",
    "trading_signal_generated: true",
    "executable_signal_generated: true",
    "operational_decision_allowed: true",
)

SPRINT_ARCHIVE_RE = re.compile(r"^qrds_sprint_(?:8[A-Z]|9[A-V])(?:_.*)?\.sh$")
HOTFIX_ARCHIVE_RE = re.compile(r"^qrds_.*hotfix.*\.sh$", re.IGNORECASE)
CURRENT_EXCLUDE_RE = re.compile(r"^qrds_sprint_9W_.*\.sh$")


def _repo_root(repo_root: str | Path | None = None) -> Path:
    if repo_root:
        return Path(repo_root).resolve()
    here = Path.cwd().resolve()
    for p in [here, *here.parents]:
        if (p / "crypto_decision_lab" / "src" / "crypto_decision_lab").exists():
            return p
    return here


def _git_status_lines(root: Path) -> list[str]:
    try:
        out = subprocess.check_output(["git", "status", "--short"], cwd=root, text=True)
    except Exception:
        return []
    return [line for line in out.splitlines() if line.strip()]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _tracked(root: Path, rel: str) -> bool:
    try:
        proc = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=root, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return proc.returncode == 0
    except Exception:
        return False


def _archive_dest(root: Path, path: Path) -> Path:
    archive = root / "scripts" / "archive" / "installers"
    archive.mkdir(parents=True, exist_ok=True)
    dest = archive / path.name
    if not dest.exists():
        return dest
    stem = path.stem
    suffix = path.suffix
    digest = _sha256(path)[:8]
    return archive / f"{stem}_{digest}{suffix}"


def _is_archive_candidate(path: Path) -> bool:
    name = path.name
    if CURRENT_EXCLUDE_RE.match(name):
        return False
    if name in {
        "qrds_installer_archive_safe_apply.sh",
        "qrds_installer_archive_safe_apply_serve.sh",
        "qrds_unified_portal_serve.sh",
    }:
        return False
    return bool(SPRINT_ARCHIVE_RE.match(name) or HOTFIX_ARCHIVE_RE.match(name))


def _scan_candidates(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.sh")):
        if not path.is_file():
            continue
        if _is_archive_candidate(path):
            rel = path.relative_to(root).as_posix()
            kind = "sprint_installer" if SPRINT_ARCHIVE_RE.match(path.name) else "hotfix_installer"
            rows.append({
                "path": rel,
                "kind": kind,
                "tracked": _tracked(root, rel),
                "sha256": _sha256(path),
                "size_bytes": path.stat().st_size,
                "destination": _archive_dest(root, path).relative_to(root).as_posix(),
                "risk": "LOW",
                "recommended_action": "archive_move",
            })
    return rows


def _apply_archive(root: Path, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    applied: list[dict[str, Any]] = []
    for row in candidates:
        src = root / row["path"]
        dest = root / row["destination"]
        if not src.exists() or not src.is_file():
            row2 = dict(row)
            row2["applied_status"] = "SKIPPED_MISSING_SOURCE"
            applied.append(row2)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        row2 = dict(row)
        row2["applied_status"] = "MOVED_TO_ARCHIVE"
        row2["destination_sha256"] = _sha256(dest)
        applied.append(row2)
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


def _assert_research_only(text: str) -> None:
    low = text.lower()
    for term in FORBIDDEN_RENDERED_PHRASES:
        if term in low:
            raise ValueError(f"Operational language is not allowed in installer archive safe apply: {term}")


def _payload_sha(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(x) for x in row) + "|")
    return "\n".join(out)


def render_markdown(payload: dict[str, Any]) -> str:
    moved_rows = [[r.get("path"), r.get("destination"), r.get("kind"), r.get("applied_status", "DRY_RUN")] for r in payload["applied_items"][:120]]
    candidate_rows = [[r.get("path"), r.get("destination"), r.get("kind"), r.get("risk")] for r in payload["archive_candidates"][:120]]
    criteria_rows = [[c["criterion_id"], c["status"], c["ready"], c["observed"], c["threshold"], c["blocker"]] for c in payload["criteria"]]
    flag_rows = [[k, v] for k, v in payload["safety_flags"].items()]
    md = f"""# QRDS/QOS • Gate BTC • Research-only
## Installer Archive / Repo Slimdown Safe Apply

This report applies reviewed low-risk installer archive moves. It does not touch live launcher wrappers, report modules, docs, datasets, or medium-review items.

**Gate answer:** {payload['gate_answer']}

**Policy lock:** {payload['policy_lock']} • **Mode:** {payload['app_mode']}

## Summary

- Apply mode: {payload['apply_mode']}
- Script files scanned: {payload['script_files_scanned']}
- Archive candidates before: {payload['archive_candidates_before']}
- Applied items: {payload['applied_item_count']}
- Skipped items: {payload['skipped_item_count']}
- Remaining archive candidates: {payload['remaining_archive_candidates']}
- Git status lines before: {payload['git_status_lines_before']}
- Git status lines after: {payload['git_status_lines_after']}
- Criteria ready: {payload['criteria_ready_count']}/{payload['criteria_total_count']}
- Mean archive score: {payload['mean_archive_score']}

Safety lock remains active for account access, order flow, execution-style instructions, and live-fund workflow markers.

## Criteria

{_table(['criterion_id', 'status', 'ready', 'observed', 'threshold', 'blocker'], criteria_rows)}

## Applied items

{_table(['source', 'destination', 'kind', 'status'], moved_rows or [['NONE', 'NONE', 'NONE', 'NO_ITEMS_APPLIED']])}

## Archive candidates

{_table(['source', 'destination', 'kind', 'risk'], candidate_rows or [['NONE', 'NONE', 'NONE', 'NO_CANDIDATES']])}

## Safety flags

{_table(['flag', 'value'], flag_rows)}

Generated at {payload['generated_at']} • SHA256 {payload['report_payload_sha256']}
"""
    _assert_research_only(md)
    return md


def render_html(payload: dict[str, Any]) -> str:
    esc = lambda x: html.escape(str(x))
    criteria_rows = "\n".join(f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td><td>{esc(c['blocker'])}</td></tr>" for c in payload["criteria"])
    applied_rows = "\n".join(f"<tr><td>{esc(r.get('path'))}</td><td>{esc(r.get('destination'))}</td><td>{esc(r.get('kind'))}</td><td>{esc(r.get('applied_status','DRY_RUN'))}</td></tr>" for r in payload["applied_items"][:160]) or "<tr><td>NONE</td><td>NONE</td><td>NONE</td><td>NO_ITEMS_APPLIED</td></tr>"
    candidate_rows = "\n".join(f"<tr><td>{esc(r.get('path'))}</td><td>{esc(r.get('destination'))}</td><td>{esc(r.get('kind'))}</td><td>{esc(r.get('risk'))}</td></tr>" for r in payload["archive_candidates"][:160]) or "<tr><td>NONE</td><td>NONE</td><td>NONE</td><td>NO_CANDIDATES</td></tr>"
    flag_rows = "\n".join(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>" for k, v in payload["safety_flags"].items())
    page = f"""<!doctype html><html><head><meta charset='utf-8'><title>QRDS Installer Archive Safe Apply</title>
<style>body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}.card{{background:#fff;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}}.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px 8px 8px 0}}table{{border-collapse:collapse;width:100%;background:#fff;margin:16px 0}}th,td{{border:1px solid #d9deea;padding:8px;text-align:left;font-size:14px}}th{{background:#eef2ff}}.warn{{border-left:6px solid #f59e0b}}</style></head><body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Installer Archive / Repo Slimdown Safe Apply</h2>
<p>This report applies reviewed low-risk installer archive moves. It does not touch live launcher wrappers, report modules, docs, datasets, or medium-review items.</p>
<div class='card warn'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p><p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>
<div class='kpi'><b>Apply mode</b><br>{esc(payload['apply_mode'])}</div><div class='kpi'><b>Scanned</b><br>{esc(payload['script_files_scanned'])}</div><div class='kpi'><b>Candidates before</b><br>{esc(payload['archive_candidates_before'])}</div><div class='kpi'><b>Applied</b><br>{esc(payload['applied_item_count'])}</div><div class='kpi'><b>Skipped</b><br>{esc(payload['skipped_item_count'])}</div><div class='kpi'><b>Remaining</b><br>{esc(payload['remaining_archive_candidates'])}</div><div class='kpi'><b>Git before/after</b><br>{esc(payload['git_status_lines_before'])}/{esc(payload['git_status_lines_after'])}</div><div class='kpi'><b>Mean score</b><br>{esc(payload['mean_archive_score'])}</div>
<p>Safety lock remains active for account access, order flow, execution-style instructions, and live-fund workflow markers.</p></div>
<h2>Criteria</h2><table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th><th>blocker</th></tr></thead><tbody>{criteria_rows}</tbody></table>
<h2>Applied items</h2><table><thead><tr><th>source</th><th>destination</th><th>kind</th><th>status</th></tr></thead><tbody>{applied_rows}</tbody></table>
<h2>Archive candidates</h2><table><thead><tr><th>source</th><th>destination</th><th>kind</th><th>risk</th></tr></thead><tbody>{candidate_rows}</tbody></table>
<h2>Safety flags</h2><table><thead><tr><th>flag</th><th>value</th></tr></thead><tbody>{flag_rows}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"""
    _assert_research_only(page)
    return page


def build_installer_archive_safe_apply(output_dir: str | Path, repo_root: str | Path | None = None, apply: bool = True, **_: Any) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    before_status = _git_status_lines(root)
    before_candidates = _scan_candidates(root)
    applied_items: list[dict[str, Any]] = []
    if apply:
        applied_items = _apply_archive(root, before_candidates)
    after_candidates = _scan_candidates(root)
    after_status = _git_status_lines(root)

    skipped = [r for r in applied_items if str(r.get("applied_status", "")).startswith("SKIPPED")]
    criteria = [
        _criterion("policy_lock", "PASS", True, "ACTIVE", "must remain active"),
        _criterion("safe_scope", "PASS", True, "root sprint/hotfix installers only", "must not touch live wrappers/modules/docs/data"),
        _criterion("apply_mode_explicit", "PASS" if apply else "WARN", bool(apply), apply, "safe apply expected for 9W", "Dry-run mode did not apply archive moves." if not apply else ""),
        _criterion("items_applied_or_noop", "PASS" if applied_items or not before_candidates else "WARN", bool(applied_items or not before_candidates), len(applied_items), ">=1 applied or no-op justified", "Candidates exist but were not applied." if before_candidates and not applied_items else ""),
        _criterion("skipped_zero", "PASS" if not skipped else "WARN", not skipped, len(skipped), "0 skipped preferred", "Some files were skipped." if skipped else ""),
        _criterion("remaining_reduced", "PASS" if len(after_candidates) <= len(before_candidates) else "FAIL", len(after_candidates) <= len(before_candidates), f"{len(before_candidates)}->{len(after_candidates)}", "remaining <= before"),
        _criterion("research_only_flags", "PASS", True, "all false for operational flags", "must stay false"),
    ]
    ready = sum(1 for c in criteria if c["ready"])
    score = round(ready / len(criteria), 4)

    if apply and applied_items and not skipped:
        gate_answer = "INSTALLER_ARCHIVE_SAFE_APPLY_LOW_RISK_MOVED_RESEARCH_ONLY"
    elif apply and not before_candidates:
        gate_answer = "INSTALLER_ARCHIVE_SAFE_APPLY_NOOP_ALREADY_CLEAN_RESEARCH_ONLY"
    elif not apply:
        gate_answer = "INSTALLER_ARCHIVE_SAFE_APPLY_DRY_RUN_ONLY_RESEARCH_ONLY"
    else:
        gate_answer = "INSTALLER_ARCHIVE_SAFE_APPLY_REVIEW_REQUIRED_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.installer_archive_safe_apply.v1",
        "report_name": "qrds-installer-archive-safe-apply",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "apply_mode": "SAFE_APPLY" if apply else "DRY_RUN",
        "script_files_scanned": len(list(root.glob("*.sh"))) + len(list((root / "scripts").glob("*.sh"))) if (root / "scripts").exists() else len(list(root.glob("*.sh"))),
        "archive_candidates_before": len(before_candidates),
        "archive_candidates_after": len(after_candidates),
        "remaining_archive_candidates": len(after_candidates),
        "applied_item_count": len(applied_items),
        "skipped_item_count": len(skipped),
        "git_status_lines_before": len(before_status),
        "git_status_lines_after": len(after_status),
        "archive_candidates": before_candidates,
        "applied_items": applied_items,
        "remaining_candidates": after_candidates,
        "git_status_before": before_status,
        "git_status_after": after_status,
        "criteria": criteria,
        "criteria_ready_count": ready,
        "criteria_total_count": len(criteria),
        "mean_archive_score": score,
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _payload_sha(payload)

    report_path = out / "installer_archive_safe_apply.json"
    md_path = out / "installer_archive_safe_apply.md"
    html_path = out / "index.html"
    index_path = out / "installer_archive_safe_apply_index.json"

    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    index = {
        "schema": "qrds.installer_archive_safe_apply_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "apply_mode": payload["apply_mode"],
        "script_files_scanned": payload["script_files_scanned"],
        "archive_candidates_before": payload["archive_candidates_before"],
        "applied_item_count": payload["applied_item_count"],
        "skipped_item_count": payload["skipped_item_count"],
        "remaining_archive_candidates": payload["remaining_archive_candidates"],
        "git_status_lines_before": payload["git_status_lines_before"],
        "git_status_lines_after": payload["git_status_lines_after"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_archive_score": payload["mean_archive_score"],
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
