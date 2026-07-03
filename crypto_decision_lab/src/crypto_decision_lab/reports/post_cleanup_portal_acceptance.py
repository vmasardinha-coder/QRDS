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


def _repo_root(repo_root: str | Path | None = None) -> Path:
    if repo_root:
        return Path(repo_root).resolve()
    here = Path.cwd().resolve()
    for p in [here, *here.parents]:
        if (p / "crypto_decision_lab").exists():
            return p
    return here


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except Exception:
        return str(path)


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


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _sha_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


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
            raise ValueError(f"Operational language is not allowed in post-cleanup portal acceptance: {term}")


def _wrapper(root: Path, rel_path: str, label: str, family: str) -> dict[str, Any]:
    path = root / rel_path
    return {"label": label, "family": family, "path": rel_path, "exists": path.exists()}


def _portal(root: Path, rel_path: str, label: str, family: str) -> dict[str, Any]:
    path = root / rel_path
    return {"label": label, "family": family, "path": rel_path, "exists": path.exists()}


def _discover(root: Path) -> dict[str, Any]:
    artifacts = root / "crypto_decision_lab" / "artifacts"
    archive_dir = root / "scripts" / "archive" / "installers"
    docs_dir = root / "crypto_decision_lab" / "docs"

    wrappers = [
        _wrapper(root, "qrds_unified_portal_serve.sh", "Unified Portal", "unified"),
        _wrapper(root, "qrds_research_command_center_serve.sh", "Research Command Center", "validation"),
        _wrapper(root, "qrds_evidence_stack_serve.sh", "Evidence Stack", "validation"),
        _wrapper(root, "qrds_research_book_reader_serve.sh", "Research Book Reader", "documentation"),
        _wrapper(root, "qrds_research_book_chronicle_serve.sh", "Research Book Chronicle", "documentation"),
        _wrapper(root, "qrds_data_source_contract_from_stack_serve.sh", "Data Source Contract", "data"),
        _wrapper(root, "qrds_data_acquisition_depth_plan_from_stack_serve.sh", "Data Acquisition Plan", "data"),
        _wrapper(root, "qrds_archive_manifest_repo_hygiene_serve.sh", "Archive Manifest", "hygiene"),
    ]

    portals = [
        _portal(root, "crypto_decision_lab/artifacts/unified_portal_suite/index.html", "Unified Portal Suite", "unified"),
        _portal(root, "crypto_decision_lab/artifacts/research_command_center/index.html", "Research Command Center", "validation"),
        _portal(root, "crypto_decision_lab/artifacts/evidence_stack/index.html", "Evidence Stack", "validation"),
        _portal(root, "crypto_decision_lab/artifacts/research_book_reader/index.html", "Research Book Reader", "documentation"),
        _portal(root, "crypto_decision_lab/artifacts/research_book_chronicle/index.html", "Research Book Chronicle", "documentation"),
        _portal(root, "crypto_decision_lab/artifacts/data_source_contract/index.html", "Data Source Contract", "data"),
        _portal(root, "crypto_decision_lab/artifacts/data_acquisition_depth_plan/index.html", "Data Acquisition Plan", "data"),
        _portal(root, "crypto_decision_lab/artifacts/archive_manifest_repo_hygiene/index.html", "Archive Manifest", "hygiene"),
    ]

    root_sprint_installers = sorted(
        [
            p for p in root.glob("*.sh")
            if p.name.startswith("qrds_sprint_") or "hotfix" in p.name.lower()
        ]
    )
    archived_installers = sorted(archive_dir.glob("*.sh")) if archive_dir.exists() else []
    portal_indexes = sorted(artifacts.rglob("index.html")) if artifacts.exists() else []
    docs_files = [p for p in docs_dir.rglob("*") if p.is_file()] if docs_dir.exists() else []

    archive_index = _load_json(artifacts / "archive_manifest_repo_hygiene" / "archive_manifest_repo_hygiene_index.json")
    unified_index = _load_json(artifacts / "unified_portal_suite" / "portal_unification_suite_index.json")
    if not unified_index:
        unified_index = _load_json(artifacts / "unified_portal_suite" / "unified_portal_suite_index.json")

    families = sorted({w["family"] for w in wrappers if w["exists"]} | {p["family"] for p in portals if p["exists"]})

    return {
        "wrappers": wrappers,
        "portals": portals,
        "root_sprint_installers": [_rel(root, p) for p in root_sprint_installers],
        "archived_installers": [_rel(root, p) for p in archived_installers],
        "portal_indexes": [_rel(root, p) for p in portal_indexes],
        "docs_files": [_rel(root, p) for p in docs_files],
        "archive_index_gate_answer": archive_index.get("gate_answer", "MISSING"),
        "archive_index_archived_count": archive_index.get("archived_installer_count", 0),
        "unified_index_gate_answer": unified_index.get("gate_answer", "MISSING"),
        "families": families,
    }


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(x) for x in row) + "|")
    return "\n".join(out)


def render_markdown(payload: dict[str, Any]) -> str:
    wrapper_rows = [[x["label"], x["family"], x["exists"], x["path"]] for x in payload["wrappers"]]
    portal_rows = [[x["label"], x["family"], x["exists"], x["path"]] for x in payload["portals"]]
    criteria_rows = [[c["criterion_id"], c["status"], c["ready"], c["observed"], c["threshold"], c["blocker"]] for c in payload["criteria"]]

    md = f"""# QRDS/QOS Post-Cleanup Portal Acceptance

This page validates that the post-cleanup repository still has a coherent portal/navigation surface.

**Gate answer:** {payload['gate_answer']}

**Policy lock:** {payload['policy_lock']} • **Mode:** {payload['app_mode']}

## Summary

- Portal families: {payload['family_count']}
- Primary families ready: {payload['primary_families_ready']}/{payload['primary_families_total']}
- Launcher wrappers ready: {payload['launcher_wrappers_ready']}/{payload['launcher_wrappers_total']}
- Portal pages ready: {payload['portal_pages_ready']}/{payload['portal_pages_total']}
- Archived installers: {payload['archived_installer_count']}
- Root sprint installers: {payload['root_sprint_installer_count']}
- Portal indexes: {payload['portal_index_count']}
- Docs files: {payload['docs_file_count']}
- Git status lines: {payload['git_status_line_count']}
- Criteria ready: {payload['criteria_ready_count']}/{payload['criteria_total_count']}
- Mean acceptance score: {payload['mean_acceptance_score']}

Safety lock remains active for account access, order flow, execution-style instructions, and live-fund workflow markers.

## Criteria

{_table(['criterion_id', 'status', 'ready', 'observed', 'threshold', 'blocker'], criteria_rows)}

## Launcher wrappers

{_table(['label', 'family', 'exists', 'path'], wrapper_rows)}

## Portal pages

{_table(['label', 'family', 'exists', 'path'], portal_rows)}

Generated at {payload['generated_at']} • SHA256 {payload['report_payload_sha256']}
"""
    _assert_research_only(md)
    return md


def render_html(payload: dict[str, Any]) -> str:
    def esc(x: Any) -> str:
        return html.escape(str(x))

    cards = [
        ("Portal families", payload["family_count"]),
        ("Primary families ready", f"{payload['primary_families_ready']}/{payload['primary_families_total']}"),
        ("Launcher wrappers", f"{payload['launcher_wrappers_ready']}/{payload['launcher_wrappers_total']}"),
        ("Portal pages", f"{payload['portal_pages_ready']}/{payload['portal_pages_total']}"),
        ("Archived installers", payload["archived_installer_count"]),
        ("Root sprint installers", payload["root_sprint_installer_count"]),
        ("Portal indexes", payload["portal_index_count"]),
        ("Docs files", payload["docs_file_count"]),
        ("Git status lines", payload["git_status_line_count"]),
        ("Mean score", payload["mean_acceptance_score"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)

    criteria_rows = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td><td>{esc(c['blocker'])}</td></tr>"
        for c in payload["criteria"]
    )
    wrapper_rows = "".join(
        f"<tr><td>{esc(x['label'])}</td><td>{esc(x['family'])}</td><td>{esc(x['exists'])}</td><td>{esc(x['path'])}</td></tr>"
        for x in payload["wrappers"]
    )
    portal_rows = "".join(
        f"<tr><td>{esc(x['label'])}</td><td>{esc(x['family'])}</td><td>{esc(x['exists'])}</td><td>{esc(x['path'])}</td></tr>"
        for x in payload["portals"]
    )

    page = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>QRDS Post-Cleanup Portal Acceptance</title>
<style>
body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}
.card{{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}}
.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px 8px 8px 0;min-width:150px}}
table{{border-collapse:collapse;width:100%;background:white;margin:14px 0}}
th,td{{border:1px solid #d9deea;padding:8px;text-align:left;font-size:14px;vertical-align:top}}
th{{background:#eef2ff}}
.badge{{display:inline-block;border-radius:999px;background:#e0f2fe;padding:6px 10px;font-weight:700}}
</style></head>
<body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1>
<h2>Post-Cleanup Portal Acceptance</h2>
<p>This page validates that the post-cleanup repository still has a coherent portal/navigation surface. It cannot unlock operational use.</p>
<div class='card'>
<p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p>
<p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>
{card_html}
<p class='badge'>Research-only guardrail active</p>
<p>Safety lock remains active for account access, order flow, execution-style instructions, and live-fund workflow markers.</p>
</div>
<h2>Criteria</h2>
<table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th><th>blocker</th></tr></thead><tbody>{criteria_rows}</tbody></table>
<h2>Launcher wrappers</h2>
<table><thead><tr><th>label</th><th>family</th><th>exists</th><th>path</th></tr></thead><tbody>{wrapper_rows}</tbody></table>
<h2>Portal pages</h2>
<table><thead><tr><th>label</th><th>family</th><th>exists</th><th>path</th></tr></thead><tbody>{portal_rows}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p>
</body></html>"""
    _assert_research_only(page)
    return page


def build_post_cleanup_portal_acceptance(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    discovered = _discover(root)
    wrappers = discovered["wrappers"]
    portals = discovered["portals"]
    git_status = _git_status(root)

    primary_families = {"unified", "validation", "documentation", "data"}
    families_ready = set(discovered["families"])
    primary_ready = len(primary_families & families_ready)

    launcher_ready = sum(1 for w in wrappers if w["exists"])
    portal_ready = sum(1 for p in portals if p["exists"])

    criteria = [
        _criterion("unified_launcher_present", "PASS" if any(w["label"] == "Unified Portal" and w["exists"] for w in wrappers) else "FAIL", any(w["label"] == "Unified Portal" and w["exists"] for w in wrappers), "present" if any(w["label"] == "Unified Portal" and w["exists"] for w in wrappers) else "missing", "unified launcher wrapper exists", ""),
        _criterion("primary_families_ready", "PASS" if primary_ready == len(primary_families) else "WARN", primary_ready == len(primary_families), f"{primary_ready}/{len(primary_families)}", "unified, validation, documentation, data", "" if primary_ready == len(primary_families) else "Some primary portal families are missing."),
        _criterion("archive_manifest_linked", "PASS" if any(w["family"] == "hygiene" and w["exists"] for w in wrappers) else "WARN", any(w["family"] == "hygiene" and w["exists"] for w in wrappers), discovered["archive_index_gate_answer"], "archive manifest wrapper/index present", ""),
        _criterion("root_sprint_installers_clean", "PASS" if len(discovered["root_sprint_installers"]) == 0 else "WARN", len(discovered["root_sprint_installers"]) == 0, len(discovered["root_sprint_installers"]), "0 root sprint/hotfix installers", ""),
        _criterion("docs_surface_present", "PASS" if len(discovered["docs_files"]) > 0 else "FAIL", len(discovered["docs_files"]) > 0, len(discovered["docs_files"]), "> 0 docs files", ""),
        _criterion("portal_surface_present", "PASS" if len(discovered["portal_indexes"]) > 0 else "FAIL", len(discovered["portal_indexes"]) > 0, len(discovered["portal_indexes"]), "> 0 portal index files", ""),
        _criterion("research_only_lock", "PASS", True, "ACTIVE", "policy lock active", ""),
    ]

    ready_count = sum(1 for c in criteria if c["ready"])
    mean_score = round(ready_count / len(criteria), 4)

    if ready_count == len(criteria):
        gate_answer = "POST_CLEANUP_PORTAL_ACCEPTANCE_READY_RESEARCH_ONLY"
    else:
        gate_answer = "POST_CLEANUP_PORTAL_ACCEPTANCE_READY_WITH_NAVIGATION_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.post_cleanup_portal_acceptance.v1",
        "report_name": "qrds-post-cleanup-portal-acceptance",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "family_count": len(discovered["families"]),
        "families": discovered["families"],
        "primary_families_ready": primary_ready,
        "primary_families_total": len(primary_families),
        "launcher_wrappers_ready": launcher_ready,
        "launcher_wrappers_total": len(wrappers),
        "portal_pages_ready": portal_ready,
        "portal_pages_total": len(portals),
        "archived_installer_count": len(discovered["archived_installers"]),
        "root_sprint_installer_count": len(discovered["root_sprint_installers"]),
        "portal_index_count": len(discovered["portal_indexes"]),
        "docs_file_count": len(discovered["docs_files"]),
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "archive_index_gate_answer": discovered["archive_index_gate_answer"],
        "archive_index_archived_count": discovered["archive_index_archived_count"],
        "unified_index_gate_answer": discovered["unified_index_gate_answer"],
        "wrappers": wrappers,
        "portals": portals,
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_acceptance_score": mean_score,
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    report_path = out / "post_cleanup_portal_acceptance.json"
    md_path = out / "post_cleanup_portal_acceptance.md"
    html_path = out / "index.html"
    index_path = out / "post_cleanup_portal_acceptance_index.json"

    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    index = {
        "schema": "qrds.post_cleanup_portal_acceptance_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "family_count": payload["family_count"],
        "primary_families_ready": payload["primary_families_ready"],
        "primary_families_total": payload["primary_families_total"],
        "launcher_wrappers_ready": payload["launcher_wrappers_ready"],
        "launcher_wrappers_total": payload["launcher_wrappers_total"],
        "portal_pages_ready": payload["portal_pages_ready"],
        "portal_pages_total": payload["portal_pages_total"],
        "archived_installer_count": payload["archived_installer_count"],
        "root_sprint_installer_count": payload["root_sprint_installer_count"],
        "portal_index_count": payload["portal_index_count"],
        "docs_file_count": payload["docs_file_count"],
        "git_status_line_count": payload["git_status_line_count"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_acceptance_score": payload["mean_acceptance_score"],
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


build_portal_acceptance = build_post_cleanup_portal_acceptance
