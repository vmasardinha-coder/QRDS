from __future__ import annotations

import hashlib
import html
import json
import subprocess
from collections import Counter, defaultdict
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
MIN_SAMPLE_ROWS_PER_SYMBOL = 5
TARGET_ROWS_PER_SYMBOL = 5000


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
            raise ValueError(f"Operational language is not allowed in sample quality promotion gate pack: {term}")


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(x) for x in row) + "|")
    return "\n".join(out)


def _staging_manifest_from_prior(root: Path) -> dict[str, Any]:
    prior = _load_json(root, "crypto_decision_lab/artifacts/phase10_offline_sample_intake_promotion_pack/phase10_offline_sample_intake_promotion_pack_index.json")
    manifest = _field(prior, "validated_staging_manifest", default={})
    if isinstance(manifest, dict) and manifest.get("entries"):
        return {
            "prior_present": bool(prior.get("_present")),
            "prior_gate_answer": prior.get("gate_answer", "MISSING"),
            "manifest": manifest,
        }

    manifest_path = root / "crypto_decision_lab" / "artifacts" / "phase10_offline_sample_intake_promotion_pack" / "validated_staging" / "validated_staging_manifest.json"
    try:
        return {
            "prior_present": bool(prior.get("_present")),
            "prior_gate_answer": prior.get("gate_answer", "MISSING"),
            "manifest": json.loads(manifest_path.read_text(encoding="utf-8")),
        }
    except Exception:
        return {
            "prior_present": bool(prior.get("_present")),
            "prior_gate_answer": prior.get("gate_answer", "MISSING"),
            "manifest": {"entries": []},
        }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
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


def _validate_row(row: dict[str, Any], idx: int) -> list[str]:
    errors = []
    for field in REQUIRED_FIELDS:
        if field not in row or row[field] in ("", None):
            errors.append(f"row{idx}:missing:{field}")
    nums = {}
    for field in NUMERIC_FIELDS:
        value = _as_float(row.get(field))
        if value is None:
            errors.append(f"row{idx}:not_number:{field}")
        else:
            nums[field] = value
    if all(k in nums for k in ("open", "high", "low", "close")):
        if nums["high"] < nums["low"]:
            errors.append(f"row{idx}:shape:high_lt_low")
        if nums["open"] < nums["low"] or nums["open"] > nums["high"]:
            errors.append(f"row{idx}:shape:open_outside_range")
        if nums["close"] < nums["low"] or nums["close"] > nums["high"]:
            errors.append(f"row{idx}:shape:close_outside_range")
    return errors


def _scan_staged_rows(root: Path, manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    all_rows: list[dict[str, Any]] = []
    file_summaries: list[dict[str, Any]] = []

    entries = manifest.get("entries", [])
    if not isinstance(entries, list):
        entries = []

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        raw_path = str(entry.get("staging_file") or "")
        path = Path(raw_path)
        if not path.is_absolute():
            path = root / raw_path
        rows = _read_jsonl(path)
        errors: list[str] = []
        for idx, row in enumerate(rows):
            errors.extend(_validate_row(row, idx))
        symbols = sorted({str(r.get("symbol")) for r in rows if r.get("symbol")})
        intervals = sorted({str(r.get("interval")) for r in rows if r.get("interval")})
        all_rows.extend(rows)
        file_summaries.append(
            {
                "path": str(path),
                "file_name": path.name,
                "present": path.exists(),
                "rows": len(rows),
                "errors": errors[:40],
                "error_count": len(errors),
                "symbols": symbols,
                "intervals": intervals,
                "sha256": _sha_file(path)[:16] if path.exists() else "MISSING",
                "ready": path.exists() and len(rows) > 0 and len(errors) == 0,
            }
        )
    return all_rows, file_summaries


def _quality_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    missing = Counter()
    invalid_numbers = Counter()
    shape_errors = 0
    timestamp_counts = Counter()
    symbol_interval_counts = Counter()
    row_hashes = Counter()
    rows_by_symbol = Counter()
    intervals_by_symbol: dict[str, set[str]] = defaultdict(set)

    for row in rows:
        for field in REQUIRED_FIELDS:
            if field not in row or row[field] in ("", None):
                missing[field] += 1
        for field in NUMERIC_FIELDS:
            if _as_float(row.get(field)) is None:
                invalid_numbers[field] += 1
        values = {k: _as_float(row.get(k)) for k in ("open", "high", "low", "close")}
        if all(v is not None for v in values.values()):
            if values["high"] < values["low"] or values["open"] < values["low"] or values["open"] > values["high"] or values["close"] < values["low"] or values["close"] > values["high"]:
                shape_errors += 1
        symbol = str(row.get("symbol", "UNKNOWN"))
        interval = str(row.get("interval", "UNKNOWN"))
        timestamp = str(row.get("timestamp", "UNKNOWN"))
        timestamp_counts[(symbol, interval, timestamp)] += 1
        symbol_interval_counts[(symbol, interval)] += 1
        rows_by_symbol[symbol] += 1
        intervals_by_symbol[symbol].add(interval)
        row_hashes[_sha_text(json.dumps(row, sort_keys=True, ensure_ascii=False))] += 1

    duplicate_symbol_timestamps = sum(count - 1 for count in timestamp_counts.values() if count > 1)
    duplicate_rows = sum(count - 1 for count in row_hashes.values() if count > 1)

    per_symbol = []
    for symbol, count in sorted(rows_by_symbol.items()):
        per_symbol.append(
            {
                "symbol": symbol,
                "rows": count,
                "intervals": sorted(intervals_by_symbol[symbol]),
                "sample_min_ready": count >= MIN_SAMPLE_ROWS_PER_SYMBOL,
                "full_depth_gap": max(TARGET_ROWS_PER_SYMBOL - count, 0),
                "full_depth_ready": count >= TARGET_ROWS_PER_SYMBOL,
            }
        )

    return {
        "total_rows": len(rows),
        "symbols_count": len(rows_by_symbol),
        "symbol_interval_groups": len(symbol_interval_counts),
        "missing_field_counts": dict(missing),
        "invalid_number_counts": dict(invalid_numbers),
        "shape_error_count": shape_errors,
        "duplicate_symbol_timestamps": duplicate_symbol_timestamps,
        "duplicate_rows": duplicate_rows,
        "per_symbol": per_symbol,
        "sample_quality_ready": (
            len(rows) > 0
            and not missing
            and not invalid_numbers
            and shape_errors == 0
            and duplicate_symbol_timestamps == 0
            and all(item["sample_min_ready"] for item in per_symbol)
        ),
        "full_depth_ready": all(item["full_depth_ready"] for item in per_symbol) if per_symbol else False,
    }


def _promotion_review(metrics: dict[str, Any], file_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    all_files_ready = bool(file_summaries) and all(f["ready"] for f in file_summaries)
    sample_quality_ready = bool(metrics.get("sample_quality_ready"))
    full_depth_ready = bool(metrics.get("full_depth_ready"))

    if all_files_ready and sample_quality_ready and not full_depth_ready:
        status = "SAMPLE_QUALITY_READY_FULL_DEPTH_BLOCKED_RESEARCH_ONLY"
        rationale = "Sample files pass artifact-stage quality checks, but row depth is far below the target needed for deeper research validation."
    elif all_files_ready and sample_quality_ready and full_depth_ready:
        status = "QUALITY_READY_PROMOTION_STILL_REVIEW_BLOCKED_RESEARCH_ONLY"
        rationale = "Quality checks pass, but canonical promotion remains blocked until explicit review and a separate promotion-safe apply gate."
    else:
        status = "QUALITY_REVIEW_REQUIRED_RESEARCH_ONLY"
        rationale = "One or more artifact-stage quality checks did not pass."

    return {
        "sample_quality_ready": sample_quality_ready,
        "full_depth_ready": full_depth_ready,
        "all_files_ready": all_files_ready,
        "promotion_allowed": False,
        "promotion_status": status,
        "promotion_rationale": rationale,
        "canonical_data_writes": 0,
    }


def _station(metrics: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    return {
        "where_we_are": "PHASE_10_SAMPLE_QUALITY_PROMOTION_GATE",
        "main_blocker": "Canonical promotion remains blocked; sample quality can pass while full dataset depth remains insufficient.",
        "next_best_step": "Feed larger offline/manual files through the inbox, rerun validation, and only then evaluate a separate canonical-promotion safe-apply gate.",
        "sample_quality_ready": review["sample_quality_ready"],
        "full_depth_ready": review["full_depth_ready"],
        "total_rows": metrics["total_rows"],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    file_rows = [
        [f["file_name"], f["present"], f["rows"], f["error_count"], f["ready"], ",".join(f["symbols"]), f["sha256"]]
        for f in payload["file_summaries"]
    ]
    symbol_rows = [
        [s["symbol"], s["rows"], ",".join(s["intervals"]), s["sample_min_ready"], s["full_depth_gap"], s["full_depth_ready"]]
        for s in payload["quality_metrics"]["per_symbol"]
    ]
    criteria_rows = [
        [c["criterion_id"], c["status"], c["ready"], c["observed"], c["threshold"], c["blocker"]]
        for c in payload["criteria"]
    ]

    md = f"""# QRDS/QOS Phase 10 Sample Quality / Promotion Gate Pack

This bundled pack computes artifact-stage sample quality metrics and keeps canonical promotion blocked.

**Gate answer:** {payload['gate_answer']}

**Policy lock:** {payload['policy_lock']} • **Mode:** {payload['app_mode']}

## Station

- Where we are: {payload['station']['where_we_are']}
- Main blocker: {payload['station']['main_blocker']}
- Next best step: {payload['station']['next_best_step']}

## Summary

- Prior sample pack present: {payload['prior_sample_pack_present']}
- Staging files checked: {payload['staging_files_checked']}
- Ready staging files: {payload['ready_staging_files']}
- Total staged rows: {payload['total_staged_rows']}
- Symbols: {payload['symbols_count']}
- Sample quality ready: {payload['sample_quality_ready']}
- Full depth ready: {payload['full_depth_ready']}
- Promotion allowed: {payload['promotion_allowed']}
- Promotion status: {payload['promotion_status']}
- Canonical data writes: {payload['canonical_data_writes']}
- Git status lines: {payload['git_status_line_count']}
- Criteria ready: {payload['criteria_ready_count']}/{payload['criteria_total_count']}
- Mean gate score: {payload['mean_gate_score']}

Safety lock remains active for account access, order flow, execution-style instructions, and live-fund workflow markers.

## Staging files

{_table(['file', 'present', 'rows', 'errors', 'ready', 'symbols', 'sha256'], file_rows or [['NONE', False, 0, 0, False, 'MISSING', 'MISSING']])}

## Per-symbol quality

{_table(['symbol', 'rows', 'intervals', 'sample_min_ready', 'full_depth_gap', 'full_depth_ready'], symbol_rows or [['NONE', 0, 'NONE', False, TARGET_ROWS_PER_SYMBOL, False]])}

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
        ("Staging files", payload["staging_files_checked"]),
        ("Ready files", payload["ready_staging_files"]),
        ("Rows", payload["total_staged_rows"]),
        ("Symbols", payload["symbols_count"]),
        ("Sample quality", payload["sample_quality_ready"]),
        ("Full depth", payload["full_depth_ready"]),
        ("Promotion allowed", payload["promotion_allowed"]),
        ("Canonical writes", payload["canonical_data_writes"]),
        ("Mean score", payload["mean_gate_score"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)

    file_rows = "".join(
        f"<tr><td>{esc(f['file_name'])}</td><td>{esc(f['present'])}</td><td>{esc(f['rows'])}</td><td>{esc(f['error_count'])}</td><td>{esc(f['ready'])}</td><td>{esc(','.join(f['symbols']))}</td><td>{esc(f['sha256'])}</td></tr>"
        for f in payload["file_summaries"]
    ) or "<tr><td>NONE</td><td>False</td><td>0</td><td>0</td><td>False</td><td>MISSING</td><td>MISSING</td></tr>"

    symbol_rows = "".join(
        f"<tr><td>{esc(s['symbol'])}</td><td>{esc(s['rows'])}</td><td>{esc(','.join(s['intervals']))}</td><td>{esc(s['sample_min_ready'])}</td><td>{esc(s['full_depth_gap'])}</td><td>{esc(s['full_depth_ready'])}</td></tr>"
        for s in payload["quality_metrics"]["per_symbol"]
    ) or f"<tr><td>NONE</td><td>0</td><td>NONE</td><td>False</td><td>{TARGET_ROWS_PER_SYMBOL}</td><td>False</td></tr>"

    criteria_rows = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td><td>{esc(c['blocker'])}</td></tr>"
        for c in payload["criteria"]
    )

    page = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>QRDS Phase 10 Sample Quality / Promotion Gate Pack</title>
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
<h2>Phase 10 Sample Quality / Promotion Gate Pack</h2>
<p>This bundled page computes sample quality metrics and keeps canonical promotion blocked. It cannot unlock operational use.</p>
<div class='card'>
<p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p>
<p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>
{card_html}
<p class='badge'>Research-only guardrail active</p>
<p class='blocked'>{esc(payload['promotion_status'])}</p>
<p>{esc(payload['promotion_rationale'])}</p>
</div>
<div class='station'>
<h2>Where we are</h2>
<p><b>{esc(payload['station']['where_we_are'])}</b></p>
<p>Main blocker: {esc(payload['station']['main_blocker'])}</p>
<p>Next best step: {esc(payload['station']['next_best_step'])}</p>
</div>
<h2>Staging files</h2>
<table><thead><tr><th>file</th><th>present</th><th>rows</th><th>errors</th><th>ready</th><th>symbols</th><th>sha256</th></tr></thead><tbody>{file_rows}</tbody></table>
<h2>Per-symbol quality</h2>
<table><thead><tr><th>symbol</th><th>rows</th><th>intervals</th><th>sample_min_ready</th><th>full_depth_gap</th><th>full_depth_ready</th></tr></thead><tbody>{symbol_rows}</tbody></table>
<h2>Criteria</h2>
<table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th><th>blocker</th></tr></thead><tbody>{criteria_rows}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p>
</body></html>"""
    _assert_research_only(page)
    return page


def build_phase10_sample_quality_promotion_gate_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    prior = _staging_manifest_from_prior(root)
    rows, file_summaries = _scan_staged_rows(root, prior["manifest"])
    metrics = _quality_metrics(rows)
    review = _promotion_review(metrics, file_summaries)
    station = _station(metrics, review)
    git_status = _git_status(root)

    ready_files = sum(1 for f in file_summaries if f["ready"])

    criteria = [
        _criterion("prior_sample_pack_present", "PASS" if prior["prior_present"] else "FAIL", prior["prior_present"], prior["prior_gate_answer"], "10I-10N sample pack present", ""),
        _criterion("staging_files_found", "PASS" if file_summaries else "FAIL", bool(file_summaries), len(file_summaries), "> 0 staging files", ""),
        _criterion("staging_files_ready", "PASS" if file_summaries and ready_files == len(file_summaries) else "FAIL", bool(file_summaries) and ready_files == len(file_summaries), f"{ready_files}/{len(file_summaries)}", "all staging files ready", ""),
        _criterion("sample_quality_ready", "PASS" if review["sample_quality_ready"] else "FAIL", review["sample_quality_ready"], review["sample_quality_ready"], "sample quality checks pass", ""),
        _criterion("full_depth_explicitly_blocked", "PASS" if not review["full_depth_ready"] else "WARN", not review["full_depth_ready"], review["full_depth_ready"], "full depth should remain explicit at sample stage", ""),
        _criterion("promotion_blocked", "PASS" if not review["promotion_allowed"] else "FAIL", not review["promotion_allowed"], review["promotion_allowed"], "promotion_allowed false", ""),
        _criterion("artifact_only", "PASS" if review["canonical_data_writes"] == 0 else "FAIL", review["canonical_data_writes"] == 0, review["canonical_data_writes"], "0 canonical data writes", ""),
        _criterion("station_created", "PASS", True, station["where_we_are"], "station status present", ""),
        _criterion("research_only_lock", "PASS", True, "ACTIVE", "policy lock active", ""),
    ]

    ready_count = sum(1 for c in criteria if c["ready"])
    mean_score = round(ready_count / len(criteria), 4)

    if prior["prior_present"] and file_summaries and review["sample_quality_ready"] and not review["promotion_allowed"]:
        gate_answer = "PHASE10_SAMPLE_QUALITY_PROMOTION_GATE_READY_BLOCKED_RESEARCH_ONLY"
    else:
        gate_answer = "PHASE10_SAMPLE_QUALITY_PROMOTION_GATE_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.phase10_sample_quality_promotion_gate_pack.v1",
        "report_name": "qrds-phase10-sample-quality-promotion-gate-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": station,
        "prior_sample_pack_present": prior["prior_present"],
        "prior_sample_gate_answer": prior["prior_gate_answer"],
        "staging_files_checked": len(file_summaries),
        "ready_staging_files": ready_files,
        "total_staged_rows": metrics["total_rows"],
        "symbols_count": metrics["symbols_count"],
        "sample_quality_ready": review["sample_quality_ready"],
        "full_depth_ready": review["full_depth_ready"],
        "promotion_allowed": review["promotion_allowed"],
        "promotion_status": review["promotion_status"],
        "promotion_rationale": review["promotion_rationale"],
        "canonical_data_writes": review["canonical_data_writes"],
        "file_summaries": file_summaries,
        "quality_metrics": metrics,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_gate_score": mean_score,
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    report_path = out / "phase10_sample_quality_promotion_gate_pack.json"
    md_path = out / "phase10_sample_quality_promotion_gate_pack.md"
    html_path = out / "index.html"
    index_path = out / "phase10_sample_quality_promotion_gate_pack_index.json"

    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    index = {
        "schema": "qrds.phase10_sample_quality_promotion_gate_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "station": payload["station"]["where_we_are"],
        "prior_sample_pack_present": payload["prior_sample_pack_present"],
        "staging_files_checked": payload["staging_files_checked"],
        "ready_staging_files": payload["ready_staging_files"],
        "total_staged_rows": payload["total_staged_rows"],
        "symbols_count": payload["symbols_count"],
        "sample_quality_ready": payload["sample_quality_ready"],
        "full_depth_ready": payload["full_depth_ready"],
        "promotion_allowed": payload["promotion_allowed"],
        "promotion_status": payload["promotion_status"],
        "canonical_data_writes": payload["canonical_data_writes"],
        "git_status_line_count": payload["git_status_line_count"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_gate_score": payload["mean_gate_score"],
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


build_sample_quality_pack = build_phase10_sample_quality_promotion_gate_pack
