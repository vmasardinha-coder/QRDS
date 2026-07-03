from __future__ import annotations

import csv
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
NUMERIC_FIELDS = ["open", "high", "low", "close", "volume"]


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


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


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
            raise ValueError(f"Operational language is not allowed in offline sample intake promotion pack: {term}")


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(x) for x in row) + "|")
    return "\n".join(out)


def _templates_from_validation(root: Path) -> list[dict[str, Any]]:
    report = _load_json(root, "crypto_decision_lab/artifacts/phase10_offline_intake_validation_pack/phase10_offline_intake_validation_pack_index.json")
    vals = _field(report, "template_validations", default=[])
    if isinstance(vals, list) and vals:
        return [v for v in vals if isinstance(v, dict)]

    report10c = _load_json(root, "crypto_decision_lab/artifacts/manual_intake_template_validation_dry_run/manual_intake_template_validation_dry_run_index.json")
    vals10c = _field(report10c, "templates", default=[])
    if isinstance(vals10c, list):
        out = []
        for t in vals10c:
            if isinstance(t, dict):
                out.append(
                    {
                        "symbol": t.get("symbol", "UNKNOWN"),
                        "interval": t.get("interval", "1h"),
                        "valid": t.get("ready", True),
                        "template_path": t.get("actual_template_path") or t.get("path") or "",
                    }
                )
        return out
    return []


def _sample_rows(symbol: str, interval: str, count: int = 5) -> list[dict[str, Any]]:
    rows = []
    base = 100.0
    for i in range(count):
        open_p = base + i
        high = open_p + 1.5
        low = open_p - 1.0
        close = open_p + 0.25
        rows.append(
            {
                "timestamp": f"2026-01-01T0{i}:00:00Z",
                "open": open_p,
                "high": high,
                "low": low,
                "close": close,
                "volume": 1000.0 + i,
                "symbol": symbol,
                "interval": interval,
                "source": "ARTIFACT_SAMPLE_RESEARCH_ONLY",
            }
        )
    return rows


def _write_artifact_samples(out: Path, templates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sample_dir = out / "sample_inputs"
    sample_dir.mkdir(parents=True, exist_ok=True)
    written = []
    seen: set[tuple[str, str]] = set()
    for t in templates:
        symbol = str(t.get("symbol") or "UNKNOWN")
        interval = str(t.get("interval") or "1h")
        key = (symbol, interval)
        if key in seen:
            continue
        seen.add(key)
        rows = _sample_rows(symbol, interval)
        fname = f"{symbol.lower().replace('-', '_')}_{interval}_artifact_sample.jsonl"
        path = sample_dir / fname
        text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
        path.write_text(text, encoding="utf-8")
        written.append(
            {
                "symbol": symbol,
                "interval": interval,
                "path": str(path),
                "rows": len(rows),
                "sha256": _sha_text(text)[:16],
                "artifact_sample": True,
            }
        )
    return written


def _discover_input_files(root: Path, out: Path) -> list[Path]:
    inbox = root / "crypto_decision_lab" / "manual_intake" / "inbox"
    files: list[Path] = []
    if inbox.exists():
        files.extend(sorted([p for p in inbox.glob("*") if p.is_file() and p.suffix.lower() in {".jsonl", ".csv"}]))
    sample_dir = out / "sample_inputs"
    if sample_dir.exists():
        files.extend(sorted([p for p in sample_dir.glob("*") if p.is_file() and p.suffix.lower() in {".jsonl", ".csv"}]))
    return files


def _read_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        if path.suffix.lower() == ".jsonl":
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                obj = json.loads(line)
                if isinstance(obj, dict):
                    rows.append(obj)
        elif path.suffix.lower() == ".csv":
            with path.open("r", encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    rows.append(dict(row))
    except Exception:
        return []
    return rows


def _validate_rows(path: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    valid_rows = 0
    symbols: set[str] = set()
    intervals: set[str] = set()
    timestamps: set[str] = set()
    duplicate_timestamps = 0

    for idx, row in enumerate(rows):
        row_errors: list[str] = []
        for field in REQUIRED_FIELDS:
            if field not in row or row[field] in ("", None):
                row_errors.append(f"row{idx}:missing:{field}")
        nums = {}
        for field in NUMERIC_FIELDS:
            value = _as_float(row.get(field))
            if value is None:
                row_errors.append(f"row{idx}:not_number:{field}")
            else:
                nums[field] = value
        if all(k in nums for k in ["open", "high", "low", "close"]):
            if nums["high"] < nums["low"]:
                row_errors.append(f"row{idx}:shape:high_lt_low")
            for field in ("open", "close"):
                if nums[field] < nums["low"] or nums[field] > nums["high"]:
                    row_errors.append(f"row{idx}:shape:{field}_outside_range")

        ts = str(row.get("timestamp", ""))
        if ts:
            if ts in timestamps:
                duplicate_timestamps += 1
                row_errors.append(f"row{idx}:duplicate_timestamp")
            timestamps.add(ts)

        if row.get("symbol"):
            symbols.add(str(row["symbol"]))
        if row.get("interval"):
            intervals.add(str(row["interval"]))

        if row_errors:
            errors.extend(row_errors)
        else:
            valid_rows += 1

    return {
        "path": str(path),
        "file_name": path.name,
        "source_kind": "INBOX" if "manual_intake/inbox" in str(path).replace("\\", "/") else "ARTIFACT_SAMPLE",
        "sha256": _sha_file(path)[:16],
        "rows": len(rows),
        "valid_rows": valid_rows,
        "error_count": len(errors),
        "errors": errors[:30],
        "symbols": sorted(symbols),
        "intervals": sorted(intervals),
        "duplicate_timestamps": duplicate_timestamps,
        "ready_for_staging": len(rows) > 0 and valid_rows == len(rows) and duplicate_timestamps == 0,
    }


def _build_staging_outputs(out: Path, validations: list[dict[str, Any]]) -> dict[str, Any]:
    staging_dir = out / "validated_staging"
    staging_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    total_staged_rows = 0

    for v in validations:
        if not v["ready_for_staging"]:
            continue
        source = Path(v["path"])
        rows = _read_rows(source)
        if not rows:
            continue
        symbol = v["symbols"][0] if v["symbols"] else "UNKNOWN"
        interval = v["intervals"][0] if v["intervals"] else "1h"
        fname = f"{symbol.lower().replace('-', '_')}_{interval}_validated_staging.jsonl"
        target = staging_dir / fname
        text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
        target.write_text(text, encoding="utf-8")
        total_staged_rows += len(rows)
        entries.append(
            {
                "symbol": symbol,
                "interval": interval,
                "source_file": str(source),
                "staging_file": str(target),
                "rows": len(rows),
                "sha256": _sha_text(text)[:16],
                "canonical_write_allowed": False,
                "promotion_status": "BLOCKED_REVIEW_REQUIRED_RESEARCH_ONLY",
            }
        )

    manifest = {
        "schema": "qrds.phase10_validated_staging_manifest.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entries": entries,
        "staging_rows": total_staged_rows,
        "canonical_data_writes": 0,
        "promotion_allowed": False,
        "promotion_status": "BLOCKED_REVIEW_REQUIRED_RESEARCH_ONLY",
    }
    text = json.dumps(manifest, indent=2, sort_keys=True)
    path = staging_dir / "validated_staging_manifest.json"
    path.write_text(text, encoding="utf-8")
    return {
        "manifest": manifest,
        "path": str(path),
        "entries": len(entries),
        "staging_rows": total_staged_rows,
        "sha256": _sha_text(text)[:16],
    }


def _station(validations: list[dict[str, Any]], staging: dict[str, Any]) -> dict[str, Any]:
    return {
        "where_we_are": "PHASE_10_OFFLINE_SAMPLE_INTAKE_STAGING",
        "main_blocker": "Validated rows are staged under artifacts only; canonical promotion remains blocked pending explicit review.",
        "next_best_step": "Use real offline/manual source files in the inbox, rerun the pack, then inspect row counts, hashes, and data-quality errors before any promotion gate.",
        "files_validated": len(validations),
        "staging_rows": staging["staging_rows"],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    validation_rows = [
        [v["file_name"], v["source_kind"], v["rows"], v["valid_rows"], v["error_count"], v["ready_for_staging"], ",".join(v["symbols"])]
        for v in payload["file_validations"]
    ]
    staging_rows = [
        [e["symbol"], e["interval"], e["rows"], e["promotion_status"], e["staging_file"]]
        for e in payload["validated_staging_manifest"]["entries"]
    ]
    criteria_rows = [
        [c["criterion_id"], c["status"], c["ready"], c["observed"], c["threshold"], c["blocker"]]
        for c in payload["criteria"]
    ]

    md = f"""# QRDS/QOS Phase 10 Offline Sample Intake / Promotion Pack

This bundled pack creates an offline/manual inbox, validates sample files, writes validated staging artifacts, and keeps canonical promotion blocked pending review.

**Gate answer:** {payload['gate_answer']}

**Policy lock:** {payload['policy_lock']} • **Mode:** {payload['app_mode']}

## Station

- Where we are: {payload['station']['where_we_are']}
- Main blocker: {payload['station']['main_blocker']}
- Next best step: {payload['station']['next_best_step']}

## Summary

- Inbox ready: {payload['inbox_ready']}
- Artifact sample files: {payload['artifact_sample_files']}
- Files validated: {payload['files_validated']}
- Valid files: {payload['valid_files']}
- Total rows validated: {payload['total_rows_validated']}
- Valid rows: {payload['valid_rows']}
- Staging entries: {payload['staging_entries']}
- Staging rows: {payload['staging_rows']}
- Canonical data writes: {payload['canonical_data_writes']}
- Promotion allowed: {payload['promotion_allowed']}
- Git status lines: {payload['git_status_line_count']}
- Criteria ready: {payload['criteria_ready_count']}/{payload['criteria_total_count']}
- Mean pack score: {payload['mean_pack_score']}

Safety lock remains active for account access, order flow, execution-style instructions, and live-fund workflow markers.

## File validation

{_table(['file', 'source_kind', 'rows', 'valid_rows', 'errors', 'ready_for_staging', 'symbols'], validation_rows or [['NONE', 'NONE', 0, 0, 0, False, 'MISSING']])}

## Validated staging

{_table(['symbol', 'interval', 'rows', 'promotion_status', 'staging_file'], staging_rows or [['NONE', 'NONE', 0, 'BLOCKED', 'MISSING']])}

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
        ("Inbox ready", payload["inbox_ready"]),
        ("Sample files", payload["artifact_sample_files"]),
        ("Files validated", payload["files_validated"]),
        ("Valid files", payload["valid_files"]),
        ("Rows validated", payload["total_rows_validated"]),
        ("Valid rows", payload["valid_rows"]),
        ("Staging rows", payload["staging_rows"]),
        ("Promotion allowed", payload["promotion_allowed"]),
        ("Canonical writes", payload["canonical_data_writes"]),
        ("Mean score", payload["mean_pack_score"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)

    validation_rows = "".join(
        f"<tr><td>{esc(v['file_name'])}</td><td>{esc(v['source_kind'])}</td><td>{esc(v['rows'])}</td><td>{esc(v['valid_rows'])}</td><td>{esc(v['error_count'])}</td><td>{esc(v['ready_for_staging'])}</td><td>{esc(','.join(v['symbols']))}</td></tr>"
        for v in payload["file_validations"]
    ) or "<tr><td>NONE</td><td>NONE</td><td>0</td><td>0</td><td>0</td><td>False</td><td>MISSING</td></tr>"

    staging_rows = "".join(
        f"<tr><td>{esc(e['symbol'])}</td><td>{esc(e['interval'])}</td><td>{esc(e['rows'])}</td><td>{esc(e['promotion_status'])}</td><td>{esc(e['staging_file'])}</td></tr>"
        for e in payload["validated_staging_manifest"]["entries"]
    ) or "<tr><td>NONE</td><td>NONE</td><td>0</td><td>BLOCKED</td><td>MISSING</td></tr>"

    criteria_rows = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td><td>{esc(c['blocker'])}</td></tr>"
        for c in payload["criteria"]
    )

    page = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>QRDS Phase 10 Offline Sample Intake / Promotion Pack</title>
<style>
body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}
.card{{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}}
.station{{background:#ecfdf5;border:1px solid #a7f3d0;border-radius:14px;padding:20px;margin:16px 0}}
.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px 8px 8px 0;min-width:150px}}
table{{border-collapse:collapse;width:100%;background:white;margin:14px 0}}
th,td{{border:1px solid #d9deea;padding:8px;text-align:left;font-size:14px;vertical-align:top}}
th{{background:#eef2ff}}
.badge{{display:inline-block;border-radius:999px;background:#e0f2fe;padding:6px 10px;font-weight:700}}
.blocked{{display:inline-block;border-radius:999px;background:#fee2e2;padding:6px 10px;font-weight:700}}
</style></head>
<body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1>
<h2>Phase 10 Offline Sample Intake / Promotion Pack</h2>
<p>This bundled page validates offline/manual samples and writes only artifact staging outputs. It cannot unlock operational use.</p>
<div class='card'>
<p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p>
<p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>
{card_html}
<p class='badge'>Research-only guardrail active</p>
<p class='blocked'>Canonical promotion blocked pending explicit review</p>
<p>Safety lock remains active for account access, order flow, execution-style instructions, and live-fund workflow markers.</p>
</div>
<div class='station'>
<h2>Where we are</h2>
<p><b>{esc(payload['station']['where_we_are'])}</b></p>
<p>Main blocker: {esc(payload['station']['main_blocker'])}</p>
<p>Next best step: {esc(payload['station']['next_best_step'])}</p>
</div>
<h2>File validation</h2>
<table><thead><tr><th>file</th><th>source_kind</th><th>rows</th><th>valid_rows</th><th>errors</th><th>ready_for_staging</th><th>symbols</th></tr></thead><tbody>{validation_rows}</tbody></table>
<h2>Validated staging</h2>
<table><thead><tr><th>symbol</th><th>interval</th><th>rows</th><th>promotion_status</th><th>staging_file</th></tr></thead><tbody>{staging_rows}</tbody></table>
<h2>Criteria</h2>
<table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th><th>blocker</th></tr></thead><tbody>{criteria_rows}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p>
</body></html>"""
    _assert_research_only(page)
    return page


def build_phase10_offline_sample_intake_promotion_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    inbox = root / "crypto_decision_lab" / "manual_intake" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)

    prior_pack = _load_json(root, "crypto_decision_lab/artifacts/phase10_offline_intake_validation_pack/phase10_offline_intake_validation_pack_index.json")
    templates = _templates_from_validation(root)
    artifact_samples = _write_artifact_samples(out, templates)
    input_files = _discover_input_files(root, out)
    file_validations = [_validate_rows(path, _read_rows(path)) for path in input_files]
    staging = _build_staging_outputs(out, file_validations)
    station = _station(file_validations, staging)

    valid_files = sum(1 for v in file_validations if v["ready_for_staging"])
    total_rows = sum(int(v["rows"]) for v in file_validations)
    valid_rows = sum(int(v["valid_rows"]) for v in file_validations)
    canonical_data_writes = 0
    promotion_allowed = False
    git_status = _git_status(root)

    criteria = [
        _criterion("previous_validation_pack_present", "PASS" if prior_pack.get("_present") else "WARN", bool(prior_pack.get("_present")), prior_pack.get("gate_answer", "MISSING"), "10D-10H pack present", ""),
        _criterion("manual_inbox_ready", "PASS" if inbox.exists() else "FAIL", inbox.exists(), str(inbox), "manual intake inbox exists", ""),
        _criterion("artifact_samples_created", "PASS" if artifact_samples else "FAIL", bool(artifact_samples), len(artifact_samples), "> 0 artifact samples", ""),
        _criterion("files_validated", "PASS" if file_validations else "FAIL", bool(file_validations), len(file_validations), "> 0 files validated", ""),
        _criterion("valid_rows_present", "PASS" if valid_rows > 0 else "FAIL", valid_rows > 0, valid_rows, "> 0 valid rows", ""),
        _criterion("staging_outputs_created", "PASS" if staging["entries"] > 0 else "FAIL", staging["entries"] > 0, staging["entries"], "> 0 staging entries", ""),
        _criterion("canonical_promotion_blocked", "PASS" if not promotion_allowed else "FAIL", not promotion_allowed, promotion_allowed, "promotion_allowed must be false", ""),
        _criterion("artifact_only_writes", "PASS" if canonical_data_writes == 0 else "FAIL", canonical_data_writes == 0, canonical_data_writes, "0 canonical data writes", ""),
        _criterion("research_only_lock", "PASS", True, "ACTIVE", "policy lock active", ""),
    ]

    ready_count = sum(1 for c in criteria if c["ready"])
    mean_score = round(ready_count / len(criteria), 4)

    if artifact_samples and file_validations and valid_rows > 0 and staging["entries"] > 0 and canonical_data_writes == 0 and not promotion_allowed:
        gate_answer = "PHASE10_OFFLINE_SAMPLE_INTAKE_PROMOTION_PACK_READY_REVIEW_BLOCKED_RESEARCH_ONLY"
    else:
        gate_answer = "PHASE10_OFFLINE_SAMPLE_INTAKE_PROMOTION_PACK_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.phase10_offline_sample_intake_promotion_pack.v1",
        "report_name": "qrds-phase10-offline-sample-intake-promotion-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": station,
        "prior_validation_pack_present": bool(prior_pack.get("_present")),
        "inbox_ready": inbox.exists(),
        "inbox_path": str(inbox),
        "artifact_sample_files": len(artifact_samples),
        "files_validated": len(file_validations),
        "valid_files": valid_files,
        "total_rows_validated": total_rows,
        "valid_rows": valid_rows,
        "staging_entries": staging["entries"],
        "staging_rows": staging["staging_rows"],
        "canonical_data_writes": canonical_data_writes,
        "promotion_allowed": promotion_allowed,
        "promotion_status": "BLOCKED_REVIEW_REQUIRED_RESEARCH_ONLY",
        "artifact_samples": artifact_samples,
        "file_validations": file_validations,
        "validated_staging_manifest": staging["manifest"],
        "validated_staging_manifest_path": staging["path"],
        "validated_staging_manifest_sha256": staging["sha256"],
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_pack_score": mean_score,
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    report_path = out / "phase10_offline_sample_intake_promotion_pack.json"
    md_path = out / "phase10_offline_sample_intake_promotion_pack.md"
    html_path = out / "index.html"
    index_path = out / "phase10_offline_sample_intake_promotion_pack_index.json"

    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    index = {
        "schema": "qrds.phase10_offline_sample_intake_promotion_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "station": payload["station"]["where_we_are"],
        "prior_validation_pack_present": payload["prior_validation_pack_present"],
        "inbox_ready": payload["inbox_ready"],
        "artifact_sample_files": payload["artifact_sample_files"],
        "files_validated": payload["files_validated"],
        "valid_files": payload["valid_files"],
        "total_rows_validated": payload["total_rows_validated"],
        "valid_rows": payload["valid_rows"],
        "staging_entries": payload["staging_entries"],
        "staging_rows": payload["staging_rows"],
        "canonical_data_writes": payload["canonical_data_writes"],
        "promotion_allowed": payload["promotion_allowed"],
        "promotion_status": payload["promotion_status"],
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


build_sample_intake_pack = build_phase10_offline_sample_intake_promotion_pack
