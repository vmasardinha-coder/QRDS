from __future__ import annotations

import csv
import hashlib
import html
import json
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

STRUCTURED_SUFFIXES = {".csv", ".json", ".jsonl", ".ndjson"}
EXCLUDE_PARTS = {".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv"}


def _symbols(symbols: str | Iterable[str]) -> list[str]:
    if isinstance(symbols, str):
        return [s.strip() for s in symbols.split(",") if s.strip()]
    return [str(s).strip() for s in symbols if str(s).strip()]


def _repo_root() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "crypto_decision_lab" / "src" / "crypto_decision_lab").exists():
        return cwd
    if cwd.name == "crypto_decision_lab" and (cwd / "src" / "crypto_decision_lab").exists():
        return cwd.parent
    for parent in [cwd, *cwd.parents]:
        if (parent / "crypto_decision_lab" / "src" / "crypto_decision_lab").exists():
            return parent
    return cwd


def _resolve_path(path: str | Path) -> Path:
    p = Path(path)
    if p.exists():
        return p
    root = _repo_root()
    candidates = [root / p, root / "crypto_decision_lab" / p]
    raw = str(p)
    if raw.startswith("crypto_decision_lab/"):
        stripped = Path(raw.split("/", 1)[1])
        candidates.append(root / "crypto_decision_lab" / stripped)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return p


def _load_json(path: str | Path) -> dict[str, Any]:
    p = _resolve_path(path)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {
            "report_name": p.stem,
            "gate_answer": "UNREADABLE_INPUT_REPORT_RESEARCH_ONLY",
            "report_payload_sha256": "UNREADABLE",
        }


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        if isinstance(value, bool):
            return int(value)
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


def _kind(payload: dict[str, Any], path: str | Path) -> str:
    name = str(payload.get("report_name") or payload.get("schema") or Path(path).stem)
    low = name.lower().replace("-", "_").replace(".", "_")
    mapping = {
        "dataset_evidence_scan": "dataset_evidence_scan",
        "dataset_evidence_scanner": "dataset_evidence_scan",
        "dataset_evidence_explorer": "dataset_evidence_explorer",
        "dataset_manifest": "dataset_manifest",
        "data_profile": "data_profile",
        "data_readiness": "data_readiness",
        "data_gap_remediation": "data_gap_remediation",
        "data_coverage": "data_coverage",
        "data_quality": "data_quality",
        "data_audit": "data_audit",
        "evidence_stack": "evidence_stack",
    }
    for needle, kind in mapping.items():
        if needle in low:
            return kind
    fallback = Path(path).stem.lower().replace("-", "_").replace(".", "_")
    for needle, kind in mapping.items():
        if needle in fallback:
            return kind
    return fallback


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return "UNREADABLE"


def _count_csv_rows(path: Path) -> tuple[int, bool]:
    try:
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
            reader = csv.reader(handle)
            rows = list(reader)
        if not rows:
            return 0, False
        headers = [str(h).lower() for h in rows[0]]
        has_time = any(x in headers for x in ["time", "timestamp", "datetime", "date", "open_time"])
        return max(len(rows) - 1, 0), has_time
    except Exception:
        return 0, False


def _count_json_rows(path: Path) -> tuple[int, bool]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        if not text:
            return 0, False
        if path.suffix.lower() in {".jsonl", ".ndjson"}:
            count = sum(1 for line in text.splitlines() if line.strip())
            sample = text.splitlines()[0] if text.splitlines() else ""
            has_time = any(key in sample.lower() for key in ["time", "timestamp", "datetime", "date", "open_time"])
            return count, has_time
        data = json.loads(text)
        if isinstance(data, list):
            count = len(data)
            sample = data[0] if data else {}
        elif isinstance(data, dict):
            candidate = None
            for key in ["rows", "data", "items", "records", "candles", "klines"]:
                if isinstance(data.get(key), list):
                    candidate = data[key]
                    break
            if candidate is None:
                count = 1
                sample = data
            else:
                count = len(candidate)
                sample = candidate[0] if candidate else {}
        else:
            count = 0
            sample = {}
        sample_text = json.dumps(sample, ensure_ascii=False).lower() if sample is not None else ""
        has_time = any(key in sample_text for key in ["time", "timestamp", "datetime", "date", "open_time"])
        return count, has_time
    except Exception:
        return 0, False


def _file_symbol(path: Path, symbols: list[str]) -> str | None:
    low = str(path).lower().replace("_", "-")
    for symbol in symbols:
        s = symbol.lower()
        variants = {s, s.replace("-", ""), s.replace("-", "_"), s.split("-")[0]}
        if any(v in low for v in variants):
            return symbol
    return None


def _scan_local_files(symbols: list[str]) -> list[dict[str, Any]]:
    root = _repo_root()
    search_roots = [
        root / "crypto_decision_lab" / "data",
        root / "crypto_decision_lab" / "fixtures",
        root / "crypto_decision_lab" / "tests" / "fixtures",
        root / "crypto_decision_lab" / "artifacts",
        root / "data",
        root / "fixtures",
        root / "artifacts",
    ]
    files: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for base in search_roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in STRUCTURED_SUFFIXES:
                continue
            if any(part in EXCLUDE_PARTS for part in path.parts):
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            symbol = _file_symbol(path, symbols)
            if symbol is None:
                continue
            if path.suffix.lower() == ".csv":
                rows, has_time = _count_csv_rows(path)
            else:
                rows, has_time = _count_json_rows(path)
            files.append(
                {
                    "path": str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
                    "symbol": symbol,
                    "rows": rows,
                    "has_time_hint": has_time,
                    "sha256": _sha_file(path)[:16],
                    "suffix": path.suffix.lower(),
                }
            )
    return sorted(files, key=lambda x: (x["symbol"], -int(x["rows"]), x["path"]))


def _collect_reports(reports: Iterable[str | Path] | None) -> list[dict[str, Any]]:
    if not reports:
        return []
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for report in reports:
        p = _resolve_path(report)
        key = str(p.resolve()) if p.exists() else str(report)
        if key in seen:
            continue
        seen.add(key)
        payload = _load_json(p)
        rows.append(
            {
                "kind": _kind(payload, p),
                "path": str(p),
                "status": "REPORT_PRESENT" if p.exists() else "MISSING_FILE",
                "gate_answer": str(payload.get("gate_answer") or payload.get("command_answer") or payload.get("acceptance_status") or "UNKNOWN_RESEARCH_ONLY"),
                "total_rows": _as_int(payload.get("total_rows") or payload.get("dataset_total_rows") or 0),
                "dataset_files": _as_int(payload.get("dataset_file_count") or payload.get("dataset_files") or 0),
                "symbols_with_files": _as_int(payload.get("symbols_with_files_count") or payload.get("symbols_with_files") or 0),
                "criteria_ready_count": _as_int(payload.get("criteria_ready_count") or 0),
                "criteria_total_count": _as_int(payload.get("criteria_total_count") or 0),
                "score": _as_float(
                    payload.get("mean_scanner_score")
                    or payload.get("mean_explorer_score")
                    or payload.get("mean_manifest_score")
                    or payload.get("mean_profile_score")
                    or payload.get("mean_readiness_score")
                    or payload.get("mean_remediation_score")
                    or payload.get("mean_coverage_score")
                    or payload.get("mean_quality_score")
                    or payload.get("mean_audit_score")
                    or 0.0
                ),
                "sha256": str(payload.get("report_payload_sha256") or payload.get("sha256") or "MISSING")[:16],
            }
        )
    return rows


def normalize_reports(reports: Iterable[str | Path] | None) -> list[dict[str, Any]]:
    return _collect_reports(reports)


@dataclass(frozen=True)
class DepthTargets:
    min_total_rows: int = 3000
    min_rows_per_symbol: int = 1000
    min_files_per_symbol: int = 1
    min_time_aware_files_per_symbol: int = 1
    min_report_count: int = 2


def _derive_depth(symbols: list[str], reports: list[dict[str, Any]], files: list[dict[str, Any]]) -> dict[str, Any]:
    file_total_rows = sum(_as_int(f.get("rows")) for f in files)
    report_total_rows = max([_as_int(r.get("total_rows")) for r in reports] or [0])
    total_rows = max(file_total_rows, report_total_rows)

    per_symbol = {symbol: {"files": 0, "rows": 0, "time_aware_files": 0} for symbol in symbols}
    for item in files:
        symbol = str(item.get("symbol") or "")
        if symbol not in per_symbol:
            continue
        per_symbol[symbol]["files"] += 1
        per_symbol[symbol]["rows"] += _as_int(item.get("rows"))
        if bool(item.get("has_time_hint")):
            per_symbol[symbol]["time_aware_files"] += 1

    # If no direct file scan is available but upstream reports saw all symbols, distribute rows conservatively.
    if files == [] and reports and total_rows > 0:
        approx = total_rows // max(len(symbols), 1)
        for symbol in symbols:
            per_symbol[symbol]["rows"] = approx
            per_symbol[symbol]["files"] = max([_as_int(r.get("dataset_files")) for r in reports] or [0]) // max(len(symbols), 1)

    return {
        "total_rows": total_rows,
        "dataset_file_count": len(files) if files else max([_as_int(r.get("dataset_files")) for r in reports] or [0]),
        "symbols_with_files_count": sum(1 for v in per_symbol.values() if v["files"] > 0 or v["rows"] > 0),
        "per_symbol_depth": per_symbol,
        "time_aware_file_count": sum(_as_int(f.get("has_time_hint")) for f in files),
        "largest_files": sorted(files, key=lambda x: _as_int(x.get("rows")), reverse=True)[:25],
    }


def _criterion(criterion_id: str, status: str, ready: bool, observed: Any, threshold: str, blocker: str = "", priority: str = "MEDIUM") -> dict[str, Any]:
    return {
        "criterion_id": criterion_id,
        "status": status,
        "ready": bool(ready),
        "observed": observed,
        "threshold": threshold,
        "blocker": blocker,
        "priority": priority,
    }


def _build_criteria(symbols: list[str], reports: list[dict[str, Any]], depth: dict[str, Any], targets: DepthTargets) -> list[dict[str, Any]]:
    per_symbol = depth["per_symbol_depth"]
    report_count = len(reports)
    total_rows = _as_int(depth.get("total_rows"))
    dataset_file_count = _as_int(depth.get("dataset_file_count"))
    symbols_with_files = _as_int(depth.get("symbols_with_files_count"))
    min_symbol_rows = min([_as_int(v.get("rows")) for v in per_symbol.values()] or [0])
    min_symbol_files = min([_as_int(v.get("files")) for v in per_symbol.values()] or [0])
    min_time_files = min([_as_int(v.get("time_aware_files")) for v in per_symbol.values()] or [0])
    has_hashes = any(str(f.get("sha256")) not in {"", "MISSING", "UNREADABLE"} for f in depth.get("largest_files", [])) or any(r["sha256"] not in {"MISSING", "UNREADABLE"} for r in reports)

    return [
        _criterion(
            "input_dataset_evidence_reports",
            "PASS" if report_count >= targets.min_report_count else "WARN",
            report_count >= targets.min_report_count,
            report_count,
            f">= {targets.min_report_count} upstream data evidence reports preferred",
            "" if report_count >= targets.min_report_count else "Need scanner/explorer/profile reports for stronger depth context.",
        ),
        _criterion(
            "symbol_file_coverage",
            "PASS" if symbols_with_files >= len(symbols) else "FAIL",
            symbols_with_files >= len(symbols),
            f"{symbols_with_files}/{len(symbols)}",
            "all requested symbols should have local evidence",
            "" if symbols_with_files >= len(symbols) else "Need local structured evidence for every requested symbol.",
            "HIGH",
        ),
        _criterion(
            "dataset_file_depth",
            "PASS" if min_symbol_files >= targets.min_files_per_symbol else "FAIL",
            min_symbol_files >= targets.min_files_per_symbol,
            min_symbol_files,
            f">= {targets.min_files_per_symbol} file per symbol",
            "" if min_symbol_files >= targets.min_files_per_symbol else "Need at least one structured data file per symbol.",
            "HIGH",
        ),
        _criterion(
            "total_row_depth",
            "PASS" if total_rows >= targets.min_total_rows else "FAIL",
            total_rows >= targets.min_total_rows,
            total_rows,
            f">= {targets.min_total_rows} total rows preliminary target",
            "" if total_rows >= targets.min_total_rows else "Need deeper historical/offline coverage before data depth is mature.",
            "HIGH",
        ),
        _criterion(
            "per_symbol_row_depth",
            "PASS" if min_symbol_rows >= targets.min_rows_per_symbol else "FAIL",
            min_symbol_rows >= targets.min_rows_per_symbol,
            min_symbol_rows,
            f">= {targets.min_rows_per_symbol} rows per symbol preliminary target",
            "" if min_symbol_rows >= targets.min_rows_per_symbol else "Need deeper per-symbol row coverage.",
            "HIGH",
        ),
        _criterion(
            "time_column_depth",
            "PASS" if min_time_files >= targets.min_time_aware_files_per_symbol else "WARN",
            min_time_files >= targets.min_time_aware_files_per_symbol,
            min_time_files,
            f">= {targets.min_time_aware_files_per_symbol} time-aware file per symbol",
            "" if min_time_files >= targets.min_time_aware_files_per_symbol else "Need explicit time-column evidence for every symbol.",
        ),
        _criterion(
            "lineage_hash_depth",
            "PASS" if has_hashes else "FAIL",
            has_hashes,
            "present" if has_hashes else "missing",
            "hash/lineage evidence present",
            "" if has_hashes else "Need file or report hashes for lineage.",
        ),
    ]


def _assert_research_only(rendered: str) -> None:
    low = rendered.lower()
    for term in FORBIDDEN_RENDERED_PHRASES:
        if term in low:
            raise ValueError(f"Operational language is not allowed in Dataset Depth Requirements: {term}")


def _payload_sha(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(x) for x in row) + "|")
    return "\n".join(out)


def render_markdown(payload: dict[str, Any]) -> str:
    criteria = payload["criteria"]
    per_symbol = payload["per_symbol_depth"]
    reports = payload["input_reports"]
    flags = payload["safety_flags"]

    md = f"""# QRDS/QOS • Gate BTC • Research-only
## Dataset Depth Requirements

Formal research-data depth target packet. This page turns local dataset evidence into explicit minimum-depth gaps; it cannot unlock operational use.

**Gate answer:** {payload["gate_answer"]}

**Policy lock:** {payload["policy_lock"]} • **Mode:** {payload["app_mode"]}

## Summary

- Input reports: {payload["input_report_count"]}
- Dataset files: {payload["dataset_file_count"]}
- Symbols with files: {payload["symbols_with_files_count"]}/{len(payload["symbols"])}
- Total rows: {payload["total_rows"]}
- Criteria ready: {payload["criteria_ready_count"]}/{payload["criteria_total_count"]}
- Mean depth score: {payload["mean_depth_score"]}
- High priority gaps: {payload["high_priority_gap_count"]}

Research-only guardrail: no execution, no exchange account, no portfolio allocation output, no trade instruction, no live-fund workflow.

## Depth criteria

{_md_table(
    ["criterion_id", "status", "ready", "observed", "threshold", "priority", "blocker"],
    [[c["criterion_id"], c["status"], c["ready"], c["observed"], c["threshold"], c["priority"], c["blocker"]] for c in criteria],
)}

## Per-symbol depth

{_md_table(
    ["symbol", "files", "rows", "time_aware_files"],
    [[symbol, values["files"], values["rows"], values["time_aware_files"]] for symbol, values in per_symbol.items()],
)}

## Input reports

{_md_table(
    ["kind", "status", "gate_answer", "rows", "sha256"],
    [[r["kind"], r["status"], r["gate_answer"], r["total_rows"], r["sha256"]] for r in reports] if reports else [["NONE", "MISSING", "MISSING_INPUT_REPORT", 0, "MISSING"]],
)}

## Safety flags

{_md_table(["flag", "value"], [[k, v] for k, v in flags.items()])}

Generated at {payload["generated_at"]} • SHA256 {payload["report_payload_sha256"]}
"""
    _assert_research_only(md)
    return md


def render_html(payload: dict[str, Any]) -> str:
    def esc(x: Any) -> str:
        return html.escape(str(x))

    criteria_rows = "\n".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td><td>{esc(c['priority'])}</td><td>{esc(c['blocker'])}</td></tr>"
        for c in payload["criteria"]
    )
    symbol_rows = "\n".join(
        f"<tr><td>{esc(symbol)}</td><td>{esc(values['files'])}</td><td>{esc(values['rows'])}</td><td>{esc(values['time_aware_files'])}</td></tr>"
        for symbol, values in payload["per_symbol_depth"].items()
    )
    report_rows = "\n".join(
        f"<tr><td>{esc(r['kind'])}</td><td>{esc(r['status'])}</td><td>{esc(r['gate_answer'])}</td><td>{esc(r['total_rows'])}</td><td>{esc(r['sha256'])}</td></tr>"
        for r in payload["input_reports"]
    ) or "<tr><td>NONE</td><td>MISSING</td><td>MISSING_INPUT_REPORT</td><td>0</td><td>MISSING</td></tr>"
    flag_rows = "\n".join(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>" for k, v in payload["safety_flags"].items())

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>QRDS Dataset Depth Requirements</title>
<style>
body{{font-family:Arial,sans-serif;margin:32px;background:#f7f8fc;color:#172033}}
.card{{background:#fff;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px 8px 8px 0;vertical-align:top}}
table{{border-collapse:collapse;width:100%;background:#fff;margin:12px 0}}
th,td{{border:1px solid #d9deea;padding:8px;text-align:left;font-size:14px}}
th{{background:#eef2ff}}
.badge{{display:inline-block;border-radius:999px;background:#fee2e2;padding:6px 10px;font-weight:700}}
</style>
</head>
<body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1>
<h2>Dataset Depth Requirements</h2>
<p>Formal research-data depth target packet. This page turns local dataset evidence into explicit minimum-depth gaps; it cannot unlock operational use.</p>
<div class="card">
<p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p>
<p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>
<div class="kpi"><b>Input reports</b><br>{esc(payload['input_report_count'])}</div>
<div class="kpi"><b>Dataset files</b><br>{esc(payload['dataset_file_count'])}</div>
<div class="kpi"><b>Symbols with files</b><br>{esc(payload['symbols_with_files_count'])}/{esc(len(payload['symbols']))}</div>
<div class="kpi"><b>Total rows</b><br>{esc(payload['total_rows'])}</div>
<div class="kpi"><b>Criteria ready</b><br>{esc(payload['criteria_ready_count'])}/{esc(payload['criteria_total_count'])}</div>
<div class="kpi"><b>Mean depth score</b><br>{esc(payload['mean_depth_score'])}</div>
<div class="kpi"><b>High priority gaps</b><br>{esc(payload['high_priority_gap_count'])}</div>
<p class="badge">Research-only guardrail active</p>
<p>No execution, no exchange account, no portfolio allocation output, no trade instruction, no live-fund workflow.</p>
</div>
<h2>Depth criteria</h2>
<table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th><th>priority</th><th>blocker</th></tr></thead><tbody>{criteria_rows}</tbody></table>
<h2>Per-symbol depth</h2>
<table><thead><tr><th>symbol</th><th>files</th><th>rows</th><th>time_aware_files</th></tr></thead><tbody>{symbol_rows}</tbody></table>
<h2>Input reports</h2>
<table><thead><tr><th>kind</th><th>status</th><th>gate_answer</th><th>rows</th><th>sha256</th></tr></thead><tbody>{report_rows}</tbody></table>
<h2>Safety flags</h2>
<table><thead><tr><th>flag</th><th>value</th></tr></thead><tbody>{flag_rows}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p>
</body>
</html>
"""
    _assert_research_only(page)
    return page


def build_dataset_depth_requirements(
    output_dir: str | Path,
    symbols: str | Iterable[str],
    reports: Iterable[str | Path] | None = None,
    min_total_rows: int = 3000,
    min_rows_per_symbol: int = 1000,
    scan_local: bool = True,
) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    symbol_list = _symbols(symbols)
    targets = DepthTargets(min_total_rows=min_total_rows, min_rows_per_symbol=min_rows_per_symbol)
    input_reports = _collect_reports(reports)
    local_files = _scan_local_files(symbol_list) if scan_local else []
    depth = _derive_depth(symbol_list, input_reports, local_files)
    criteria = _build_criteria(symbol_list, input_reports, depth, targets)

    ready_count = sum(1 for c in criteria if c["ready"])
    total_count = len(criteria)
    mean_score = round(ready_count / total_count if total_count else 0.0, 4)
    high_priority_gap_count = sum(1 for c in criteria if not c["ready"] and c["priority"] == "HIGH")
    medium_priority_gap_count = sum(1 for c in criteria if not c["ready"] and c["priority"] != "HIGH")

    if not input_reports and not local_files:
        gate_answer = "NO_DATASET_DEPTH_EVIDENCE_FOUND_RESEARCH_ONLY"
    elif high_priority_gap_count > 0:
        gate_answer = "DATASET_DEPTH_REQUIREMENTS_CREATED_HIGH_PRIORITY_DEPTH_GAPS_RESEARCH_ONLY"
    elif medium_priority_gap_count > 0:
        gate_answer = "DATASET_DEPTH_REQUIREMENTS_CREATED_MEDIUM_DEPTH_GAPS_RESEARCH_ONLY"
    else:
        gate_answer = "DATASET_DEPTH_REQUIREMENTS_PRELIMINARY_READY_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.dataset_depth_requirements.v1",
        "report_name": "qrds-dataset-depth-requirements",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "symbols": symbol_list,
        "input_report_count": len(input_reports),
        "dataset_file_count": depth["dataset_file_count"],
        "symbols_with_files_count": depth["symbols_with_files_count"],
        "total_rows": depth["total_rows"],
        "per_symbol_depth": depth["per_symbol_depth"],
        "time_aware_file_count": depth["time_aware_file_count"],
        "largest_files": depth["largest_files"],
        "criteria_ready_count": ready_count,
        "criteria_total_count": total_count,
        "mean_depth_score": mean_score,
        "high_priority_gap_count": high_priority_gap_count,
        "medium_priority_gap_count": medium_priority_gap_count,
        "targets": {
            "min_total_rows": targets.min_total_rows,
            "min_rows_per_symbol": targets.min_rows_per_symbol,
            "min_files_per_symbol": targets.min_files_per_symbol,
            "min_time_aware_files_per_symbol": targets.min_time_aware_files_per_symbol,
        },
        "criteria": criteria,
        "input_reports": input_reports,
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _payload_sha(payload)

    report_path = out / "dataset_depth_requirements_gate.json"
    markdown_path = out / "dataset_depth_requirements_gate.md"
    html_path = out / "index.html"
    index_path = out / "dataset_depth_requirements_index.json"

    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    index = {
        "schema": "qrds.dataset_depth_requirements_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "symbols": payload["symbols"],
        "input_report_count": payload["input_report_count"],
        "dataset_file_count": payload["dataset_file_count"],
        "symbols_with_files_count": payload["symbols_with_files_count"],
        "total_rows": payload["total_rows"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_depth_score": payload["mean_depth_score"],
        "high_priority_gap_count": payload["high_priority_gap_count"],
        "medium_priority_gap_count": payload["medium_priority_gap_count"],
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
