from __future__ import annotations

import csv
import hashlib
import html
import json
import os
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
    "recommended allocation",
)

STRUCTURED_SUFFIXES = {".csv", ".json", ".jsonl", ".ndjson"}
TIME_COLUMNS = ("timestamp", "time", "datetime", "date", "open_time", "close_time", "ts")

DEFAULT_SCAN_ROOTS = (
    "crypto_decision_lab/data",
    "crypto_decision_lab/fixtures",
    "crypto_decision_lab/tests/fixtures",
    "crypto_decision_lab/artifacts",
    "data",
    "fixtures",
    "artifacts",
)


def _symbols(symbols: str | Iterable[str]) -> list[str]:
    if isinstance(symbols, str):
        values = [s.strip() for s in symbols.split(",") if s.strip()]
    else:
        values = [str(s).strip() for s in symbols if str(s).strip()]
    return values or ["BTC-USDT", "ETH-USDT", "SOL-USDT"]


def _symbol_tokens(symbol: str) -> set[str]:
    base = symbol.lower()
    compact = base.replace("-", "").replace("_", "").replace("/", "")
    underscored = base.replace("-", "_").replace("/", "_")
    dashed = base.replace("_", "-").replace("/", "-")
    slash = base.replace("-", "/").replace("_", "/")
    return {base, compact, underscored, dashed, slash}


def _split_roots(scan_roots: str | Iterable[str] | None) -> list[Path]:
    if scan_roots is None:
        raw = list(DEFAULT_SCAN_ROOTS)
    elif isinstance(scan_roots, str):
        raw = [x.strip() for x in scan_roots.split(",") if x.strip()]
    else:
        raw = [str(x).strip() for x in scan_roots if str(x).strip()]
    roots: list[Path] = []
    for item in raw:
        p = Path(item)
        candidates = [p, Path.cwd() / p, Path.cwd().parent / p]
        for c in candidates:
            if c.exists() and c.is_dir():
                rp = c.resolve()
                if rp not in roots:
                    roots.append(rp)
                break
    return roots


def _file_sha256(path: Path, max_bytes: int = 8_000_000) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        remaining = max_bytes
        while remaining > 0:
            chunk = fh.read(min(1024 * 1024, remaining))
            if not chunk:
                break
            h.update(chunk)
            remaining -= len(chunk)
    return h.hexdigest()


def _safe_read_json_rows(path: Path, max_rows: int) -> tuple[int, list[dict[str, Any]], str]:
    try:
        text = path.read_text(encoding="utf-8")
        parsed = json.loads(text)
        if isinstance(parsed, list):
            rows = [x for x in parsed[:max_rows] if isinstance(x, dict)]
            return len(parsed), rows, ""
        if isinstance(parsed, dict):
            # Prefer common container keys; otherwise treat the dict as one row.
            for key in ("rows", "data", "records", "candles", "items"):
                value = parsed.get(key)
                if isinstance(value, list):
                    rows = [x for x in value[:max_rows] if isinstance(x, dict)]
                    return len(value), rows, ""
            return 1, [parsed], ""
        return 0, [], "json_root_not_tabular"
    except Exception as exc:
        return 0, [], f"json_read_error:{type(exc).__name__}"


def _safe_read_jsonl_rows(path: Path, max_rows: int) -> tuple[int, list[dict[str, Any]], str]:
    rows: list[dict[str, Any]] = []
    count = 0
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                count += 1
                if len(rows) < max_rows:
                    try:
                        obj = json.loads(line)
                        if isinstance(obj, dict):
                            rows.append(obj)
                    except Exception:
                        pass
        return count, rows, ""
    except Exception as exc:
        return count, rows, f"jsonl_read_error:{type(exc).__name__}"


def _safe_read_csv_rows(path: Path, max_rows: int) -> tuple[int, list[dict[str, Any]], str]:
    rows: list[dict[str, Any]] = []
    count = 0
    try:
        with path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                count += 1
                if len(rows) < max_rows:
                    rows.append(dict(row))
        return count, rows, ""
    except UnicodeDecodeError:
        try:
            with path.open("r", encoding="latin-1", newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    count += 1
                    if len(rows) < max_rows:
                        rows.append(dict(row))
            return count, rows, ""
        except Exception as exc:
            return count, rows, f"csv_read_error:{type(exc).__name__}"
    except Exception as exc:
        return count, rows, f"csv_read_error:{type(exc).__name__}"


def _infer_time_column(rows: list[dict[str, Any]]) -> str | None:
    if not rows:
        return None
    keys = {str(k).lower(): str(k) for row in rows[:20] for k in row.keys()}
    for name in TIME_COLUMNS:
        if name in keys:
            return keys[name]
    for lower, original in keys.items():
        if "time" in lower or "date" in lower:
            return original
    return None


def _parse_time_value(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        num = float(value)
        if num > 10_000_000_000:  # ms
            return num / 1000.0
        return num
    raw = str(value).strip()
    if not raw:
        return None
    try:
        num = float(raw)
        if num > 10_000_000_000:
            return num / 1000.0
        return num
    except Exception:
        pass
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def _profile_rows(path: Path, max_rows: int = 5000) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        row_count, rows, error = _safe_read_csv_rows(path, max_rows)
    elif suffix == ".json":
        row_count, rows, error = _safe_read_json_rows(path, max_rows)
    elif suffix in {".jsonl", ".ndjson"}:
        row_count, rows, error = _safe_read_jsonl_rows(path, max_rows)
    else:
        row_count, rows, error = 0, [], "unsupported_suffix"

    sample_count = len(rows)
    columns = sorted({str(k) for row in rows for k in row.keys()})
    cell_count = sample_count * len(columns) if columns else 0
    null_count = 0
    seen: set[str] = set()
    duplicate_sample_count = 0
    for row in rows:
        null_count += sum(1 for v in row.values() if v is None or v == "")
        fingerprint = json.dumps(row, sort_keys=True, ensure_ascii=False)
        if fingerprint in seen:
            duplicate_sample_count += 1
        seen.add(fingerprint)

    time_column = _infer_time_column(rows)
    time_values = []
    if time_column:
        for row in rows:
            parsed = _parse_time_value(row.get(time_column))
            if parsed is not None:
                time_values.append(parsed)
    time_values_sorted = sorted(time_values)
    gap_count = 0
    if len(time_values_sorted) >= 3:
        deltas = [b - a for a, b in zip(time_values_sorted, time_values_sorted[1:]) if b >= a]
        if deltas:
            median = sorted(deltas)[len(deltas) // 2]
            if median > 0:
                gap_count = sum(1 for d in deltas if d > median * 2.5)

    return {
        "row_count": row_count,
        "sampled_rows": sample_count,
        "column_count": len(columns),
        "columns": columns[:50],
        "null_count_sample": null_count,
        "cell_count_sample": cell_count,
        "null_rate_sample": round(null_count / cell_count, 6) if cell_count else 0.0,
        "duplicate_rows_sample": duplicate_sample_count,
        "time_column": time_column or "MISSING",
        "time_values_sample": len(time_values),
        "time_gap_count_sample": gap_count,
        "read_error": error,
    }


def discover_dataset_files(symbols: list[str], scan_roots: str | Iterable[str] | None = None) -> dict[str, list[Path]]:
    roots = _split_roots(scan_roots)
    by_symbol: dict[str, list[Path]] = {s: [] for s in symbols}
    for root in roots:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in STRUCTURED_SUFFIXES:
                continue
            low_path = str(path).lower()
            for symbol in symbols:
                if any(token in low_path for token in _symbol_tokens(symbol)):
                    by_symbol[symbol].append(path)
    for symbol in by_symbol:
        # deterministic and keep the packet small
        by_symbol[symbol] = sorted(set(by_symbol[symbol]))[:50]
    return by_symbol


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
            raise ValueError(f"Operational language is not allowed in Dataset Evidence Scanner: {term}")


def _payload_sha(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(x) for x in row) + "|")
    return "\n".join(out)


def render_markdown(payload: dict[str, Any]) -> str:
    profiles = payload["symbol_profiles"]
    criteria = payload["criteria"]
    md = f"""# QRDS/QOS • Gate BTC • Research-only
## Dataset Evidence Scanner

Real local dataset scanner for the research stack. This packet profiles structured dataset files found in offline/cache/fixture locations; it cannot unlock operational use.

**Gate answer:** {payload['gate_answer']}

**Policy lock:** {payload['policy_lock']} • **Mode:** {payload['app_mode']}

## Summary

- Symbols: {', '.join(payload['symbols'])}
- Dataset files found: {payload['dataset_file_count']}
- Symbols with files: {payload['symbols_with_files']}/{len(payload['symbols'])}
- Total observed rows: {payload['total_observed_rows']}
- Criteria ready: {payload['criteria_ready_count']}/{payload['criteria_total_count']}
- Mean scanner score: {payload['mean_scanner_score']}

Research-only guardrail: no execution, no exchange account, no portfolio allocation output, no trade instruction, no live-fund workflow.

## Symbol profiles

{_table(
    ['symbol', 'file_count', 'row_count', 'time_column_present', 'null_rate_sample', 'duplicate_rows_sample', 'time_gap_count_sample', 'status'],
    [[p['symbol'], p['file_count'], p['row_count'], p['time_column_present'], p['null_rate_sample'], p['duplicate_rows_sample'], p['time_gap_count_sample'], p['status']] for p in profiles],
)}

## Criteria

{_table(
    ['criterion_id', 'status', 'ready', 'observed', 'threshold', 'blocker'],
    [[c['criterion_id'], c['status'], c['ready'], c['observed'], c['threshold'], c['blocker']] for c in criteria],
)}

## Safety flags

{_table(['flag', 'value'], [[k, v] for k, v in payload['safety_flags'].items()])}

Generated at {payload['generated_at']} • SHA256 {payload['report_payload_sha256']}
"""
    _assert_research_only(md)
    return md


def render_html(payload: dict[str, Any]) -> str:
    esc = lambda x: html.escape(str(x))
    profile_rows = "\n".join(
        f"<tr><td>{esc(p['symbol'])}</td><td>{esc(p['file_count'])}</td><td>{esc(p['row_count'])}</td><td>{esc(p['time_column_present'])}</td><td>{esc(p['null_rate_sample'])}</td><td>{esc(p['duplicate_rows_sample'])}</td><td>{esc(p['time_gap_count_sample'])}</td><td>{esc(p['status'])}</td></tr>"
        for p in payload['symbol_profiles']
    )
    criteria_rows = "\n".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td><td>{esc(c['blocker'])}</td></tr>"
        for c in payload['criteria']
    )
    flag_rows = "\n".join(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>" for k, v in payload['safety_flags'].items())
    page = f"""<!doctype html><html><head><meta charset='utf-8'><title>QRDS Dataset Evidence Scanner</title>
<style>
body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}.card{{background:#fff;border:1px solid #dbe3f0;border-radius:14px;padding:20px;margin:16px 0;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px 8px 8px 0;vertical-align:top}}table{{border-collapse:collapse;width:100%;background:white}}th,td{{border:1px solid #dbe3f0;padding:8px;text-align:left;font-size:14px}}th{{background:#eef2ff}}.warn{{border-left:6px solid #f59e0b}}.ok{{border-left:6px solid #16a34a}}.lock{{display:inline-block;background:#dbeafe;border-radius:999px;padding:6px 10px;font-weight:700}}
</style></head><body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Dataset Evidence Scanner</h2>
<p>Real local dataset scanner for the research stack. This page profiles structured offline/cache/fixture data; it cannot unlock operational use.</p>
<div class='card warn'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p><p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>
<div class='kpi'><b>Dataset files</b><br>{esc(payload['dataset_file_count'])}</div><div class='kpi'><b>Symbols with files</b><br>{esc(payload['symbols_with_files'])}/{esc(len(payload['symbols']))}</div><div class='kpi'><b>Total rows</b><br>{esc(payload['total_observed_rows'])}</div><div class='kpi'><b>Criteria ready</b><br>{esc(payload['criteria_ready_count'])}/{esc(payload['criteria_total_count'])}</div><div class='kpi'><b>Mean scanner score</b><br>{esc(payload['mean_scanner_score'])}</div>
<p class='lock'>Research-only guardrail active</p><p>No execution, no exchange account, no portfolio allocation output, no trade instruction, no live-fund workflow.</p></div>
<h2>Symbol profiles</h2><table><thead><tr><th>symbol</th><th>file_count</th><th>row_count</th><th>time_column_present</th><th>null_rate_sample</th><th>duplicate_rows_sample</th><th>time_gap_count_sample</th><th>status</th></tr></thead><tbody>{profile_rows}</tbody></table>
<h2>Criteria</h2><table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th><th>blocker</th></tr></thead><tbody>{criteria_rows}</tbody></table>
<h2>Safety flags</h2><table><thead><tr><th>flag</th><th>value</th></tr></thead><tbody>{flag_rows}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"""
    _assert_research_only(page)
    return page


def build_dataset_evidence_scan(
    output_dir: str | Path,
    symbols: str | Iterable[str] = "BTC-USDT,ETH-USDT,SOL-USDT",
    scan_roots: str | Iterable[str] | None = None,
    min_rows_per_symbol: int = 1000,
) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    symbol_list = _symbols(symbols)
    discovered = discover_dataset_files(symbol_list, scan_roots)

    symbol_profiles: list[dict[str, Any]] = []
    file_rows: list[dict[str, Any]] = []
    for symbol, files in discovered.items():
        row_count = 0
        null_cells = 0
        cell_count = 0
        duplicate_rows = 0
        gap_count = 0
        time_present = False
        file_hashes: list[str] = []
        errors: list[str] = []
        for file in files:
            profile = _profile_rows(file)
            sha = _file_sha256(file)
            file_hashes.append(sha[:16])
            row_count += int(profile['row_count'])
            null_cells += int(profile['null_count_sample'])
            cell_count += int(profile['cell_count_sample'])
            duplicate_rows += int(profile['duplicate_rows_sample'])
            gap_count += int(profile['time_gap_count_sample'])
            time_present = time_present or profile['time_column'] != 'MISSING'
            if profile['read_error']:
                errors.append(profile['read_error'])
            file_rows.append({
                'symbol': symbol,
                'path': str(file),
                'sha256': sha[:16],
                **profile,
            })
        null_rate = round(null_cells / cell_count, 6) if cell_count else 0.0
        status = 'PROFILED_WITH_GAPS_RESEARCH_ONLY'
        if not files:
            status = 'NO_LOCAL_STRUCTURED_DATASET_FOUND_RESEARCH_ONLY'
        elif row_count >= min_rows_per_symbol and time_present:
            status = 'PROFILED_PRELIMINARY_RESEARCH_ONLY'
        symbol_profiles.append({
            'symbol': symbol,
            'file_count': len(files),
            'row_count': row_count,
            'time_column_present': time_present,
            'null_rate_sample': null_rate,
            'duplicate_rows_sample': duplicate_rows,
            'time_gap_count_sample': gap_count,
            'file_hash_count': len(file_hashes),
            'status': status,
            'ready': bool(files and row_count >= min_rows_per_symbol and time_present),
            'blocker': '' if files else 'No structured local dataset file was found for this symbol.',
        })

    total_files = sum(p['file_count'] for p in symbol_profiles)
    symbols_with_files = sum(1 for p in symbol_profiles if p['file_count'] > 0)
    total_rows = sum(p['row_count'] for p in symbol_profiles)
    symbols_ready = sum(1 for p in symbol_profiles if p['ready'])
    time_symbols = sum(1 for p in symbol_profiles if p['time_column_present'])
    lineage_symbols = sum(1 for p in symbol_profiles if p['file_hash_count'] > 0)

    criteria = [
        _criterion('dataset_files_discovered', 'PASS' if total_files else 'FAIL', total_files > 0, total_files, '>= 1 structured local dataset file', '' if total_files else 'Need local fixture/cache/dataset files to profile.'),
        _criterion('symbol_file_coverage', 'PASS' if symbols_with_files == len(symbol_list) else 'WARN', symbols_with_files == len(symbol_list), f'{symbols_with_files}/{len(symbol_list)}', 'all symbols have at least one file', '' if symbols_with_files == len(symbol_list) else 'Need structured files for every requested symbol.'),
        _criterion('row_count_coverage', 'PASS' if symbols_ready == len(symbol_list) else 'WARN', symbols_ready == len(symbol_list), f'{symbols_ready}/{len(symbol_list)} symbols >= {min_rows_per_symbol} rows with time evidence', f'>= {min_rows_per_symbol} rows per symbol preferred', '' if symbols_ready == len(symbol_list) else 'Need larger explicit row coverage by symbol.'),
        _criterion('time_column_evidence', 'PASS' if time_symbols == len(symbol_list) else 'WARN', time_symbols == len(symbol_list), f'{time_symbols}/{len(symbol_list)}', 'time column detected for every symbol', '' if time_symbols == len(symbol_list) else 'Need time-index evidence for every symbol.'),
        _criterion('lineage_hashes', 'PASS' if lineage_symbols == len(symbol_list) else 'WARN', lineage_symbols == len(symbol_list), f'{lineage_symbols}/{len(symbol_list)}', 'file hashes for every symbol', '' if lineage_symbols == len(symbol_list) else 'Need hashed file lineage for every symbol.'),
        _criterion('research_only_lock', 'PASS', True, APP_MODE, 'policy lock active', ''),
    ]
    ready = sum(1 for c in criteria if c['ready'])
    score = round(ready / len(criteria), 4)

    if total_files == 0:
        gate_answer = 'NO_LOCAL_DATASET_EVIDENCE_FOUND_RESEARCH_ONLY'
    elif score >= 0.80:
        gate_answer = 'DATASET_EVIDENCE_SCANNER_PROFILED_WITH_REMAINING_RESEARCH_GAPS'
    else:
        gate_answer = 'DATASET_EVIDENCE_SCANNER_CREATED_WITH_PROFILE_GAPS_RESEARCH_ONLY'

    payload: dict[str, Any] = {
        'schema': 'qrds.dataset_evidence_scanner.v1',
        'report_name': 'qrds-dataset-evidence-scanner',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'gate_answer': gate_answer,
        'policy_lock': 'ACTIVE',
        'app_mode': APP_MODE,
        'symbols': symbol_list,
        'scan_roots': [str(p) for p in _split_roots(scan_roots)],
        'dataset_file_count': total_files,
        'symbols_with_files': symbols_with_files,
        'total_observed_rows': total_rows,
        'criteria_ready_count': ready,
        'criteria_total_count': len(criteria),
        'mean_scanner_score': score,
        'symbol_profiles': symbol_profiles,
        'file_profiles': file_rows[:200],
        'criteria': criteria,
        'safety_flags': SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload['report_payload_sha256'] = _payload_sha(payload)

    report_path = out / 'dataset_evidence_scan.json'
    markdown_path = out / 'dataset_evidence_scan.md'
    html_path = out / 'index.html'
    index_path = out / 'dataset_evidence_scan_index.json'
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding='utf-8')
    markdown_path.write_text(render_markdown(payload), encoding='utf-8')
    html_path.write_text(render_html(payload), encoding='utf-8')

    index = {
        'schema': 'qrds.dataset_evidence_scanner_index.v1',
        'report_name': payload['report_name'],
        'generated_at': payload['generated_at'],
        'gate_answer': payload['gate_answer'],
        'policy_lock': payload['policy_lock'],
        'app_mode': payload['app_mode'],
        'symbols': payload['symbols'],
        'dataset_file_count': payload['dataset_file_count'],
        'symbols_with_files': payload['symbols_with_files'],
        'total_observed_rows': payload['total_observed_rows'],
        'criteria_ready_count': payload['criteria_ready_count'],
        'criteria_total_count': payload['criteria_total_count'],
        'mean_scanner_score': payload['mean_scanner_score'],
        'report_path': str(report_path),
        'markdown_path': str(markdown_path),
        'html_path': str(html_path),
        'index_path': str(index_path),
        'serve_entrypoint': str(html_path),
        'report_payload_sha256': payload['report_payload_sha256'],
        'payload': payload,
        **SAFETY_FLAGS,
    }
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True), encoding='utf-8')
    return index
