from __future__ import annotations

import csv
import hashlib
import html
import json
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

DATA_EXTENSIONS = {".csv", ".json", ".jsonl", ".ndjson"}
EXCLUDED_DIR_PARTS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    "artifacts",
    "htmlcov",
    ".mypy_cache",
    ".ruff_cache",
}


def _symbols(symbols: str | Iterable[str]) -> list[str]:
    if isinstance(symbols, str):
        return [s.strip() for s in symbols.split(",") if s.strip()]
    return [str(s).strip() for s in symbols if str(s).strip()]


def _resolve(path: str | Path, repo_root: str | Path | None = None) -> Path:
    p = Path(path)
    if p.exists():
        return p
    roots = [Path.cwd()]
    if repo_root:
        roots.append(Path(repo_root))
    roots.extend([Path.cwd().parent, Path.cwd() / "crypto_decision_lab", Path.cwd().parent / "crypto_decision_lab"])
    raw = str(p)
    for root in roots:
        candidates = [root / p]
        if raw.startswith("crypto_decision_lab/"):
            candidates.append(root / raw.split("/", 1)[1])
        for c in candidates:
            if c.exists():
                return c
    return p


def _sha_file(path: Path, limit_bytes: int = 2_000_000) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            remaining = limit_bytes
            while remaining > 0:
                chunk = f.read(min(65536, remaining))
                if not chunk:
                    break
                h.update(chunk)
                remaining -= len(chunk)
        return h.hexdigest()
    except Exception:
        return "UNREADABLE"


def _infer_symbol(path: Path, symbols: list[str]) -> str:
    low = str(path).lower().replace("_", "-")
    for sym in symbols:
        if sym.lower() in low or sym.lower().replace("-", "") in low.replace("-", ""):
            return sym
    return "UNKNOWN"


def _count_rows(path: Path) -> tuple[int, list[str], bool, str]:
    """Count rows and infer columns/time hints for CSV/JSON/JSONL.

    JSON counting is recursive to avoid treating fixture wrappers as one row.
    """
    time_names = {"time", "timestamp", "datetime", "date", "open_time", "close_time", "ts"}
    row_keys = ("candles", "klines", "rows", "records", "items", "data", "bars", "ohlcv", "prices")

    def sample_columns(rows: list[Any]) -> list[str]:
        if not rows:
            return []
        first = rows[0]
        if isinstance(first, dict):
            return [str(k) for k in first.keys()]
        if isinstance(first, (list, tuple)):
            return [f"col_{i}" for i in range(len(first))]
        return ["value"]

    def has_time(cols: list[str]) -> bool:
        low = {c.lower() for c in cols}
        return bool(low.intersection(time_names))

    def find_rows(obj: Any) -> tuple[int, list[str], bool]:
        if isinstance(obj, list):
            cols = sample_columns(obj)
            return len(obj), cols, has_time(cols)
        if isinstance(obj, dict):
            for key in row_keys:
                value = obj.get(key)
                if isinstance(value, list):
                    cols = sample_columns(value)
                    return len(value), cols, has_time(cols)
                if isinstance(value, dict):
                    count, cols, time_col = find_rows(value)
                    if count:
                        return count, cols, time_col
            payload = obj.get("payload")
            if isinstance(payload, (dict, list)):
                count, cols, time_col = find_rows(payload)
                if count:
                    return count, cols, time_col
        return 0, [], False

    try:
        suffix = path.suffix.lower()
        if suffix == ".csv":
            with path.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                cols = list(reader.fieldnames or [])
                count = sum(1 for _ in reader)
                return count, cols, has_time(cols), "OK"
        if suffix == ".jsonl":
            count = 0
            cols: list[str] = []
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    count += 1
                    if not cols:
                        try:
                            obj = json.loads(line)
                            cols = sample_columns([obj])
                        except Exception:
                            cols = []
            return count, cols, has_time(cols), "OK"
        if suffix == ".json":
            obj = json.loads(path.read_text(encoding="utf-8"))
            count, cols, time_col = find_rows(obj)
            return count, cols, time_col, "OK" if count else "NO_ROWS_FOUND"
        return 0, [], False, "UNSUPPORTED_SUFFIX"
    except Exception as exc:  # pragma: no cover - defensive explorer reader
        return 0, [], False, f"READ_ERROR:{type(exc).__name__}"


def _extract_scan_rows(obj: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            keys = {str(k).lower() for k in node}
            has_path = any(k in keys for k in ["path", "file", "file_path", "dataset_path"])
            has_dataset_shape = any(k in keys for k in ["row_count", "rows", "total_rows", "symbol", "sha256", "status"])
            if has_path and has_dataset_shape:
                rows.append(node)
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(obj)
    return rows


def _row_from_scan(raw: dict[str, Any], repo_root: str | Path | None, symbols: list[str]) -> dict[str, Any]:
    raw_path = raw.get("path") or raw.get("file") or raw.get("file_path") or raw.get("dataset_path") or "UNKNOWN"
    path = _resolve(str(raw_path), repo_root)
    row_count = int(float(raw.get("row_count") or raw.get("rows") or raw.get("total_rows") or 0)) if str(raw.get("row_count") or raw.get("rows") or raw.get("total_rows") or "0").replace('.', '', 1).isdigit() else 0
    if row_count == 0 and path.exists() and path.is_file():
        row_count, cols, time_col, read_status = _count_rows(path)
    else:
        cols = raw.get("columns") if isinstance(raw.get("columns"), list) else []
        time_col = bool(raw.get("time_column_present") or raw.get("has_time_column") or raw.get("time_col"))
        read_status = "READABLE" if path.exists() else "MISSING_FILE"
    symbol = str(raw.get("symbol") or _infer_symbol(path, symbols))
    return {
        "symbol": symbol,
        "path": str(path),
        "status": read_status,
        "row_count": row_count,
        "columns": [str(c) for c in cols[:12]],
        "time_column_present": bool(time_col),
        "sha256": str(raw.get("sha256") or raw.get("file_sha256") or _sha_file(path))[:16],
        "source": "scan_report",
    }


def _scan_local(repo_root: str | Path | None, symbols: list[str], max_files: int) -> list[dict[str, Any]]:
    root = Path(repo_root) if repo_root else Path.cwd()
    if not root.exists():
        root = Path.cwd()
    candidates = [root / "crypto_decision_lab" / "data", root / "crypto_decision_lab" / "fixtures", root / "crypto_decision_lab" / "cache", root / "crypto_decision_lab" / "tests", root / "crypto_decision_lab" / "src"]
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for base in candidates:
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if len(rows) >= max_files:
                break
            if not p.is_file() or p.suffix.lower() not in DATA_EXTENSIONS:
                continue
            if any(part in EXCLUDED_DIR_PARTS for part in p.parts):
                continue
            key = str(p.resolve())
            if key in seen:
                continue
            seen.add(key)
            row_count, cols, time_col, status = _count_rows(p)
            rows.append({
                "symbol": _infer_symbol(p, symbols),
                "path": str(p),
                "status": status,
                "row_count": row_count,
                "columns": cols,
                "time_column_present": time_col,
                "sha256": _sha_file(p)[:16],
                "source": "local_scan",
            })
    return rows


def _collect_rows(scan_report: str | Path | None, repo_root: str | Path | None, symbols: list[str], max_files: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if scan_report:
        p = _resolve(scan_report, repo_root)
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
            rows.extend(_row_from_scan(r, repo_root, symbols) for r in _extract_scan_rows(obj))
        except Exception:
            pass
    if not rows:
        rows = _scan_local(repo_root, symbols, max_files=max_files)
    # Deduplicate by path, keep largest row_count.
    by_path: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = row.get("path", "")
        old = by_path.get(key)
        if old is None or int(row.get("row_count") or 0) > int(old.get("row_count") or 0):
            by_path[key] = row
    return sorted(by_path.values(), key=lambda r: int(r.get("row_count") or 0), reverse=True)[:max_files]


def _criterion(criterion_id: str, status: str, ready: bool, observed: Any, threshold: str, blocker: str = "") -> dict[str, Any]:
    return {"criterion_id": criterion_id, "status": status, "ready": bool(ready), "observed": observed, "threshold": threshold, "blocker": blocker}


def _build_criteria(rows: list[dict[str, Any]], symbols: list[str]) -> list[dict[str, Any]]:
    files = len(rows)
    total_rows = sum(int(r.get("row_count") or 0) for r in rows)
    covered = {r.get("symbol") for r in rows if r.get("symbol") in set(symbols)}
    readable = sum(1 for r in rows if r.get("status") == "READABLE")
    with_time = sum(1 for r in rows if r.get("time_column_present"))
    with_hash = sum(1 for r in rows if r.get("sha256") and r.get("sha256") != "UNREADABLE")
    return [
        _criterion("dataset_files_found", "PASS" if files > 0 else "FAIL", files > 0, files, ">= 1 structured file", "" if files else "Need local fixture/cache/offline data files."),
        _criterion("symbol_file_coverage", "PASS" if len(covered) >= len(symbols) else "WARN", len(covered) >= len(symbols), f"{len(covered)}/{len(symbols)}", "all requested symbols have files", "" if len(covered) >= len(symbols) else "Some requested symbols do not have explicit files."),
        _criterion("row_volume_observed", "PASS" if total_rows >= 1000 else "WARN", total_rows >= 1000, total_rows, ">= 1000 rows preferred", "" if total_rows >= 1000 else "Need deeper local historical coverage before data readiness can mature."),
        _criterion("readable_files", "PASS" if readable == files and files > 0 else "WARN", readable == files and files > 0, f"{readable}/{files}", "all files readable", "" if readable == files and files > 0 else "Some structured files are missing or unreadable."),
        _criterion("time_column_presence", "PASS" if with_time > 0 else "WARN", with_time > 0, with_time, ">= 1 file with explicit time column", "" if with_time > 0 else "Need explicit time columns for time-series audits."),
        _criterion("lineage_hash_presence", "PASS" if with_hash == files and files > 0 else "WARN", with_hash == files and files > 0, f"{with_hash}/{files}", "all files have content hash", "" if with_hash == files and files > 0 else "Need hashes for all dataset evidence files."),
    ]


def _assert_research_only(rendered: str) -> None:
    low = rendered.lower()
    for term in FORBIDDEN_RENDERED_PHRASES:
        if term in low:
            raise ValueError(f"Operational language is not allowed in Dataset Evidence Explorer: {term}")


def _sha_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _table_md(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    out.extend("|" + "|".join(str(x) for x in row) + "|" for row in rows)
    return "\n".join(out)


def render_markdown(payload: dict[str, Any]) -> str:
    file_rows = [[r["symbol"], r["status"], r["row_count"], r["time_column_present"], r["sha256"], r["path"]] for r in payload["dataset_rows"][:40]]
    criteria_rows = [[c["criterion_id"], c["status"], c["ready"], c["observed"], c["threshold"], c["blocker"]] for c in payload["criteria"]]
    flag_rows = [[k, v] for k, v in payload["safety_flags"].items()]
    md = f"""# QRDS/QOS • Gate BTC • Research-only
## Dataset Evidence Explorer

Drilldown of local structured dataset evidence. This page explains which files were found and what remains to validate; it cannot unlock operational use.

**Gate answer:** {payload['gate_answer']}

**Policy lock:** {payload['policy_lock']} • **Mode:** {payload['app_mode']}

- Dataset files: {payload['dataset_file_count']}
- Symbols with files: {payload['symbols_with_files']}/{len(payload['symbols'])}
- Total rows: {payload['total_rows']}
- Criteria ready: {payload['criteria_ready_count']}/{payload['criteria_total_count']}
- Mean explorer score: {payload['mean_explorer_score']}

Research-only guardrail: no execution, no exchange account, no portfolio allocation output, no trade instruction, no live-fund workflow.

## Criteria

{_table_md(['criterion_id', 'status', 'ready', 'observed', 'threshold', 'blocker'], criteria_rows)}

## Dataset files

{_table_md(['symbol', 'status', 'rows', 'time_col', 'sha256', 'path'], file_rows if file_rows else [['NONE', 'MISSING', 0, False, 'MISSING', 'MISSING']])}

## Safety flags

{_table_md(['flag', 'value'], flag_rows)}

Generated at {payload['generated_at']} • SHA256 {payload['report_payload_sha256']}
"""
    _assert_research_only(md)
    return md


def render_html(payload: dict[str, Any]) -> str:
    esc = lambda x: html.escape(str(x))
    criteria_rows = "\n".join(f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td><td>{esc(c['blocker'])}</td></tr>" for c in payload["criteria"])
    file_rows = "\n".join(f"<tr><td>{esc(r['symbol'])}</td><td>{esc(r['status'])}</td><td>{esc(r['row_count'])}</td><td>{esc(r['time_column_present'])}</td><td>{esc(r['sha256'])}</td><td>{esc(r['path'])}</td></tr>" for r in payload["dataset_rows"][:80]) or "<tr><td>NONE</td><td>MISSING</td><td>0</td><td>False</td><td>MISSING</td><td>MISSING</td></tr>"
    flag_rows = "\n".join(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>" for k, v in payload["safety_flags"].items())
    page = f"""<!doctype html><html><head><meta charset='utf-8'><title>QRDS Dataset Evidence Explorer</title>
<style>body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}.card{{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0;box-shadow:0 1px 3px rgba(0,0,0,.06)}}.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px 8px 8px 0}}table{{border-collapse:collapse;width:100%;background:white}}th,td{{border:1px solid #d9deea;padding:8px;text-align:left;font-size:13px}}th{{background:#eef2ff}}.badge{{display:inline-block;border-radius:999px;background:#dbeafe;padding:6px 10px;font-weight:700}}</style></head><body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Dataset Evidence Explorer</h2>
<p>Drilldown of local structured dataset evidence. This page records files, row coverage, time-column hints, lineage hashes, and blockers; it cannot unlock operational use.</p>
<div class='card'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p><p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>
<div class='kpi'><b>Dataset files</b><br>{esc(payload['dataset_file_count'])}</div><div class='kpi'><b>Symbols with files</b><br>{esc(payload['symbols_with_files'])}/{esc(len(payload['symbols']))}</div><div class='kpi'><b>Total rows</b><br>{esc(payload['total_rows'])}</div><div class='kpi'><b>Criteria ready</b><br>{esc(payload['criteria_ready_count'])}/{esc(payload['criteria_total_count'])}</div><div class='kpi'><b>Mean explorer score</b><br>{esc(payload['mean_explorer_score'])}</div>
<p class='badge'>Research-only guardrail active</p><p>No execution, no exchange account, no portfolio allocation output, no trade instruction, no live-fund workflow.</p></div>
<h2>Criteria</h2><table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th><th>blocker</th></tr></thead><tbody>{criteria_rows}</tbody></table>
<h2>Dataset files</h2><table><thead><tr><th>symbol</th><th>status</th><th>rows</th><th>time_col</th><th>sha256</th><th>path</th></tr></thead><tbody>{file_rows}</tbody></table>
<h2>Safety flags</h2><table><thead><tr><th>flag</th><th>value</th></tr></thead><tbody>{flag_rows}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"""
    _assert_research_only(page)
    return page


def build_dataset_evidence_explorer(
    output_dir: str | Path,
    symbols: str | Iterable[str] = "BTC-USDT,ETH-USDT,SOL-USDT",
    scan_report: str | Path | None = None,
    repo_root: str | Path | None = None,
    max_files: int = 150,
) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    symbol_list = _symbols(symbols)
    rows = _collect_rows(scan_report=scan_report, repo_root=repo_root, symbols=symbol_list, max_files=max_files)
    criteria = _build_criteria(rows, symbol_list)
    ready_count = sum(1 for c in criteria if c["ready"])
    total = len(criteria)
    score = round(ready_count / total if total else 0.0, 4)
    covered = {r.get("symbol") for r in rows if r.get("symbol") in set(symbol_list)}
    total_rows = sum(int(r.get("row_count") or 0) for r in rows)
    if not rows:
        gate_answer = "NO_DATASET_EVIDENCE_TO_EXPLORE_RESEARCH_ONLY"
    elif score >= 0.83 and total_rows >= 1000:
        gate_answer = "DATASET_EVIDENCE_EXPLORER_PROFILED_PARTIAL_GAPS_REMAIN_RESEARCH_ONLY"
    else:
        gate_answer = "DATASET_EVIDENCE_EXPLORER_READY_WITH_REMAINING_RESEARCH_GAPS_RESEARCH_ONLY"
    payload: dict[str, Any] = {
        "schema": "qrds.dataset_evidence_explorer.v1",
        "report_name": "qrds-dataset-evidence-explorer",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "symbols": symbol_list,
        "dataset_file_count": len(rows),
        "symbols_with_files": len(covered),
        "total_rows": total_rows,
        "criteria_ready_count": ready_count,
        "criteria_total_count": total,
        "mean_explorer_score": score,
        "dataset_rows": rows,
        "criteria": criteria,
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)
    report_path = out / "dataset_evidence_explorer.json"
    md_path = out / "dataset_evidence_explorer.md"
    html_path = out / "index.html"
    index_path = out / "dataset_evidence_explorer_index.json"
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")
    index = {
        "schema": "qrds.dataset_evidence_explorer_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "symbols": symbol_list,
        "dataset_file_count": payload["dataset_file_count"],
        "symbols_with_files": payload["symbols_with_files"],
        "total_rows": payload["total_rows"],
        "criteria_ready_count": ready_count,
        "criteria_total_count": total,
        "mean_explorer_score": score,
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
