from __future__ import annotations

import csv
import hashlib
import html
import json
import math
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
    "position sizing",
    "use real capital",
    "execute trade",
    "trading signal:",
    "buy signal",
    "sell signal",
)

CANONICAL_DATA_ROOT = "crypto_decision_lab/data"
ALLOWED_DATA_PREFIXES = (
    "crypto_decision_lab/data/fixtures/",
    "crypto_decision_lab/data/research/",
    "crypto_decision_lab/data/canonical/",
    "crypto_decision_lab/data/raw/",
    "crypto_decision_lab/data/validated/",
)
REJECTED_PATH_PARTS = {"artifacts", "docs", "tests", "__pycache__", ".git", ".pytest_cache"}
DATA_EXTENSIONS = {".json", ".jsonl", ".csv"}
REQUIRED_BAR_FIELDS = ("timestamp", "open", "high", "low", "close", "volume")
REQUIRED_METADATA_FIELDS = ("symbol", "interval", "source")
ALLOWED_INTERVALS = ("1m", "5m", "15m", "30m", "1h", "4h", "1d")
MIN_SAMPLE_ROWS_FOR_CONTRACT = 1


def _repo_root() -> Path:
    here = Path.cwd().resolve()
    for p in [here, *here.parents]:
        if (p / "crypto_decision_lab").exists():
            return p
    return here


def _symbols(symbols: str | Iterable[str]) -> list[str]:
    if isinstance(symbols, str):
        return [s.strip() for s in symbols.split(",") if s.strip()]
    return [str(s).strip() for s in symbols if str(s).strip()]


def _symbol_tokens(symbol: str) -> set[str]:
    low = symbol.lower()
    return {low, low.replace("-", "_"), low.replace("-", ""), low.replace("_", "-")}


def _file_symbol(path: Path, symbols: list[str]) -> str | None:
    low = str(path).lower()
    for symbol in symbols:
        if any(token in low for token in _symbol_tokens(symbol)):
            return symbol
    return None


def _path_is_allowed(path: Path, root: Path) -> tuple[bool, str]:
    try:
        rel = str(path.resolve().relative_to(root)).replace("\\", "/")
    except Exception:
        rel = str(path).replace("\\", "/")

    parts = set(Path(rel).parts)
    if parts.intersection(REJECTED_PATH_PARTS):
        return False, "REJECTED_PATH_PART"
    if not any(rel.startswith(prefix) for prefix in ALLOWED_DATA_PREFIXES):
        return False, "OUTSIDE_ALLOWED_DATA_PREFIX"
    if path.suffix.lower() not in DATA_EXTENSIONS:
        return False, "UNSUPPORTED_EXTENSION"
    return True, "ALLOWED"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _candidate_rows_from_obj(obj: Any) -> list[Any]:
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for key in ("candles", "klines", "rows", "records", "items", "data", "bars", "ohlcv", "prices"):
            value = obj.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                nested = _candidate_rows_from_obj(value)
                if nested:
                    return nested
        payload = obj.get("payload")
        if isinstance(payload, (dict, list)):
            nested = _candidate_rows_from_obj(payload)
            if nested:
                return nested
        # OKX fixture style may have a single `bar` object.
        bar = obj.get("bar")
        if isinstance(bar, dict):
            return [bar]
    return []


def _metadata_from_obj(obj: Any, path: Path, symbol_hint: str | None) -> dict[str, Any]:
    if not isinstance(obj, dict):
        return {"symbol": symbol_hint or "UNKNOWN", "interval": "UNKNOWN", "source": "UNKNOWN"}
    payload = obj.get("payload") if isinstance(obj.get("payload"), dict) else {}
    symbol = obj.get("symbol") or obj.get("instId") or payload.get("symbol") or payload.get("instId") or symbol_hint or "UNKNOWN"
    interval = obj.get("interval") or obj.get("timeframe") or obj.get("bar") or payload.get("interval") or payload.get("timeframe") or "UNKNOWN"
    source = obj.get("source") or payload.get("source") or "UNKNOWN"
    return {"symbol": str(symbol), "interval": str(interval), "source": str(source)}


def _coerce_number(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        x = float(value)
        if math.isnan(x) or math.isinf(x):
            return None
        return x
    except Exception:
        return None


def _normalize_bar(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        ts = row.get("timestamp") or row.get("time") or row.get("ts") or row.get("datetime") or row.get("date")
        return {
            "timestamp": ts,
            "open": row.get("open") or row.get("o"),
            "high": row.get("high") or row.get("h"),
            "low": row.get("low") or row.get("l"),
            "close": row.get("close") or row.get("c"),
            "volume": row.get("volume") or row.get("vol") or row.get("v"),
        }
    if isinstance(row, (list, tuple)) and len(row) >= 6:
        return {
            "timestamp": row[0],
            "open": row[1],
            "high": row[2],
            "low": row[3],
            "close": row[4],
            "volume": row[5],
        }
    return {k: None for k in REQUIRED_BAR_FIELDS}


def _read_rows_and_metadata(path: Path, symbol_hint: str | None) -> tuple[list[Any], dict[str, Any], str]:
    suffix = path.suffix.lower()
    try:
        if suffix == ".json":
            obj = _read_json(path)
            return _candidate_rows_from_obj(obj), _metadata_from_obj(obj, path, symbol_hint), "READABLE"
        if suffix == ".jsonl":
            rows = []
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        rows.append(json.loads(line))
            return rows, {"symbol": symbol_hint or "UNKNOWN", "interval": "UNKNOWN", "source": "JSONL"}, "READABLE"
        if suffix == ".csv":
            with path.open("r", encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
            return rows, {"symbol": symbol_hint or "UNKNOWN", "interval": "UNKNOWN", "source": "CSV"}, "READABLE"
    except Exception as exc:
        return [], {"symbol": symbol_hint or "UNKNOWN", "interval": "UNKNOWN", "source": "UNKNOWN"}, f"UNREADABLE:{type(exc).__name__}"
    return [], {"symbol": symbol_hint or "UNKNOWN", "interval": "UNKNOWN", "source": "UNKNOWN"}, "UNSUPPORTED"


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return "UNREADABLE"


def _validate_file(path: Path, root: Path, symbols: list[str]) -> dict[str, Any]:
    symbol_hint = _file_symbol(path, symbols)
    allowed, path_status = _path_is_allowed(path, root)
    rel = str(path.resolve().relative_to(root)).replace("\\", "/") if path.exists() else str(path).replace("\\", "/")

    rows, metadata, read_status = _read_rows_and_metadata(path, symbol_hint)
    sample = rows[:50]
    normalized = [_normalize_bar(r) for r in sample]

    row_count = len(rows)
    missing_field_counts = {field: 0 for field in REQUIRED_BAR_FIELDS}
    numeric_fail_counts = {field: 0 for field in ("open", "high", "low", "close", "volume")}
    timestamp_present_count = 0

    for bar in normalized:
        if bar.get("timestamp") not in (None, ""):
            timestamp_present_count += 1
        for field in REQUIRED_BAR_FIELDS:
            if bar.get(field) in (None, ""):
                missing_field_counts[field] += 1
        for field in numeric_fail_counts:
            if _coerce_number(bar.get(field)) is None:
                numeric_fail_counts[field] += 1

    required_metadata_present = all(str(metadata.get(k) or "UNKNOWN") != "UNKNOWN" for k in REQUIRED_METADATA_FIELDS)
    symbol_match = bool(symbol_hint) and symbol_hint.replace("-", "").lower() in str(metadata.get("symbol", "")).replace("-", "").replace("_", "").lower()
    interval_known = str(metadata.get("interval", "UNKNOWN")) in ALLOWED_INTERVALS or str(metadata.get("interval", "UNKNOWN")) != "UNKNOWN"

    sample_rows_present = row_count >= MIN_SAMPLE_ROWS_FOR_CONTRACT
    required_fields_present = bool(normalized) and all(missing_field_counts[field] == 0 for field in REQUIRED_BAR_FIELDS)
    numeric_fields_valid = bool(normalized) and all(numeric_fail_counts[field] == 0 for field in numeric_fail_counts)
    timestamp_present = bool(normalized) and timestamp_present_count == len(normalized)

    contract_ready = bool(
        allowed
        and read_status == "READABLE"
        and sample_rows_present
        and required_fields_present
        and numeric_fields_valid
        and timestamp_present
        and required_metadata_present
    )

    if contract_ready:
        status = "CONTRACT_READY"
    elif not allowed:
        status = path_status
    elif read_status != "READABLE":
        status = read_status
    else:
        status = "CONTRACT_GAPS"

    return {
        "path": rel,
        "symbol_hint": symbol_hint or "UNKNOWN",
        "metadata_symbol": metadata.get("symbol", "UNKNOWN"),
        "metadata_interval": metadata.get("interval", "UNKNOWN"),
        "metadata_source": metadata.get("source", "UNKNOWN"),
        "row_count": row_count,
        "sample_size": len(normalized),
        "status": status,
        "contract_ready": contract_ready,
        "path_allowed": allowed,
        "path_status": path_status,
        "read_status": read_status,
        "required_metadata_present": required_metadata_present,
        "symbol_match": symbol_match,
        "interval_known": interval_known,
        "timestamp_present": timestamp_present,
        "required_fields_present": required_fields_present,
        "numeric_fields_valid": numeric_fields_valid,
        "missing_field_counts": missing_field_counts,
        "numeric_fail_counts": numeric_fail_counts,
        "sha256": _sha_file(path)[:16],
    }


def _discover_dataset_files(symbols: list[str]) -> list[Path]:
    root = _repo_root()
    data_root = root / CANONICAL_DATA_ROOT
    if not data_root.exists():
        return []
    paths: list[Path] = []
    for path in sorted(data_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in DATA_EXTENSIONS:
            continue
        allowed, _ = _path_is_allowed(path, root)
        if not allowed:
            continue
        if _file_symbol(path, symbols) is None:
            continue
        paths.append(path)
    return paths


def _load_reports(reports: Iterable[str | Path] | None) -> list[dict[str, Any]]:
    if not reports:
        return []
    root = _repo_root()
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in reports:
        raw = str(item).strip()
        if not raw:
            continue
        candidates = [Path(raw), root / raw]
        if raw.startswith("crypto_decision_lab/"):
            candidates.append(root / raw)
            candidates.append(root / "crypto_decision_lab" / raw.split("/", 1)[1])
        resolved = next((c for c in candidates if c.exists()), Path(raw))
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        try:
            payload = json.loads(resolved.read_text(encoding="utf-8")) if resolved.exists() else {}
            nested = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
            rows.append({
                "path": key,
                "status": "REPORT_PRESENT" if resolved.exists() else "MISSING_FILE",
                "report_name": payload.get("report_name") or nested.get("report_name") or resolved.stem,
                "gate_answer": payload.get("gate_answer") or nested.get("gate_answer") or "UNKNOWN_RESEARCH_ONLY",
            })
        except Exception:
            rows.append({"path": key, "status": "UNREADABLE", "report_name": Path(raw).stem, "gate_answer": "UNREADABLE_RESEARCH_ONLY"})
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


def _sha_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _assert_research_only(rendered: str) -> None:
    low = rendered.lower()
    for term in FORBIDDEN_RENDERED_PHRASES:
        if term in low:
            raise ValueError(f"Operational language is not allowed in Data Source Contract: {term}")


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(x) for x in row) + "|")
    return "\n".join(out)


def _contract_spec() -> dict[str, Any]:
    return {
        "schema_name": "qrds.canonical_bar_dataset.v1",
        "allowed_extensions": sorted(DATA_EXTENSIONS),
        "allowed_prefixes": list(ALLOWED_DATA_PREFIXES),
        "rejected_path_parts": sorted(REJECTED_PATH_PARTS),
        "required_metadata_fields": list(REQUIRED_METADATA_FIELDS),
        "required_bar_fields": list(REQUIRED_BAR_FIELDS),
        "allowed_intervals": list(ALLOWED_INTERVALS),
        "field_types": {
            "symbol": "string, normalized like BTC-USDT",
            "interval": "string, e.g. 1h",
            "source": "string, data origin label",
            "timestamp": "ISO-8601 string or millisecond epoch; must be monotonic after validation stage",
            "open": "numeric",
            "high": "numeric",
            "low": "numeric",
            "close": "numeric",
            "volume": "numeric",
        },
        "research_only_scope": "Dataset contract and validation evidence only; no live-market connection or operational output.",
    }


def render_markdown(payload: dict[str, Any]) -> str:
    spec = payload["contract_spec"]
    file_rows = [
        [r["symbol_hint"], r["status"], r["contract_ready"], r["row_count"], r["metadata_interval"], r["metadata_source"], r["path"]]
        for r in payload["validated_files"][:80]
    ] or [["NONE", "MISSING", False, 0, "UNKNOWN", "UNKNOWN", "MISSING"]]
    criteria_rows = [[c["criterion_id"], c["status"], c["ready"], c["observed"], c["threshold"], c["blocker"]] for c in payload["criteria"]]
    flag_rows = [[k, v] for k, v in payload["safety_flags"].items()]

    md = f"""# QRDS/QOS • Gate BTC • Research-only
## Data Source Contract / Canonical Schema Pack

Formal source and schema contract for research datasets. This artifact defines what a dataset must look like before depth expansion. It cannot unlock operational use.

**Gate answer:** {payload['gate_answer']}

**Policy lock:** {payload['policy_lock']} • **Mode:** {payload['app_mode']}

## Summary

- Input reports: {payload['input_report_count']}
- Dataset files checked: {payload['dataset_file_count']}
- Contract-ready files: {payload['contract_ready_file_count']}
- Symbols with contract-ready files: {payload['symbols_contract_ready']}/{len(payload['symbols'])}
- Total observed rows: {payload['total_rows']}
- Criteria ready: {payload['criteria_ready_count']}/{payload['criteria_total_count']}
- Mean contract score: {payload['mean_contract_score']}
- High priority gaps: {payload['high_priority_gap_count']}

Research-only guardrail: no exchange account, no orders, no portfolio allocation output, no executable instruction, no live-fund workflow.

## Canonical schema

- Schema name: `{spec['schema_name']}`
- Allowed prefixes: `{', '.join(spec['allowed_prefixes'])}`
- Allowed extensions: `{', '.join(spec['allowed_extensions'])}`
- Required metadata fields: `{', '.join(spec['required_metadata_fields'])}`
- Required bar fields: `{', '.join(spec['required_bar_fields'])}`
- Allowed intervals: `{', '.join(spec['allowed_intervals'])}`

## Criteria

{_table(['criterion_id', 'status', 'ready', 'observed', 'threshold', 'blocker'], criteria_rows)}

## Checked dataset files

{_table(['symbol', 'status', 'ready', 'rows', 'interval', 'source', 'path'], file_rows)}

## Safety flags

{_table(['flag', 'value'], flag_rows)}

Generated at {payload['generated_at']} • SHA256 {payload['report_payload_sha256']}
"""
    _assert_research_only(md)
    return md


def render_html(payload: dict[str, Any]) -> str:
    def esc(x: Any) -> str:
        return html.escape(str(x))

    spec = payload["contract_spec"]
    criteria_rows = "\n".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td><td>{esc(c['blocker'])}</td></tr>"
        for c in payload["criteria"]
    )
    file_rows = "\n".join(
        f"<tr><td>{esc(r['symbol_hint'])}</td><td>{esc(r['status'])}</td><td>{esc(r['contract_ready'])}</td><td>{esc(r['row_count'])}</td><td>{esc(r['metadata_interval'])}</td><td>{esc(r['metadata_source'])}</td><td>{esc(r['path'])}</td></tr>"
        for r in payload["validated_files"][:120]
    ) or "<tr><td>NONE</td><td>MISSING</td><td>False</td><td>0</td><td>UNKNOWN</td><td>UNKNOWN</td><td>MISSING</td></tr>"
    flag_rows = "\n".join(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>" for k, v in payload["safety_flags"].items())

    page = f"""<!doctype html><html><head><meta charset='utf-8'><title>QRDS Data Source Contract</title>
<style>
body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}
.card{{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}}
.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px 8px 8px 0}}
table{{border-collapse:collapse;width:100%;background:white;margin:12px 0}}
th,td{{border:1px solid #d9deea;padding:8px;text-align:left;font-size:14px;vertical-align:top}}
th{{background:#eef2ff}}
.badge{{display:inline-block;background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}}
code{{background:#eef2ff;padding:2px 5px;border-radius:5px}}
</style></head><body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1>
<h2>Data Source Contract / Canonical Schema Pack</h2>
<p>Formal source and schema contract for research datasets. This artifact defines what a dataset must look like before depth expansion. It cannot unlock operational use.</p>
<div class='card'>
<p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p>
<p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>
<div class='kpi'><b>Input reports</b><br>{esc(payload['input_report_count'])}</div>
<div class='kpi'><b>Dataset files checked</b><br>{esc(payload['dataset_file_count'])}</div>
<div class='kpi'><b>Contract-ready files</b><br>{esc(payload['contract_ready_file_count'])}</div>
<div class='kpi'><b>Symbols ready</b><br>{esc(payload['symbols_contract_ready'])}/{esc(len(payload['symbols']))}</div>
<div class='kpi'><b>Total rows</b><br>{esc(payload['total_rows'])}</div>
<div class='kpi'><b>Criteria ready</b><br>{esc(payload['criteria_ready_count'])}/{esc(payload['criteria_total_count'])}</div>
<div class='kpi'><b>Mean contract score</b><br>{esc(payload['mean_contract_score'])}</div>
<div class='kpi'><b>High priority gaps</b><br>{esc(payload['high_priority_gap_count'])}</div>
<p class='badge'>Research-only guardrail active</p>
<p>No exchange account, no orders, no portfolio allocation output, no executable instruction, no live-fund workflow.</p>
</div>
<h2>Canonical schema</h2>
<div class='card'>
<p><b>Schema:</b> <code>{esc(spec['schema_name'])}</code></p>
<p><b>Allowed prefixes:</b> {esc(', '.join(spec['allowed_prefixes']))}</p>
<p><b>Allowed extensions:</b> {esc(', '.join(spec['allowed_extensions']))}</p>
<p><b>Required metadata:</b> {esc(', '.join(spec['required_metadata_fields']))}</p>
<p><b>Required bar fields:</b> {esc(', '.join(spec['required_bar_fields']))}</p>
</div>
<h2>Criteria</h2><table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th><th>blocker</th></tr></thead><tbody>{criteria_rows}</tbody></table>
<h2>Checked dataset files</h2><table><thead><tr><th>symbol</th><th>status</th><th>ready</th><th>rows</th><th>interval</th><th>source</th><th>path</th></tr></thead><tbody>{file_rows}</tbody></table>
<h2>Safety flags</h2><table><thead><tr><th>flag</th><th>value</th></tr></thead><tbody>{flag_rows}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p>
</body></html>"""
    _assert_research_only(page)
    return page


def build_data_source_contract(
    output_dir: str | Path,
    symbols: str | Iterable[str] = "BTC-USDT,ETH-USDT,SOL-USDT",
    reports: Iterable[str | Path] | None = None,
    max_files: int = 300,
    **_: Any,
) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    symbol_list = _symbols(symbols)
    input_reports = _load_reports(reports)
    root = _repo_root()
    files = _discover_dataset_files(symbol_list)[:max_files]
    validated = [_validate_file(path, root, symbol_list) for path in files]

    total_rows = sum(int(r.get("row_count") or 0) for r in validated)
    ready_files = [r for r in validated if r.get("contract_ready")]
    symbols_ready_set = {str(r.get("symbol_hint")) for r in ready_files if str(r.get("symbol_hint")) != "UNKNOWN"}
    high_priority_gaps = 0

    path_scope_ready = all(r.get("path_allowed") for r in validated) if validated else False
    readable_ready = all(r.get("read_status") == "READABLE" for r in validated) if validated else False
    metadata_ready = all(r.get("required_metadata_present") for r in validated) if validated else False
    required_fields_ready = all(r.get("required_fields_present") for r in validated) if validated else False
    numeric_ready = all(r.get("numeric_fields_valid") for r in validated) if validated else False
    timestamp_ready = all(r.get("timestamp_present") for r in validated) if validated else False
    symbol_coverage_ready = len(symbols_ready_set) == len(symbol_list)

    criteria = [
        _criterion("allowed_path_scope", "PASS" if path_scope_ready else "FAIL", path_scope_ready, f"{sum(1 for r in validated if r.get('path_allowed'))}/{len(validated)}", f"all files under allowed {CANONICAL_DATA_ROOT} prefixes", "" if path_scope_ready else "Reject or move files outside canonical data prefixes."),
        _criterion("readable_dataset_files", "PASS" if readable_ready else "FAIL", readable_ready, f"{sum(1 for r in validated if r.get('read_status') == 'READABLE')}/{len(validated)}", "all checked files readable", "" if readable_ready else "Unreadable files must be repaired or excluded."),
        _criterion("metadata_contract", "PASS" if metadata_ready else "FAIL", metadata_ready, f"{sum(1 for r in validated if r.get('required_metadata_present'))}/{len(validated)}", "symbol, interval, source present", "" if metadata_ready else "Metadata fields must be explicit."),
        _criterion("bar_field_contract", "PASS" if required_fields_ready else "FAIL", required_fields_ready, f"{sum(1 for r in validated if r.get('required_fields_present'))}/{len(validated)}", "timestamp, open, high, low, close, volume present in sample", "" if required_fields_ready else "Bar/candle fields must match canonical schema."),
        _criterion("numeric_field_contract", "PASS" if numeric_ready else "FAIL", numeric_ready, f"{sum(1 for r in validated if r.get('numeric_fields_valid'))}/{len(validated)}", "open/high/low/close/volume numeric in sample", "" if numeric_ready else "Numeric fields must be parseable."),
        _criterion("timestamp_contract", "PASS" if timestamp_ready else "FAIL", timestamp_ready, f"{sum(1 for r in validated if r.get('timestamp_present'))}/{len(validated)}", "timestamp present in sample", "" if timestamp_ready else "Timestamp evidence must be explicit."),
        _criterion("symbol_contract_coverage", "PASS" if symbol_coverage_ready else "FAIL", symbol_coverage_ready, f"{len(symbols_ready_set)}/{len(symbol_list)}", "all requested symbols have contract-ready files", "" if symbol_coverage_ready else "Every requested symbol needs at least one contract-ready dataset file."),
        _criterion("research_only_lock", "PASS", True, "ACTIVE", "policy lock active", ""),
    ]

    high_priority_gaps = sum(1 for c in criteria if c["status"] == "FAIL")
    ready_count = sum(1 for c in criteria if c["ready"])
    mean_score = round(ready_count / len(criteria), 4)

    if not validated:
        gate_answer = "NO_DATA_SOURCE_CONTRACT_FILES_FOUND_RESEARCH_ONLY"
    elif high_priority_gaps > 0:
        gate_answer = "DATA_SOURCE_CONTRACT_CREATED_WITH_SCHEMA_GAPS_RESEARCH_ONLY"
    else:
        gate_answer = "DATA_SOURCE_CONTRACT_CREATED_SCHEMA_READY_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.data_source_contract.v1",
        "report_name": "qrds-data-source-contract",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "symbols": symbol_list,
        "input_report_count": len(input_reports),
        "input_reports": input_reports,
        "dataset_file_count": len(validated),
        "contract_ready_file_count": len(ready_files),
        "symbols_contract_ready": len(symbols_ready_set),
        "total_rows": total_rows,
        "high_priority_gap_count": high_priority_gaps,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_contract_score": mean_score,
        "criteria": criteria,
        "contract_spec": _contract_spec(),
        "validated_files": validated,
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    report_path = out / "data_source_contract.json"
    markdown_path = out / "data_source_contract.md"
    html_path = out / "index.html"
    index_path = out / "data_source_contract_index.json"

    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    index = {
        "schema": "qrds.data_source_contract_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "symbols": payload["symbols"],
        "input_report_count": payload["input_report_count"],
        "dataset_file_count": payload["dataset_file_count"],
        "contract_ready_file_count": payload["contract_ready_file_count"],
        "symbols_contract_ready": payload["symbols_contract_ready"],
        "total_rows": payload["total_rows"],
        "high_priority_gap_count": payload["high_priority_gap_count"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_contract_score": payload["mean_contract_score"],
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


build_data_source_contract_pack = build_data_source_contract
