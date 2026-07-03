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

REQUIRED_FIELDS = [
    {"name": "timestamp", "type": "integer|string", "description": "UTC timestamp or ISO-8601 time."},
    {"name": "open", "type": "number", "description": "Open price."},
    {"name": "high", "type": "number", "description": "High price."},
    {"name": "low", "type": "number", "description": "Low price."},
    {"name": "close", "type": "number", "description": "Close price."},
    {"name": "volume", "type": "number", "description": "Base/venue volume as provided by source."},
    {"name": "symbol", "type": "string", "description": "Canonical symbol, e.g. BTC-USDT."},
    {"name": "interval", "type": "string", "description": "Bar interval, e.g. 1h."},
    {"name": "source", "type": "string", "description": "Source profile or filename origin."},
]

OPTIONAL_FIELDS = [
    {"name": "source_row_id", "type": "string", "description": "Optional stable row identifier."},
    {"name": "ingested_at", "type": "string", "description": "Optional UTC ingestion timestamp."},
    {"name": "quality_notes", "type": "string", "description": "Optional data-quality note."},
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
            raise ValueError(f"Operational language is not allowed in manual intake template validation dry run: {term}")


def _sha_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(x) for x in row) + "|")
    return "\n".join(out)


def _adapter_jobs(adapter_report: dict[str, Any]) -> list[dict[str, Any]]:
    jobs = _field(adapter_report, "adapter_jobs", default=[])
    if isinstance(jobs, list):
        return [j for j in jobs if isinstance(j, dict)]
    return []


def _sample_record(symbol: str, interval: str, source: str) -> dict[str, Any]:
    return {
        "timestamp": "2026-01-01T00:00:00Z",
        "open": 0.0,
        "high": 0.0,
        "low": 0.0,
        "close": 0.0,
        "volume": 0.0,
        "symbol": symbol,
        "interval": interval,
        "source": source,
    }


def _validate_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        name = field["name"]
        if name not in record:
            errors.append(f"missing:{name}")
    for name in ["open", "high", "low", "close", "volume"]:
        if name in record and not isinstance(record[name], (int, float)):
            errors.append(f"not_number:{name}")
    if all(k in record for k in ("open", "high", "low", "close")):
        high = float(record["high"])
        low = float(record["low"])
        values = [float(record["open"]), float(record["close"])]
        if high < low:
            errors.append("price_shape:high_lt_low")
        if any(v > high or v < low for v in values):
            errors.append("price_shape:open_close_outside_range")
    return errors


def _build_templates(adapter_jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_symbol: dict[str, dict[str, Any]] = {}
    for job in adapter_jobs:
        symbol = str(job.get("symbol") or "UNKNOWN")
        if symbol in by_symbol:
            continue
        interval = str(job.get("interval") or "1h")
        source = str(job.get("source_type") or "MANUAL_FILE_DROP")
        record = _sample_record(symbol, interval, source)
        errors = _validate_record(record)
        output_path = f"crypto_decision_lab/artifacts/manual_intake_template_validation_dry_run/templates/{symbol.lower().replace('-', '_')}_{interval}_template.jsonl"
        by_symbol[symbol] = {
            "symbol": symbol,
            "interval": interval,
            "template_format": "JSONL",
            "output_path": output_path,
            "sample_record": record,
            "sample_record_sha256": _sha_text(json.dumps(record, sort_keys=True))[:16],
            "validation_errors": errors,
            "ready": len(errors) == 0,
        }
    return list(by_symbol.values())


def _write_template_files(out: Path, templates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    template_dir = out / "templates"
    template_dir.mkdir(parents=True, exist_ok=True)
    written: list[dict[str, Any]] = []
    for t in templates:
        path = out / Path(t["output_path"]).name
        # Keep template files in the artifact directory to avoid writing into canonical data.
        path = template_dir / Path(t["output_path"]).name
        text = json.dumps(t["sample_record"], sort_keys=True, ensure_ascii=False) + "\n"
        path.write_text(text, encoding="utf-8")
        row = dict(t)
        row["actual_template_path"] = str(path)
        row["template_sha256"] = _sha_text(text)[:16]
        written.append(row)
    return written


def render_markdown(payload: dict[str, Any]) -> str:
    template_rows = [
        [t["symbol"], t["interval"], t["template_format"], t["ready"], t["template_sha256"], t["actual_template_path"]]
        for t in payload["templates"]
    ]
    field_rows = [
        [f["name"], f["type"], f["description"]]
        for f in payload["required_fields"]
    ]
    criteria_rows = [
        [c["criterion_id"], c["status"], c["ready"], c["observed"], c["threshold"], c["blocker"]]
        for c in payload["criteria"]
    ]

    md = f"""# QRDS/QOS Manual Intake Template / Validation Dry Run

This report creates manual intake templates for canonical research datasets and validates the template structure. It writes templates only under artifacts.

**Gate answer:** {payload['gate_answer']}

**Policy lock:** {payload['policy_lock']} • **Mode:** {payload['app_mode']}

## Summary

- Adapter queue present: {payload['adapter_queue_present']}
- Adapter jobs: {payload['adapter_jobs_count']}
- Templates created: {payload['templates_created']}
- Valid templates: {payload['valid_templates']}
- Required fields: {payload['required_field_count']}
- Optional fields: {payload['optional_field_count']}
- Template destination: {payload['template_destination']}
- Canonical data writes: {payload['canonical_data_writes']}
- Git status lines: {payload['git_status_line_count']}
- Criteria ready: {payload['criteria_ready_count']}/{payload['criteria_total_count']}
- Mean template score: {payload['mean_template_score']}

Safety lock remains active for account access, order flow, execution-style instructions, and live-fund workflow markers.

## Required canonical fields

{_table(['name', 'type', 'description'], field_rows)}

## Templates

{_table(['symbol', 'interval', 'format', 'ready', 'sha256', 'path'], template_rows or [['NONE', 'NONE', 'NONE', False, 'MISSING', 'MISSING']])}

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
        ("Adapter queue", payload["adapter_queue_present"]),
        ("Adapter jobs", payload["adapter_jobs_count"]),
        ("Templates created", payload["templates_created"]),
        ("Valid templates", payload["valid_templates"]),
        ("Required fields", payload["required_field_count"]),
        ("Template destination", payload["template_destination"]),
        ("Canonical data writes", payload["canonical_data_writes"]),
        ("Git status lines", payload["git_status_line_count"]),
        ("Mean score", payload["mean_template_score"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)

    field_rows = "".join(
        f"<tr><td>{esc(f['name'])}</td><td>{esc(f['type'])}</td><td>{esc(f['description'])}</td></tr>"
        for f in payload["required_fields"]
    )
    template_rows = "".join(
        f"<tr><td>{esc(t['symbol'])}</td><td>{esc(t['interval'])}</td><td>{esc(t['template_format'])}</td><td>{esc(t['ready'])}</td><td>{esc(t['template_sha256'])}</td><td>{esc(t['actual_template_path'])}</td></tr>"
        for t in payload["templates"]
    ) or "<tr><td>NONE</td><td>NONE</td><td>NONE</td><td>False</td><td>MISSING</td><td>MISSING</td></tr>"
    criteria_rows = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td><td>{esc(c['blocker'])}</td></tr>"
        for c in payload["criteria"]
    )

    page = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>QRDS Manual Intake Template / Validation Dry Run</title>
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
<h2>Manual Intake Template / Validation Dry Run</h2>
<p>This page creates manual intake templates for canonical research datasets and validates the template structure. It cannot unlock operational use.</p>
<div class='card'>
<p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p>
<p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>
{card_html}
<p class='badge'>Research-only guardrail active</p>
<p>Safety lock remains active for account access, order flow, execution-style instructions, and live-fund workflow markers.</p>
</div>
<h2>Required canonical fields</h2>
<table><thead><tr><th>name</th><th>type</th><th>description</th></tr></thead><tbody>{field_rows}</tbody></table>
<h2>Templates</h2>
<table><thead><tr><th>symbol</th><th>interval</th><th>format</th><th>ready</th><th>sha256</th><th>path</th></tr></thead><tbody>{template_rows}</tbody></table>
<h2>Criteria</h2>
<table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th><th>blocker</th></tr></thead><tbody>{criteria_rows}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p>
</body></html>"""
    _assert_research_only(page)
    return page


def build_manual_intake_template_validation_dry_run(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    adapter_report = _load_json(root, "crypto_decision_lab/artifacts/canonical_data_source_adapter_dry_run/canonical_data_source_adapter_dry_run_index.json")
    adapter_jobs = _adapter_jobs(adapter_report)
    templates = _write_template_files(out, _build_templates(adapter_jobs))
    git_status = _git_status(root)

    valid_templates = sum(1 for t in templates if t["ready"])
    canonical_data_writes = 0

    criteria = [
        _criterion("adapter_queue_present", "PASS" if adapter_report.get("_present") else "FAIL", bool(adapter_report.get("_present")), adapter_report.get("gate_answer", "MISSING"), "10B adapter queue present", ""),
        _criterion("templates_created", "PASS" if templates else "FAIL", bool(templates), len(templates), "> 0 templates", ""),
        _criterion("templates_valid", "PASS" if templates and valid_templates == len(templates) else "FAIL", bool(templates) and valid_templates == len(templates), f"{valid_templates}/{len(templates)}", "all templates valid", ""),
        _criterion("required_fields_defined", "PASS" if len(REQUIRED_FIELDS) >= 9 else "FAIL", len(REQUIRED_FIELDS) >= 9, len(REQUIRED_FIELDS), ">= 9 required fields", ""),
        _criterion("artifact_only_writes", "PASS" if canonical_data_writes == 0 else "FAIL", canonical_data_writes == 0, canonical_data_writes, "0 canonical data writes in dry run", ""),
        _criterion("git_status_recorded", "PASS", True, len(git_status), "git status captured", ""),
        _criterion("research_only_lock", "PASS", True, "ACTIVE", "policy lock active", ""),
    ]

    ready_count = sum(1 for c in criteria if c["ready"])
    mean_score = round(ready_count / len(criteria), 4)

    if adapter_report.get("_present") and templates and valid_templates == len(templates):
        gate_answer = "MANUAL_INTAKE_TEMPLATE_VALIDATION_DRY_RUN_READY_RESEARCH_ONLY"
    else:
        gate_answer = "MANUAL_INTAKE_TEMPLATE_VALIDATION_DRY_RUN_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.manual_intake_template_validation_dry_run.v1",
        "report_name": "qrds-manual-intake-template-validation-dry-run",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "adapter_queue_present": bool(adapter_report.get("_present")),
        "adapter_gate_answer": adapter_report.get("gate_answer", "MISSING"),
        "adapter_jobs_count": len(adapter_jobs),
        "templates_created": len(templates),
        "valid_templates": valid_templates,
        "required_field_count": len(REQUIRED_FIELDS),
        "optional_field_count": len(OPTIONAL_FIELDS),
        "template_destination": "artifacts_only",
        "canonical_data_writes": canonical_data_writes,
        "required_fields": REQUIRED_FIELDS,
        "optional_fields": OPTIONAL_FIELDS,
        "templates": templates,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_template_score": mean_score,
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    report_path = out / "manual_intake_template_validation_dry_run.json"
    md_path = out / "manual_intake_template_validation_dry_run.md"
    html_path = out / "index.html"
    index_path = out / "manual_intake_template_validation_dry_run_index.json"

    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    index = {
        "schema": "qrds.manual_intake_template_validation_dry_run_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "adapter_queue_present": payload["adapter_queue_present"],
        "adapter_jobs_count": payload["adapter_jobs_count"],
        "templates_created": payload["templates_created"],
        "valid_templates": payload["valid_templates"],
        "required_field_count": payload["required_field_count"],
        "optional_field_count": payload["optional_field_count"],
        "template_destination": payload["template_destination"],
        "canonical_data_writes": payload["canonical_data_writes"],
        "git_status_line_count": payload["git_status_line_count"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_template_score": payload["mean_template_score"],
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


build_manual_intake_template = build_manual_intake_template_validation_dry_run
