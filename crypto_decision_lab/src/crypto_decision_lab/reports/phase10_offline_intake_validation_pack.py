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

REQUIRED_FIELDS = ["timestamp", "open", "high", "low", "close", "volume", "symbol", "interval", "source"]


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
        return {"_present": False, "_path": rel_path, "gate_answer": "MISSING_RESEARCH_ONLY"}


def _payload(d: dict[str, Any]) -> dict[str, Any]:
    return d.get("payload") if isinstance(d.get("payload"), dict) else {}


def _field(d: dict[str, Any], name: str, default: Any = None) -> Any:
    p = _payload(d)
    if name in d:
        return d[name]
    if name in p:
        return p[name]
    return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def _git_status(root: Path) -> list[str]:
    try:
        proc = subprocess.run(["git", "status", "--short"], cwd=str(root), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        return [line for line in proc.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return "UNREADABLE"


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
            raise ValueError(f"Operational language is not allowed in phase10 offline intake validation pack: {term}")


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(x) for x in row) + "|")
    return "\n".join(out)


def _templates_from_10c(root: Path) -> list[dict[str, Any]]:
    report = _load_json(root, "crypto_decision_lab/artifacts/manual_intake_template_validation_dry_run/manual_intake_template_validation_dry_run_index.json")
    templates = _field(report, "templates", default=[])
    if isinstance(templates, list) and templates:
        return [t for t in templates if isinstance(t, dict)]

    # Fallback: scan the artifact templates directory.
    template_dir = root / "crypto_decision_lab" / "artifacts" / "manual_intake_template_validation_dry_run" / "templates"
    out: list[dict[str, Any]] = []
    if template_dir.exists():
        for p in sorted(template_dir.glob("*.jsonl")):
            name = p.stem
            symbol = name.split("_manual_template")[0].replace("_", "-").upper()
            out.append(
                {
                    "symbol": symbol,
                    "interval": "1h",
                    "actual_template_path": str(p),
                    "template_format": "JSONL",
                    "ready": True,
                    "template_sha256": _sha_file(p)[:16],
                }
            )
    return out


def _read_jsonl_template(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
    except Exception:
        return []
    return rows


def _validate_row(row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for name in REQUIRED_FIELDS:
        if name not in row:
            errors.append(f"missing:{name}")
    for name in ["open", "high", "low", "close", "volume"]:
        if name in row and not isinstance(row[name], (int, float)):
            errors.append(f"not_number:{name}")
    if all(k in row for k in ("open", "high", "low", "close")):
        high = float(row["high"])
        low = float(row["low"])
        if high < low:
            errors.append("shape:high_lt_low")
        for name in ("open", "close"):
            v = float(row[name])
            if v < low or v > high:
                errors.append(f"shape:{name}_outside_range")
    return errors


def _validate_templates(root: Path, templates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for t in templates:
        path_raw = str(t.get("actual_template_path") or t.get("path") or "")
        p = Path(path_raw)
        if not p.is_absolute():
            p = root / path_raw
        template_rows = _read_jsonl_template(p)
        validation_errors: list[str] = []
        for row in template_rows:
            validation_errors.extend(_validate_row(row))
        rows.append(
            {
                "symbol": str(t.get("symbol") or "UNKNOWN"),
                "interval": str(t.get("interval") or "1h"),
                "template_path": str(p),
                "template_present": p.exists(),
                "template_rows": len(template_rows),
                "validation_errors": validation_errors,
                "valid": p.exists() and len(template_rows) > 0 and not validation_errors,
                "sha256": _sha_file(p)[:16] if p.exists() else "MISSING",
            }
        )
    return rows


def _build_staging_manifest(out: Path, validations: list[dict[str, Any]]) -> dict[str, Any]:
    staging_dir = out / "staging"
    staging_dir.mkdir(parents=True, exist_ok=True)

    entries = []
    for v in validations:
        symbol = v["symbol"]
        interval = v["interval"]
        safe_symbol = symbol.lower().replace("-", "_")
        planned_path = f"crypto_decision_lab/data/research/{safe_symbol}/{interval}/canonical_ohlcv.jsonl"
        entries.append(
            {
                "symbol": symbol,
                "interval": interval,
                "template_valid": bool(v["valid"]),
                "template_sha256": v["sha256"],
                "planned_canonical_path": planned_path,
                "staging_only": True,
                "canonical_write_allowed": False,
            }
        )

    manifest = {
        "schema": "qrds.phase10_staging_manifest.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entries": entries,
        "canonical_data_writes": 0,
        "staging_only": True,
    }
    manifest_text = json.dumps(manifest, indent=2, sort_keys=True)
    manifest_path = staging_dir / "staging_manifest.json"
    manifest_path.write_text(manifest_text, encoding="utf-8")
    return {
        "path": str(manifest_path),
        "entry_count": len(entries),
        "sha256": _sha_text(manifest_text)[:16],
        "canonical_data_writes": 0,
    }


def _station(collection: dict[str, Any], adapter: dict[str, Any], template: dict[str, Any], valid_count: int, total_count: int) -> dict[str, Any]:
    return {
        "where_we_are": "PHASE_10_OFFLINE_INTAKE_VALIDATION",
        "ready_stack": {
            "10A_collection_queue": bool(collection.get("_present")),
            "10B_adapter_dry_run": bool(adapter.get("_present")),
            "10C_manual_templates": bool(template.get("_present")),
            "10D_to_10H_validation_pack": valid_count == total_count and total_count > 0,
        },
        "main_blocker": "Dataset depth remains insufficient; next work should validate actual offline/manual sample files before larger expansion.",
        "next_best_step": "Run controlled sample-file intake into artifact staging, then promote only after schema, hash, and row-count checks pass.",
    }


def render_markdown(payload: dict[str, Any]) -> str:
    validation_rows = [
        [v["symbol"], v["interval"], v["template_present"], v["template_rows"], v["valid"], ";".join(v["validation_errors"]) or "OK", v["template_path"]]
        for v in payload["template_validations"]
    ]
    manifest_rows = [
        [e["symbol"], e["interval"], e["template_valid"], e["canonical_write_allowed"], e["planned_canonical_path"]]
        for e in payload["staging_manifest"]["entries"]
    ]
    criteria_rows = [
        [c["criterion_id"], c["status"], c["ready"], c["observed"], c["threshold"], c["blocker"]]
        for c in payload["criteria"]
    ]

    md = f"""# QRDS/QOS Phase 10 Offline Intake Validation Pack

This bundled pack validates manual templates, builds an artifact-only staging manifest, and states where the project is before any larger data expansion.

**Gate answer:** {payload['gate_answer']}

**Policy lock:** {payload['policy_lock']} • **Mode:** {payload['app_mode']}

## Station

- Where we are: {payload['station']['where_we_are']}
- Main blocker: {payload['station']['main_blocker']}
- Next best step: {payload['station']['next_best_step']}

## Summary

- Collection queue present: {payload['collection_queue_present']}
- Adapter queue present: {payload['adapter_queue_present']}
- Template report present: {payload['template_report_present']}
- Templates checked: {payload['templates_checked']}
- Valid templates: {payload['valid_templates']}
- Staging manifest entries: {payload['staging_manifest_entry_count']}
- Canonical data writes: {payload['canonical_data_writes']}
- Git status lines: {payload['git_status_line_count']}
- Criteria ready: {payload['criteria_ready_count']}/{payload['criteria_total_count']}
- Mean pack score: {payload['mean_pack_score']}

Safety lock remains active for account access, order flow, execution-style instructions, and live-fund workflow markers.

## Template validation

{_table(['symbol', 'interval', 'present', 'rows', 'valid', 'errors', 'path'], validation_rows or [['NONE', 'NONE', False, 0, False, 'MISSING', 'MISSING']])}

## Staging manifest

{_table(['symbol', 'interval', 'template_valid', 'canonical_write_allowed', 'planned_canonical_path'], manifest_rows or [['NONE', 'NONE', False, False, 'MISSING']])}

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
        ("Station", payload["station"]["where_we_are"]),
        ("Collection queue", payload["collection_queue_present"]),
        ("Adapter queue", payload["adapter_queue_present"]),
        ("Templates checked", payload["templates_checked"]),
        ("Valid templates", f"{payload['valid_templates']}/{payload['templates_checked']}"),
        ("Staging entries", payload["staging_manifest_entry_count"]),
        ("Canonical data writes", payload["canonical_data_writes"]),
        ("Git status lines", payload["git_status_line_count"]),
        ("Mean score", payload["mean_pack_score"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)

    validation_rows = "".join(
        f"<tr><td>{esc(v['symbol'])}</td><td>{esc(v['interval'])}</td><td>{esc(v['template_present'])}</td><td>{esc(v['template_rows'])}</td><td>{esc(v['valid'])}</td><td>{esc(';'.join(v['validation_errors']) or 'OK')}</td><td>{esc(v['template_path'])}</td></tr>"
        for v in payload["template_validations"]
    ) or "<tr><td>NONE</td><td>NONE</td><td>False</td><td>0</td><td>False</td><td>MISSING</td><td>MISSING</td></tr>"

    manifest_rows = "".join(
        f"<tr><td>{esc(e['symbol'])}</td><td>{esc(e['interval'])}</td><td>{esc(e['template_valid'])}</td><td>{esc(e['canonical_write_allowed'])}</td><td>{esc(e['planned_canonical_path'])}</td></tr>"
        for e in payload["staging_manifest"]["entries"]
    ) or "<tr><td>NONE</td><td>NONE</td><td>False</td><td>False</td><td>MISSING</td></tr>"

    criteria_rows = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td><td>{esc(c['blocker'])}</td></tr>"
        for c in payload["criteria"]
    )

    page = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>QRDS Phase 10 Offline Intake Validation Pack</title>
<style>
body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}
.card{{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}}
.station{{background:#ecfdf5;border:1px solid #a7f3d0;border-radius:14px;padding:20px;margin:16px 0}}
.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px 8px 8px 0;min-width:150px}}
table{{border-collapse:collapse;width:100%;background:white;margin:14px 0}}
th,td{{border:1px solid #d9deea;padding:8px;text-align:left;font-size:14px;vertical-align:top}}
th{{background:#eef2ff}}
.badge{{display:inline-block;border-radius:999px;background:#e0f2fe;padding:6px 10px;font-weight:700}}
</style></head>
<body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1>
<h2>Phase 10 Offline Intake Validation Pack</h2>
<p>This bundled page validates templates, creates an artifact-only staging manifest, and states where the project is. It cannot unlock operational use.</p>
<div class='card'>
<p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p>
<p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>
{card_html}
<p class='badge'>Research-only guardrail active</p>
<p>Safety lock remains active for account access, order flow, execution-style instructions, and live-fund workflow markers.</p>
</div>
<div class='station'>
<h2>Where we are</h2>
<p><b>{esc(payload['station']['where_we_are'])}</b></p>
<p>Main blocker: {esc(payload['station']['main_blocker'])}</p>
<p>Next best step: {esc(payload['station']['next_best_step'])}</p>
</div>
<h2>Template validation</h2>
<table><thead><tr><th>symbol</th><th>interval</th><th>present</th><th>rows</th><th>valid</th><th>errors</th><th>path</th></tr></thead><tbody>{validation_rows}</tbody></table>
<h2>Staging manifest</h2>
<table><thead><tr><th>symbol</th><th>interval</th><th>template_valid</th><th>canonical_write_allowed</th><th>planned_canonical_path</th></tr></thead><tbody>{manifest_rows}</tbody></table>
<h2>Criteria</h2>
<table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th><th>blocker</th></tr></thead><tbody>{criteria_rows}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p>
</body></html>"""
    _assert_research_only(page)
    return page


def build_phase10_offline_intake_validation_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    collection = _load_json(root, "crypto_decision_lab/artifacts/canonical_data_collection_dry_run/canonical_data_collection_dry_run_index.json")
    adapter = _load_json(root, "crypto_decision_lab/artifacts/canonical_data_source_adapter_dry_run/canonical_data_source_adapter_dry_run_index.json")
    template_report = _load_json(root, "crypto_decision_lab/artifacts/manual_intake_template_validation_dry_run/manual_intake_template_validation_dry_run_index.json")

    templates = _templates_from_10c(root)
    validations = _validate_templates(root, templates)
    staging_manifest_meta = _build_staging_manifest(out, validations)
    staging_manifest = json.loads(Path(staging_manifest_meta["path"]).read_text(encoding="utf-8"))
    git_status = _git_status(root)

    valid_templates = sum(1 for v in validations if v["valid"])
    canonical_data_writes = 0
    station = _station(collection, adapter, template_report, valid_templates, len(validations))

    criteria = [
        _criterion("collection_queue_present", "PASS" if collection.get("_present") else "FAIL", bool(collection.get("_present")), collection.get("gate_answer", "MISSING"), "10A present", ""),
        _criterion("adapter_queue_present", "PASS" if adapter.get("_present") else "FAIL", bool(adapter.get("_present")), adapter.get("gate_answer", "MISSING"), "10B present", ""),
        _criterion("template_report_present", "PASS" if template_report.get("_present") else "FAIL", bool(template_report.get("_present")), template_report.get("gate_answer", "MISSING"), "10C template report present", ""),
        _criterion("templates_valid", "PASS" if validations and valid_templates == len(validations) else "FAIL", bool(validations) and valid_templates == len(validations), f"{valid_templates}/{len(validations)}", "all templates valid", ""),
        _criterion("staging_manifest_created", "PASS" if staging_manifest_meta["entry_count"] == len(validations) else "FAIL", staging_manifest_meta["entry_count"] == len(validations), staging_manifest_meta["entry_count"], "one staging entry per template", ""),
        _criterion("artifact_only_writes", "PASS" if canonical_data_writes == 0 else "FAIL", canonical_data_writes == 0, canonical_data_writes, "0 canonical data writes", ""),
        _criterion("station_created", "PASS", True, station["where_we_are"], "station status present", ""),
        _criterion("research_only_lock", "PASS", True, "ACTIVE", "policy lock active", ""),
    ]

    ready_count = sum(1 for c in criteria if c["ready"])
    mean_score = round(ready_count / len(criteria), 4)

    if collection.get("_present") and adapter.get("_present") and template_report.get("_present") and validations and valid_templates == len(validations):
        gate_answer = "PHASE10_OFFLINE_INTAKE_VALIDATION_PACK_READY_RESEARCH_ONLY"
    else:
        gate_answer = "PHASE10_OFFLINE_INTAKE_VALIDATION_PACK_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.phase10_offline_intake_validation_pack.v1",
        "report_name": "qrds-phase10-offline-intake-validation-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": station,
        "collection_queue_present": bool(collection.get("_present")),
        "adapter_queue_present": bool(adapter.get("_present")),
        "template_report_present": bool(template_report.get("_present")),
        "templates_checked": len(validations),
        "valid_templates": valid_templates,
        "staging_manifest_entry_count": staging_manifest_meta["entry_count"],
        "staging_manifest_sha256": staging_manifest_meta["sha256"],
        "canonical_data_writes": canonical_data_writes,
        "template_validations": validations,
        "staging_manifest": staging_manifest,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_pack_score": mean_score,
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

    report_path = out / "phase10_offline_intake_validation_pack.json"
    md_path = out / "phase10_offline_intake_validation_pack.md"
    html_path = out / "index.html"
    index_path = out / "phase10_offline_intake_validation_pack_index.json"

    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    index = {
        "schema": "qrds.phase10_offline_intake_validation_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "station": payload["station"]["where_we_are"],
        "collection_queue_present": payload["collection_queue_present"],
        "adapter_queue_present": payload["adapter_queue_present"],
        "template_report_present": payload["template_report_present"],
        "templates_checked": payload["templates_checked"],
        "valid_templates": payload["valid_templates"],
        "staging_manifest_entry_count": payload["staging_manifest_entry_count"],
        "canonical_data_writes": payload["canonical_data_writes"],
        "git_status_line_count": payload["git_status_line_count"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_pack_score": payload["mean_pack_score"],
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


build_offline_intake_pack = build_phase10_offline_intake_validation_pack
