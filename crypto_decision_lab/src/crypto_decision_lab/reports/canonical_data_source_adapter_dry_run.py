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

ADAPTERS = [
    {
        "adapter_id": "local_fixture_import",
        "source_type": "LOCAL_FILE",
        "auth_required": False,
        "network_used_in_dry_run": False,
        "status": "READY_FOR_DRY_RUN",
        "notes": "Reads already stored local canonical or fixture files only.",
    },
    {
        "adapter_id": "manual_csv_jsonl_intake",
        "source_type": "MANUAL_FILE_DROP",
        "auth_required": False,
        "network_used_in_dry_run": False,
        "status": "READY_FOR_DRY_RUN",
        "notes": "Accepts manually provided CSV or JSONL after schema validation.",
    },
    {
        "adapter_id": "public_ohlcv_rest_plan",
        "source_type": "PUBLIC_REST_PLAN_ONLY",
        "auth_required": False,
        "network_used_in_dry_run": False,
        "status": "PLAN_ONLY",
        "notes": "Documents how a public OHLCV pull would be mapped later; this report performs no network operation.",
    },
    {
        "adapter_id": "offline_cache_replay",
        "source_type": "OFFLINE_CACHE",
        "auth_required": False,
        "network_used_in_dry_run": False,
        "status": "READY_FOR_DRY_RUN",
        "notes": "Replays approved local cache files after manifest/hash checks.",
    },
]


def _repo_root(repo_root: str | Path | None = None) -> Path:
    if repo_root:
        return Path(repo_root).resolve()
    here = Path.cwd().resolve()
    for p in [here, *here.parents]:
        if (p / "crypto_decision_lab").exists():
            return p
    return here


def _load_json(root: Path, rel_path: str) -> dict[str, Any]:
    p = root / rel_path
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        d["_present"] = True
        d["_path"] = rel_path
        return d
    except Exception:
        return {"_present": False, "_path": rel_path}


def _payload(d: dict[str, Any]) -> dict[str, Any]:
    return d.get("payload") if isinstance(d.get("payload"), dict) else {}


def _field(d: dict[str, Any], name: str, default: Any = None) -> Any:
    p = _payload(d)
    if name in d:
        return d[name]
    if name in p:
        return p[name]
    return default


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


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


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
            raise ValueError(f"Operational language is not allowed in canonical data source adapter dry run: {term}")


def _sha_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(x) for x in row) + "|")
    return "\n".join(out)


def _jobs_from_collection(collection: dict[str, Any]) -> list[dict[str, Any]]:
    jobs = _field(collection, "collection_jobs", default=[])
    if isinstance(jobs, list):
        return [j for j in jobs if isinstance(j, dict)]
    return []


def _build_adapter_jobs(collection_jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for job in collection_jobs:
        symbol = str(job.get("symbol") or "UNKNOWN")
        interval = str(job.get("interval") or "1h")
        output_path = str(job.get("output_path") or "")
        gap = _as_int(job.get("gap_rows"), 0)
        for adapter in ADAPTERS:
            rows.append(
                {
                    "symbol": symbol,
                    "interval": interval,
                    "adapter_id": adapter["adapter_id"],
                    "source_type": adapter["source_type"],
                    "auth_required": adapter["auth_required"],
                    "network_used_in_dry_run": adapter["network_used_in_dry_run"],
                    "status": adapter["status"],
                    "gap_rows": gap,
                    "output_path": output_path,
                    "dry_run_only": True,
                }
            )
    return rows


def render_markdown(payload: dict[str, Any]) -> str:
    adapter_rows = [
        [a["adapter_id"], a["source_type"], a["auth_required"], a["network_used_in_dry_run"], a["status"], a["notes"]]
        for a in payload["adapters"]
    ]
    job_rows = [
        [j["symbol"], j["interval"], j["adapter_id"], j["gap_rows"], j["status"], j["output_path"]]
        for j in payload["adapter_jobs"][:80]
    ]
    criteria_rows = [
        [c["criterion_id"], c["status"], c["ready"], c["observed"], c["threshold"], c["blocker"]]
        for c in payload["criteria"]
    ]

    md = f"""# QRDS/QOS Canonical Data Source Adapter Dry Run

This report maps the dry-run collection queue to source adapters. It performs no network operation and does not create live workflow markers.

**Gate answer:** {payload['gate_answer']}

**Policy lock:** {payload['policy_lock']} • **Mode:** {payload['app_mode']}

## Summary

- Collection queue present: {payload['collection_queue_present']}
- Collection jobs: {payload['collection_jobs_count']}
- Source adapters: {payload['adapter_count']}
- Adapter jobs: {payload['adapter_jobs_count']}
- Auth-free adapters: {payload['auth_free_adapter_count']}
- Network operations in dry run: {payload['network_operations_in_dry_run']}
- Total gap rows: {payload['total_gap_rows']}
- Git status lines: {payload['git_status_line_count']}
- Criteria ready: {payload['criteria_ready_count']}/{payload['criteria_total_count']}
- Mean adapter score: {payload['mean_adapter_score']}

Safety lock remains active for account access, order flow, execution-style instructions, and live-fund workflow markers.

## Source adapters

{_table(['adapter_id', 'source_type', 'auth_required', 'network_used_in_dry_run', 'status', 'notes'], adapter_rows)}

## Adapter jobs

{_table(['symbol', 'interval', 'adapter_id', 'gap_rows', 'status', 'output_path'], job_rows or [['NONE', 'NONE', 'NONE', 0, 'MISSING', 'MISSING']])}

## Criteria

{_table(['criterion_id', 'status', 'ready', 'observed', 'threshold', 'blocker'], criteria_rows)}

Generated at {payload['generated_at']} • SHA256 {payload['report_payload_sha256']}
"""
    _assert_research_only(md)
    return md


def render_html(payload: dict[str, Any]) -> str:
    def esc(x: Any) -> str:
        return html.escape(str(x))

    cards = [
        ("Collection queue", payload["collection_queue_present"]),
        ("Collection jobs", payload["collection_jobs_count"]),
        ("Source adapters", payload["adapter_count"]),
        ("Adapter jobs", payload["adapter_jobs_count"]),
        ("Auth-free adapters", payload["auth_free_adapter_count"]),
        ("Network ops in dry run", payload["network_operations_in_dry_run"]),
        ("Total gap rows", payload["total_gap_rows"]),
        ("Git status lines", payload["git_status_line_count"]),
        ("Mean score", payload["mean_adapter_score"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)

    adapter_rows = "".join(
        f"<tr><td>{esc(a['adapter_id'])}</td><td>{esc(a['source_type'])}</td><td>{esc(a['auth_required'])}</td><td>{esc(a['network_used_in_dry_run'])}</td><td>{esc(a['status'])}</td><td>{esc(a['notes'])}</td></tr>"
        for a in payload["adapters"]
    )
    job_rows = "".join(
        f"<tr><td>{esc(j['symbol'])}</td><td>{esc(j['interval'])}</td><td>{esc(j['adapter_id'])}</td><td>{esc(j['gap_rows'])}</td><td>{esc(j['status'])}</td><td>{esc(j['output_path'])}</td></tr>"
        for j in payload["adapter_jobs"][:100]
    ) or "<tr><td>NONE</td><td>NONE</td><td>NONE</td><td>0</td><td>MISSING</td><td>MISSING</td></tr>"
    criteria_rows = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td><td>{esc(c['blocker'])}</td></tr>"
        for c in payload["criteria"]
    )

    page = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>QRDS Canonical Data Source Adapter Dry Run</title>
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
<h2>Canonical Data Source Adapter Dry Run</h2>
<p>This page maps the dry-run collection queue to source adapters. It cannot unlock operational use.</p>
<div class='card'>
<p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p>
<p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>
{card_html}
<p class='badge'>Research-only guardrail active</p>
<p>Safety lock remains active for account access, order flow, execution-style instructions, and live-fund workflow markers.</p>
</div>
<h2>Source adapters</h2>
<table><thead><tr><th>adapter_id</th><th>source_type</th><th>auth_required</th><th>network_used_in_dry_run</th><th>status</th><th>notes</th></tr></thead><tbody>{adapter_rows}</tbody></table>
<h2>Adapter jobs</h2>
<table><thead><tr><th>symbol</th><th>interval</th><th>adapter_id</th><th>gap_rows</th><th>status</th><th>output_path</th></tr></thead><tbody>{job_rows}</tbody></table>
<h2>Criteria</h2>
<table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th><th>blocker</th></tr></thead><tbody>{criteria_rows}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p>
</body></html>"""
    _assert_research_only(page)
    return page


def build_canonical_data_source_adapter_dry_run(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    collection = _load_json(root, "crypto_decision_lab/artifacts/canonical_data_collection_dry_run/canonical_data_collection_dry_run_index.json")
    collection_jobs = _jobs_from_collection(collection)
    adapter_jobs = _build_adapter_jobs(collection_jobs)
    git_status = _git_status(root)

    adapter_count = len(ADAPTERS)
    auth_free = sum(1 for a in ADAPTERS if not a["auth_required"])
    network_ops = sum(1 for a in ADAPTERS if a["network_used_in_dry_run"])
    total_gap = sum(_as_int(j.get("gap_rows"), 0) for j in collection_jobs)

    criteria = [
        _criterion("collection_queue_present", "PASS" if collection.get("_present") else "FAIL", bool(collection.get("_present")), collection.get("gate_answer", "MISSING"), "10A collection queue present", ""),
        _criterion("adapters_defined", "PASS" if adapter_count >= 3 else "FAIL", adapter_count >= 3, adapter_count, ">= 3 adapters", ""),
        _criterion("auth_free_only", "PASS" if auth_free == adapter_count else "FAIL", auth_free == adapter_count, f"{auth_free}/{adapter_count}", "all adapters auth-free", ""),
        _criterion("dry_run_network_zero", "PASS" if network_ops == 0 else "FAIL", network_ops == 0, network_ops, "0 network operations in dry run", ""),
        _criterion("adapter_jobs_created", "PASS" if adapter_jobs else "FAIL", bool(adapter_jobs), len(adapter_jobs), "> 0 adapter jobs", ""),
        _criterion("depth_gap_carried_forward", "PASS" if total_gap > 0 else "WARN", total_gap > 0, total_gap, "> 0 gap rows", ""),
        _criterion("research_only_lock", "PASS", True, "ACTIVE", "policy lock active", ""),
    ]

    ready_count = sum(1 for c in criteria if c["ready"])
    mean_score = round(ready_count / len(criteria), 4)

    if collection.get("_present") and adapter_jobs and network_ops == 0 and auth_free == adapter_count:
        gate_answer = "CANONICAL_DATA_SOURCE_ADAPTER_DRY_RUN_READY_RESEARCH_ONLY"
    else:
        gate_answer = "CANONICAL_DATA_SOURCE_ADAPTER_DRY_RUN_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.canonical_data_source_adapter_dry_run.v1",
        "report_name": "qrds-canonical-data-source-adapter-dry-run",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "collection_queue_present": bool(collection.get("_present")),
        "collection_gate_answer": collection.get("gate_answer", "MISSING"),
        "collection_jobs_count": len(collection_jobs),
        "adapter_count": adapter_count,
        "auth_free_adapter_count": auth_free,
        "network_operations_in_dry_run": network_ops,
        "adapter_jobs_count": len(adapter_jobs),
        "total_gap_rows": total_gap,
        "adapters": ADAPTERS,
        "adapter_jobs": adapter_jobs,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_adapter_score": mean_score,
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    report_path = out / "canonical_data_source_adapter_dry_run.json"
    md_path = out / "canonical_data_source_adapter_dry_run.md"
    html_path = out / "index.html"
    index_path = out / "canonical_data_source_adapter_dry_run_index.json"

    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    index = {
        "schema": "qrds.canonical_data_source_adapter_dry_run_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "collection_queue_present": payload["collection_queue_present"],
        "collection_jobs_count": payload["collection_jobs_count"],
        "adapter_count": payload["adapter_count"],
        "auth_free_adapter_count": payload["auth_free_adapter_count"],
        "network_operations_in_dry_run": payload["network_operations_in_dry_run"],
        "adapter_jobs_count": payload["adapter_jobs_count"],
        "total_gap_rows": payload["total_gap_rows"],
        "git_status_line_count": payload["git_status_line_count"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_adapter_score": payload["mean_adapter_score"],
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


build_adapter_dry_run = build_canonical_data_source_adapter_dry_run
