from __future__ import annotations

import hashlib
import html
import json
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
    "real orders generated: true",
    "orders_generated: true",
    "real_capital_used: true",
    "trading_signal_generated: true",
    "executable_signal_generated: true",
    "operational_decision_allowed: true",
)


IMPORTANT_REPORTS = [
    ("data_source_contract", "Data Source Contract", "crypto_decision_lab/artifacts/data_source_contract/data_source_contract_index.json"),
    ("data_acquisition_depth_plan", "Data Acquisition Depth Plan", "crypto_decision_lab/artifacts/data_acquisition_depth_plan/data_acquisition_depth_plan_index.json"),
    ("dataset_depth_requirements", "Dataset Depth Requirements", "crypto_decision_lab/artifacts/dataset_depth_requirements/dataset_depth_requirements_index.json"),
    ("archive_manifest", "Archive Manifest Repo Hygiene", "crypto_decision_lab/artifacts/archive_manifest_repo_hygiene/archive_manifest_repo_hygiene_index.json"),
    ("post_cleanup_portal_acceptance", "Post-Cleanup Portal Acceptance", "crypto_decision_lab/artifacts/post_cleanup_portal_acceptance/post_cleanup_portal_acceptance_index.json"),
    ("portal_unification_suite", "Unified Portal Suite", "crypto_decision_lab/artifacts/unified_portal_suite/portal_unification_suite_index.json"),
    ("portal_unification_suite_alt", "Unified Portal Suite", "crypto_decision_lab/artifacts/unified_portal_suite/unified_portal_suite_index.json"),
    ("research_command_center", "Research Command Center", "crypto_decision_lab/artifacts/research_command_center/research_command_center_index.json"),
    ("evidence_stack", "Evidence Stack", "crypto_decision_lab/artifacts/evidence_stack/evidence_stack_index.json"),
]


def _repo_root(repo_root: str | Path | None = None) -> Path:
    if repo_root:
        return Path(repo_root).resolve()
    here = Path.cwd().resolve()
    for p in [here, *here.parents]:
        if (p / "crypto_decision_lab").exists():
            return p
    return here


def _git_status(root: Path) -> list[str]:
    try:
        proc = subprocess.run(
            ["git", "status", "--short"],
            cwd=str(root),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        return [line for line in proc.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def _load_json(root: Path, rel_path: str) -> dict[str, Any]:
    p = root / rel_path
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        d["_path"] = rel_path
        d["_present"] = True
        return d
    except Exception:
        return {"_path": rel_path, "_present": False, "gate_answer": "MISSING_RESEARCH_ONLY"}


def _pick_report(root: Path, candidates: list[tuple[str, str, str]]) -> dict[str, Any]:
    for key, label, rel in candidates:
        d = _load_json(root, rel)
        if d.get("_present"):
            d["_key"] = key
            d["_label"] = label
            return d
    key, label, rel = candidates[0]
    return {"_key": key, "_label": label, "_path": rel, "_present": False, "gate_answer": "MISSING_RESEARCH_ONLY"}


def _reports(root: Path) -> list[dict[str, Any]]:
    grouped: dict[str, list[tuple[str, str, str]]] = {}
    for key, label, rel in IMPORTANT_REPORTS:
        base = key.replace("_alt", "")
        grouped.setdefault(base, []).append((key, label, rel))
    return [_pick_report(root, candidates) for candidates in grouped.values()]


def _count_files(path: Path, pattern: str = "*") -> int:
    if not path.exists():
        return 0
    return sum(1 for p in path.rglob(pattern) if p.is_file())


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _summary_value(report: dict[str, Any], *names: str, default: Any = 0) -> Any:
    payload = report.get("payload") if isinstance(report.get("payload"), dict) else {}
    for name in names:
        if name in report:
            return report.get(name)
        if name in payload:
            return payload.get(name)
    return default


def _gate_state(report: dict[str, Any]) -> str:
    ga = str(report.get("gate_answer") or "")
    if not report.get("_present"):
        return "MISSING"
    if any(x in ga for x in ("READY_RESEARCH_ONLY", "SCHEMA_READY_RESEARCH_ONLY", "ACCEPTANCE_READY_RESEARCH_ONLY", "INDEX_READY_RESEARCH_ONLY")):
        return "READY"
    if any(x in ga for x in ("HIGH_PRIORITY", "GAPS", "REVIEW", "INCOMPLETE", "BLOCK")):
        return "BLOCKING_OR_REVIEW"
    return "OBSERVED"


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
            raise ValueError(f"Operational language is not allowed in foundation checkpoint next phase: {term}")


def _sha_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(x) for x in row) + "|")
    return "\n".join(out)


def render_markdown(payload: dict[str, Any]) -> str:
    report_rows = [
        [
            r["label"],
            r["present"],
            r["state"],
            r["gate_answer"],
            r["path"],
        ]
        for r in payload["report_matrix"]
    ]
    criteria_rows = [
        [c["criterion_id"], c["status"], c["ready"], c["observed"], c["threshold"], c["blocker"]]
        for c in payload["criteria"]
    ]

    md = f"""# QRDS/QOS Foundation Checkpoint / Next Phase Gate

This checkpoint summarizes the post-cleanup, post-schema foundation and decides whether the project can move into the next research phase.

**Gate answer:** {payload['gate_answer']}

**Policy lock:** {payload['policy_lock']} • **Mode:** {payload['app_mode']}

## Summary

- Reports present: {payload['reports_present']}/{payload['reports_total']}
- Ready reports: {payload['ready_reports']}
- Review/blocking reports: {payload['review_or_blocking_reports']}
- Data schema ready: {payload['data_schema_ready']}
- Depth expansion plan ready: {payload['depth_plan_ready']}
- Repo hygiene ready: {payload['repo_hygiene_ready']}
- Portal acceptance ready: {payload['portal_acceptance_ready']}
- Root sprint installers: {payload['root_sprint_installer_count']}
- Archived installers: {payload['archived_installer_count']}
- Dataset rows observed: {payload['dataset_rows_observed']}
- Target rows/symbol: {payload['target_rows_per_symbol']}
- Git status lines: {payload['git_status_line_count']}
- Criteria ready: {payload['criteria_ready_count']}/{payload['criteria_total_count']}
- Mean checkpoint score: {payload['mean_checkpoint_score']}

## Next phase recommendation

**{payload['next_phase']}**

{payload['next_phase_rationale']}

Safety lock remains active for account access, order flow, execution-style instructions, and live-fund workflow markers.

## Criteria

{_table(['criterion_id', 'status', 'ready', 'observed', 'threshold', 'blocker'], criteria_rows)}

## Report matrix

{_table(['label', 'present', 'state', 'gate_answer', 'path'], report_rows)}

Generated at {payload['generated_at']} • SHA256 {payload['report_payload_sha256']}
"""
    _assert_research_only(md)
    return md


def render_html(payload: dict[str, Any]) -> str:
    def esc(x: Any) -> str:
        return html.escape(str(x))

    cards = [
        ("Reports present", f"{payload['reports_present']}/{payload['reports_total']}"),
        ("Ready reports", payload["ready_reports"]),
        ("Review/blocking", payload["review_or_blocking_reports"]),
        ("Data schema ready", payload["data_schema_ready"]),
        ("Depth plan ready", payload["depth_plan_ready"]),
        ("Repo hygiene ready", payload["repo_hygiene_ready"]),
        ("Portal acceptance", payload["portal_acceptance_ready"]),
        ("Root sprint installers", payload["root_sprint_installer_count"]),
        ("Archived installers", payload["archived_installer_count"]),
        ("Dataset rows", payload["dataset_rows_observed"]),
        ("Target rows/symbol", payload["target_rows_per_symbol"]),
        ("Git status lines", payload["git_status_line_count"]),
        ("Mean score", payload["mean_checkpoint_score"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)

    criteria_rows = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td><td>{esc(c['blocker'])}</td></tr>"
        for c in payload["criteria"]
    )
    report_rows = "".join(
        f"<tr><td>{esc(r['label'])}</td><td>{esc(r['present'])}</td><td>{esc(r['state'])}</td><td>{esc(r['gate_answer'])}</td><td>{esc(r['path'])}</td></tr>"
        for r in payload["report_matrix"]
    )

    page = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>QRDS Foundation Checkpoint / Next Phase Gate</title>
<style>
body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}
.card{{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}}
.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px 8px 8px 0;min-width:150px}}
table{{border-collapse:collapse;width:100%;background:white;margin:14px 0}}
th,td{{border:1px solid #d9deea;padding:8px;text-align:left;font-size:14px;vertical-align:top}}
th{{background:#eef2ff}}
.badge{{display:inline-block;border-radius:999px;background:#e0f2fe;padding:6px 10px;font-weight:700}}
.next{{background:#ecfdf5;border:1px solid #a7f3d0;border-radius:14px;padding:18px;margin:16px 0}}
</style></head>
<body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1>
<h2>Foundation Checkpoint / Next Phase Gate</h2>
<p>This checkpoint summarizes the post-cleanup, post-schema foundation and decides whether the project can move into the next research phase. It cannot unlock operational use.</p>
<div class='card'>
<p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p>
<p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>
{card_html}
<p class='badge'>Research-only guardrail active</p>
<p>Safety lock remains active for account access, order flow, execution-style instructions, and live-fund workflow markers.</p>
</div>
<div class='next'>
<h2>Next phase recommendation</h2>
<p><b>{esc(payload['next_phase'])}</b></p>
<p>{esc(payload['next_phase_rationale'])}</p>
</div>
<h2>Criteria</h2>
<table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th><th>blocker</th></tr></thead><tbody>{criteria_rows}</tbody></table>
<h2>Report matrix</h2>
<table><thead><tr><th>label</th><th>present</th><th>state</th><th>gate_answer</th><th>path</th></tr></thead><tbody>{report_rows}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p>
</body></html>"""
    _assert_research_only(page)
    return page


def build_foundation_checkpoint_next_phase(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    reports = _reports(root)
    report_matrix = []
    for r in reports:
        report_matrix.append(
            {
                "key": r.get("_key"),
                "label": r.get("_label"),
                "path": r.get("_path"),
                "present": bool(r.get("_present")),
                "gate_answer": str(r.get("gate_answer") or "UNKNOWN_RESEARCH_ONLY"),
                "state": _gate_state(r),
            }
        )

    data_source = next((r for r in reports if r.get("_key") == "data_source_contract"), {})
    depth_plan = next((r for r in reports if r.get("_key") == "data_acquisition_depth_plan"), {})
    depth_requirements = next((r for r in reports if r.get("_key") == "dataset_depth_requirements"), {})
    archive = next((r for r in reports if r.get("_key") == "archive_manifest"), {})
    portal_acceptance = next((r for r in reports if r.get("_key") == "post_cleanup_portal_acceptance"), {})

    git_status = _git_status(root)
    root_sprint_installers = [
        p for p in root.glob("*.sh")
        if p.name.startswith("qrds_sprint_") or "hotfix" in p.name.lower()
    ]

    reports_present = sum(1 for r in report_matrix if r["present"])
    ready_reports = sum(1 for r in report_matrix if r["state"] == "READY")
    review_reports = sum(1 for r in report_matrix if r["state"] == "BLOCKING_OR_REVIEW")

    data_schema_ready = "SCHEMA_READY" in str(data_source.get("gate_answer", ""))
    depth_plan_ready = bool(depth_plan.get("_present")) and "DATA_ACQUISITION_DEPTH_PLAN" in str(depth_plan.get("gate_answer", ""))
    repo_hygiene_ready = "ARCHIVE_MANIFEST_REPO_HYGIENE_INDEX_READY" in str(archive.get("gate_answer", ""))
    portal_ready = "POST_CLEANUP_PORTAL_ACCEPTANCE_READY" in str(portal_acceptance.get("gate_answer", ""))

    rows_observed = _as_int(_summary_value(depth_plan, "total_rows", default=0))
    if rows_observed == 0:
        rows_observed = _as_int(_summary_value(depth_requirements, "total_rows", default=0))

    target_rows = _as_int(_summary_value(depth_plan, "target_rows_per_symbol", "target_rows_symbol", default=5000), 5000)
    archived_count = _as_int(_summary_value(archive, "archived_installer_count", default=0))
    root_sprint_count = len(root_sprint_installers)

    criteria = [
        _criterion("data_schema_contract_ready", "PASS" if data_schema_ready else "FAIL", data_schema_ready, str(data_source.get("gate_answer", "MISSING")), "schema contract ready", "" if data_schema_ready else "Data Source Contract not ready."),
        _criterion("depth_plan_ready", "PASS" if depth_plan_ready else "FAIL", depth_plan_ready, str(depth_plan.get("gate_answer", "MISSING")), "depth expansion plan present", "" if depth_plan_ready else "Depth expansion plan missing."),
        _criterion("depth_gap_still_blocking", "PASS" if rows_observed < target_rows * 3 else "WARN", rows_observed < target_rows * 3, rows_observed, "gap should remain explicit before next phase", ""),
        _criterion("repo_hygiene_ready", "PASS" if repo_hygiene_ready else "FAIL", repo_hygiene_ready, str(archive.get("gate_answer", "MISSING")), "archive manifest ready", "" if repo_hygiene_ready else "Archive manifest missing."),
        _criterion("portal_acceptance_ready", "PASS" if portal_ready else "FAIL", portal_ready, str(portal_acceptance.get("gate_answer", "MISSING")), "post-cleanup portal accepted", "" if portal_ready else "Portal acceptance missing."),
        _criterion("root_sprint_installers_clean", "PASS" if root_sprint_count == 0 else "WARN", root_sprint_count == 0, root_sprint_count, "0 root sprint/hotfix installers", ""),
        _criterion("git_worktree_clean", "PASS" if len(git_status) == 0 else "WARN", len(git_status) == 0, len(git_status), "0 git status lines after commit", ""),
        _criterion("research_only_lock", "PASS", True, "ACTIVE", "policy lock active", ""),
    ]

    ready_count = sum(1 for c in criteria if c["ready"])
    mean_score = round(ready_count / len(criteria), 4)

    if data_schema_ready and depth_plan_ready and repo_hygiene_ready and portal_ready and root_sprint_count == 0:
        gate_answer = "FOUNDATION_CHECKPOINT_READY_FOR_PHASE_10_DATA_COLLECTION_RESEARCH_ONLY"
        next_phase = "PHASE_10_DATA_COLLECTION_DRY_RUN"
        next_phase_rationale = "The repository is navigable, schema contract is ready, cleanup is archived, and the remaining blocker is explicit dataset depth. The next phase should collect or synthesize deeper canonical research datasets without operational use."
    else:
        gate_answer = "FOUNDATION_CHECKPOINT_NEEDS_FOUNDATION_REVIEW_RESEARCH_ONLY"
        next_phase = "FOUNDATION_REVIEW_BEFORE_PHASE_10"
        next_phase_rationale = "One or more foundation surfaces are missing or under review. Complete the foundation gaps before expanding datasets."

    payload: dict[str, Any] = {
        "schema": "qrds.foundation_checkpoint_next_phase.v1",
        "report_name": "qrds-foundation-checkpoint-next-phase",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "reports_present": reports_present,
        "reports_total": len(report_matrix),
        "ready_reports": ready_reports,
        "review_or_blocking_reports": review_reports,
        "data_schema_ready": data_schema_ready,
        "depth_plan_ready": depth_plan_ready,
        "repo_hygiene_ready": repo_hygiene_ready,
        "portal_acceptance_ready": portal_ready,
        "root_sprint_installer_count": root_sprint_count,
        "archived_installer_count": archived_count,
        "dataset_rows_observed": rows_observed,
        "target_rows_per_symbol": target_rows,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "next_phase": next_phase,
        "next_phase_rationale": next_phase_rationale,
        "report_matrix": report_matrix,
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_checkpoint_score": mean_score,
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    report_path = out / "foundation_checkpoint_next_phase.json"
    md_path = out / "foundation_checkpoint_next_phase.md"
    html_path = out / "index.html"
    index_path = out / "foundation_checkpoint_next_phase_index.json"

    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    index = {
        "schema": "qrds.foundation_checkpoint_next_phase_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "reports_present": payload["reports_present"],
        "reports_total": payload["reports_total"],
        "ready_reports": payload["ready_reports"],
        "review_or_blocking_reports": payload["review_or_blocking_reports"],
        "data_schema_ready": payload["data_schema_ready"],
        "depth_plan_ready": payload["depth_plan_ready"],
        "repo_hygiene_ready": payload["repo_hygiene_ready"],
        "portal_acceptance_ready": payload["portal_acceptance_ready"],
        "root_sprint_installer_count": payload["root_sprint_installer_count"],
        "archived_installer_count": payload["archived_installer_count"],
        "dataset_rows_observed": payload["dataset_rows_observed"],
        "target_rows_per_symbol": payload["target_rows_per_symbol"],
        "git_status_line_count": payload["git_status_line_count"],
        "next_phase": payload["next_phase"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_checkpoint_score": payload["mean_checkpoint_score"],
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


build_foundation_checkpoint = build_foundation_checkpoint_next_phase
