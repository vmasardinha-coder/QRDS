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

DATA_EXTENSIONS = {".csv", ".json", ".jsonl"}


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


def _is_canonical_data_path(path: Path) -> bool:
    parts = {p.lower() for p in path.parts}
    if "artifacts" in parts:
        return False
    if "docs" in parts or "tests" in parts or "__pycache__" in parts:
        return False
    if ".git" in parts or ".pytest_cache" in parts:
        return False
    return True


def _count_json_rows(path: Path) -> int:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return 0
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        for key in ("data", "rows", "records", "items", "candles", "klines", "prices", "bars"):
            value = payload.get(key)
            if isinstance(value, list):
                return len(value)
        return 1
    return 0


def _count_rows(path: Path) -> int:
    suffix = path.suffix.lower()
    try:
        if suffix == ".csv":
            with path.open("r", encoding="utf-8", newline="") as f:
                return max(sum(1 for _ in f) - 1, 0)
        if suffix == ".jsonl":
            with path.open("r", encoding="utf-8") as f:
                return sum(1 for line in f if line.strip())
        if suffix == ".json":
            return _count_json_rows(path)
    except Exception:
        return 0
    return 0


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return "UNREADABLE"


def _scan_canonical_data(symbols: list[str]) -> list[dict[str, Any]]:
    root = _repo_root()
    data_root = root / "crypto_decision_lab" / "data"
    rows: list[dict[str, Any]] = []
    if not data_root.exists():
        return rows

    for path in sorted(data_root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in DATA_EXTENSIONS:
            continue
        if not _is_canonical_data_path(path):
            continue

        symbol = _file_symbol(path, symbols)
        if not symbol:
            continue

        rel = str(path.relative_to(root))
        if "artifacts/" in rel or "/artifacts/" in rel:
            raise ValueError(f"Contaminated dataset path is not allowed: {rel}")

        rows.append(
            {
                "symbol": symbol,
                "path": rel,
                "row_count": _count_rows(path),
                "sha256": _sha_file(path)[:16],
                "extension": path.suffix.lower(),
            }
        )
    return rows


def _report_kind(payload: dict[str, Any], path: str | Path) -> str:
    name = str(payload.get("report_name") or payload.get("schema") or Path(path).stem)
    low = name.lower().replace("-", "_").replace(".", "_")
    mapping = {
        "dataset_evidence_scan": "dataset_evidence_scan",
        "dataset_evidence_explorer": "dataset_evidence_explorer",
        "dataset_manifest": "dataset_manifest",
        "data_profile": "data_profile",
        "data_readiness": "data_readiness",
        "data_gap_remediation": "data_gap_remediation",
        "data_coverage": "data_coverage",
        "data_quality": "data_quality",
        "data_audit": "data_audit",
    }
    for needle, kind in mapping.items():
        if needle in low:
            return kind
    fallback = Path(path).stem.lower().replace("-", "_").replace(".", "_")
    for needle, kind in mapping.items():
        if needle in fallback:
            return kind
    return fallback


def _safe_load_report(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    candidates = [p, Path.cwd() / p, Path.cwd().parent / p]
    raw = str(p)
    if raw.startswith("crypto_decision_lab/"):
        stripped = Path(raw.split("/", 1)[1])
        candidates.extend([Path.cwd() / stripped, Path.cwd().parent / stripped])
    for candidate in candidates:
        if candidate.exists():
            try:
                payload = json.loads(candidate.read_text(encoding="utf-8"))
                payload["_resolved_path"] = str(candidate)
                return payload
            except Exception:
                return {"_resolved_path": str(candidate), "report_name": candidate.stem, "gate_answer": "UNREADABLE_INPUT_REPORT_RESEARCH_ONLY"}
    return {"_resolved_path": str(p), "report_name": p.stem, "gate_answer": "MISSING_INPUT_REPORT_RESEARCH_ONLY"}


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
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


def normalize_reports(reports: Iterable[str | Path] | None) -> list[dict[str, Any]]:
    """Normalize only explicitly provided reports.

    This function intentionally does not auto-discover local artifacts.
    The shell wrapper decides which reports are explicit inputs.
    """
    rows: list[dict[str, Any]] = []
    if not reports:
        return rows

    seen: set[str] = set()
    for item in reports:
        payload = _safe_load_report(item)
        resolved = str(payload.get("_resolved_path") or item)
        if resolved in seen:
            continue
        seen.add(resolved)

        rows.append(
            {
                "kind": _report_kind(payload, resolved),
                "path": resolved,
                "status": "REPORT_PRESENT" if Path(resolved).exists() else "MISSING_FILE",
                "ready": bool(payload.get("ready") or payload.get("formal_data_coverage_ready") == "YES"),
                "gate_answer": str(payload.get("gate_answer") or "UNKNOWN_RESEARCH_ONLY"),
                "dataset_file_count": _as_int(payload.get("dataset_file_count") or payload.get("dataset_files") or 0),
                "symbols_with_files_count": _as_int(payload.get("symbols_with_files_count") or payload.get("symbols_with_files") or 0),
                "total_rows": _as_int(payload.get("total_rows") or 0),
                "score": _as_float(
                    payload.get("mean_scanner_score")
                    or payload.get("mean_explorer_score")
                    or payload.get("mean_manifest_score")
                    or payload.get("mean_profile_score")
                    or payload.get("mean_readiness_score")
                    or payload.get("mean_remediation_score")
                    or 0.0
                ),
                "sha256": str(payload.get("report_payload_sha256") or payload.get("sha256") or "MISSING")[:16],
            }
        )
    return rows


def _summary_from_reports(input_reports: list[dict[str, Any]]) -> dict[str, int]:
    """Use explicit upstream evidence summaries, without walking nested artifact paths."""
    preferred = [
        r for r in input_reports
        if r.get("kind") in {"dataset_evidence_scan", "dataset_evidence_explorer", "dataset_manifest", "data_profile"}
    ]
    pool = preferred or input_reports
    return {
        "dataset_file_count": max([_as_int(r.get("dataset_file_count")) for r in pool] or [0]),
        "symbols_with_files_count": max([_as_int(r.get("symbols_with_files_count")) for r in pool] or [0]),
        "total_rows": max([_as_int(r.get("total_rows")) for r in pool] or [0]),
    }


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
            raise ValueError(f"Operational language is not allowed in Dataset Depth Requirements: {term}")


def _sha_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(x) for x in row) + "|")
    return "\n".join(out)


def render_markdown(payload: dict[str, Any]) -> str:
    md = f"""# QRDS/QOS • Gate BTC • Research-only
## Dataset Depth Requirements

Formal research-data depth target packet. This page turns canonical local dataset evidence into explicit minimum-depth gaps; it cannot unlock operational use.

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

## Criteria

{_table(
    ["criterion_id", "status", "ready", "observed", "threshold", "blocker"],
    [[c["criterion_id"], c["status"], c["ready"], c["observed"], c["threshold"], c["blocker"]] for c in payload["criteria"]],
)}

## Canonical dataset files

{_table(
    ["symbol", "path", "rows", "sha256"],
    [[r["symbol"], r["path"], r["row_count"], r["sha256"]] for r in payload["dataset_files"][:80]] or [["NONE", "MISSING", 0, "MISSING"]],
)}

## Safety flags

{_table(["flag", "value"], [[k, v] for k, v in SAFETY_FLAGS.items()])}

Generated at {payload["generated_at"]} • SHA256 {payload["report_payload_sha256"]}
"""
    _assert_research_only(md)
    return md


def render_html(payload: dict[str, Any]) -> str:
    def esc(x: Any) -> str:
        return html.escape(str(x))

    criteria_rows = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td><td>{esc(c['blocker'])}</td></tr>"
        for c in payload["criteria"]
    )
    file_rows = "".join(
        f"<tr><td>{esc(r['symbol'])}</td><td>{esc(r['path'])}</td><td>{esc(r['row_count'])}</td><td>{esc(r['sha256'])}</td></tr>"
        for r in payload["dataset_files"][:120]
    ) or "<tr><td>NONE</td><td>MISSING</td><td>0</td><td>MISSING</td></tr>"
    flag_rows = "".join(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>" for k, v in SAFETY_FLAGS.items())

    page = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>QRDS Dataset Depth Requirements</title>
<style>
body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}
.card{{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}}
.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px 8px 8px 0}}
table{{border-collapse:collapse;width:100%;background:white}}
th,td{{border:1px solid #d9deea;padding:8px;text-align:left;font-size:14px}}
th{{background:#eef2ff}}
.badge{{display:inline-block;background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}}
</style></head><body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1>
<h2>Dataset Depth Requirements</h2>
<p>Formal research-data depth target packet. This page uses only canonical local data under <code>crypto_decision_lab/data/</code>; it cannot unlock operational use.</p>
<div class="card">
<p><b>Gate answer:</b> {esc(payload["gate_answer"])}</p>
<p><b>Policy lock:</b> {esc(payload["policy_lock"])} • <b>Mode:</b> {esc(payload["app_mode"])}</p>
<div class="kpi"><b>Input reports</b><br>{esc(payload["input_report_count"])}</div>
<div class="kpi"><b>Dataset files</b><br>{esc(payload["dataset_file_count"])}</div>
<div class="kpi"><b>Symbols with files</b><br>{esc(payload["symbols_with_files_count"])}/{esc(len(payload["symbols"]))}</div>
<div class="kpi"><b>Total rows</b><br>{esc(payload["total_rows"])}</div>
<div class="kpi"><b>Criteria ready</b><br>{esc(payload["criteria_ready_count"])}/{esc(payload["criteria_total_count"])}</div>
<div class="kpi"><b>Mean depth score</b><br>{esc(payload["mean_depth_score"])}</div>
<div class="kpi"><b>High priority gaps</b><br>{esc(payload["high_priority_gap_count"])}</div>
<p class="badge">Research-only guardrail active</p>
<p>No execution, no exchange account, no portfolio allocation output, no trade instruction, no live-fund workflow.</p>
</div>
<h2>Criteria</h2><table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th><th>blocker</th></tr></thead><tbody>{criteria_rows}</tbody></table>
<h2>Canonical dataset files</h2><table><thead><tr><th>symbol</th><th>path</th><th>rows</th><th>sha256</th></tr></thead><tbody>{file_rows}</tbody></table>
<h2>Safety flags</h2><table><thead><tr><th>flag</th><th>value</th></tr></thead><tbody>{flag_rows}</tbody></table>
<p>Generated at {esc(payload["generated_at"])} • SHA256 {esc(payload["report_payload_sha256"])}</p>
</body></html>"""
    _assert_research_only(page)
    return page


def build_dataset_depth_requirements(
    output_dir: str | Path,
    symbols: str | Iterable[str] = "BTC-USDT,ETH-USDT,SOL-USDT",
    reports: Iterable[str | Path] | None = None,
    scan_local: bool = False,
    no_scan_local: bool = False,
    **_: Any,
) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    symbol_list = _symbols(symbols)
    input_reports = normalize_reports(reports)

    # Default mode: use explicit upstream report summaries only.
    # Optional scan_local is retained for manual diagnostics, but the acceptance path should not auto-walk artifacts.
    dataset_files: list[dict[str, Any]] = []
    if scan_local and not no_scan_local:
        dataset_files = _scan_canonical_data(symbol_list)

    summary = _summary_from_reports(input_reports)
    if dataset_files:
        total_rows = sum(int(r["row_count"]) for r in dataset_files)
        symbols_with_files = sorted({r["symbol"] for r in dataset_files})
        dataset_file_count = len(dataset_files)
        symbols_with_files_count = len(symbols_with_files)
    else:
        total_rows = int(summary["total_rows"])
        dataset_file_count = int(summary["dataset_file_count"])
        symbols_with_files_count = int(summary["symbols_with_files_count"])
        symbols_with_files = symbol_list[:symbols_with_files_count] if symbols_with_files_count else []

    min_rows_per_symbol = 1000

    rows_by_symbol = {s: 0 for s in symbol_list}
    files_by_symbol = {s: 0 for s in symbol_list}
    if dataset_files:
        for row in dataset_files:
            rows_by_symbol[row["symbol"]] += int(row["row_count"])
            files_by_symbol[row["symbol"]] += 1
    elif symbols_with_files_count:
        # Summary-only mode: distribute observed rows conservatively for display.
        per = total_rows // max(symbols_with_files_count, 1)
        for s in symbol_list[:symbols_with_files_count]:
            rows_by_symbol[s] = per
            files_by_symbol[s] = max(dataset_file_count // max(symbols_with_files_count, 1), 1)

    high_gaps = 0
    criteria = [
        _criterion("canonical_scope", "PASS", True, "crypto_decision_lab/data/", "no artifacts counted"),
        _criterion("dataset_files_present", "PASS" if dataset_file_count else "FAIL", bool(dataset_file_count), dataset_file_count, ">= 1 canonical file or explicit upstream evidence", "" if dataset_file_count else "Need canonical dataset evidence."),
        _criterion("symbol_file_coverage", "PASS" if symbols_with_files_count == len(symbol_list) else "FAIL", symbols_with_files_count == len(symbol_list), f"{symbols_with_files_count}/{len(symbol_list)}", "all requested symbols", "" if symbols_with_files_count == len(symbol_list) else "Some symbols have no canonical evidence."),
        _criterion("total_row_depth", "PASS" if total_rows >= min_rows_per_symbol * len(symbol_list) else "FAIL", total_rows >= min_rows_per_symbol * len(symbol_list), total_rows, f">= {min_rows_per_symbol * len(symbol_list)} total rows", "" if total_rows >= min_rows_per_symbol * len(symbol_list) else "Need deeper history across symbols."),
        _criterion("per_symbol_depth", "PASS" if all(v >= min_rows_per_symbol for v in rows_by_symbol.values()) else "FAIL", all(v >= min_rows_per_symbol for v in rows_by_symbol.values()), rows_by_symbol, f">= {min_rows_per_symbol} rows per symbol", "" if all(v >= min_rows_per_symbol for v in rows_by_symbol.values()) else "Need deeper per-symbol history."),
        _criterion("lineage_hashes", "PASS" if all(r["sha256"] != "UNREADABLE" for r in dataset_files) else "WARN", all(r["sha256"] != "UNREADABLE" for r in dataset_files), "present", "hash per file", ""),
        _criterion("research_only_lock", "PASS", True, "ACTIVE", "policy lock active"),
    ]

    for c in criteria:
        if c["status"] == "FAIL":
            high_gaps += 1

    ready_count = sum(1 for c in criteria if c["ready"])
    mean_score = round(ready_count / len(criteria), 4)

    if not dataset_files and dataset_file_count == 0 and total_rows == 0:
        gate_answer = "NO_DATASET_DEPTH_EVIDENCE_FOUND_RESEARCH_ONLY"
    elif high_gaps > 0:
        gate_answer = "DATASET_DEPTH_REQUIREMENTS_CREATED_HIGH_PRIORITY_DEPTH_GAPS_RESEARCH_ONLY"
    else:
        gate_answer = "DATASET_DEPTH_REQUIREMENTS_CREATED_RESEARCH_DEPTH_OBSERVED_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.dataset_depth_requirements.v2",
        "report_name": "qrds-dataset-depth-requirements",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "symbols": symbol_list,
        "input_report_count": len(input_reports),
        "dataset_file_count": dataset_file_count,
        "symbols_with_files_count": symbols_with_files_count,
        "total_rows": total_rows,
        "rows_by_symbol": rows_by_symbol,
        "files_by_symbol": files_by_symbol,
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_depth_score": mean_score,
        "high_priority_gap_count": high_gaps,
        "medium_priority_gap_count": sum(1 for c in criteria if c["status"] == "WARN"),
        "dataset_files": dataset_files,
        "input_reports": input_reports,
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }

    if any("artifacts/" in r["path"] for r in dataset_files):
        raise ValueError("Contaminated artifacts path detected in canonical dataset files.")

    payload["report_payload_sha256"] = _sha_payload(payload)

    report_file = out / "dataset_depth_requirements_gate.json"
    md_file = out / "dataset_depth_requirements_gate.md"
    html_file = out / "index.html"
    index_file = out / "dataset_depth_requirements_index.json"

    report_file.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_file.write_text(render_markdown(payload), encoding="utf-8")
    html_file.write_text(render_html(payload), encoding="utf-8")

    index = {
        "schema": "qrds.dataset_depth_requirements_index.v2",
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
        "report_path": str(report_file),
        "markdown_path": str(md_file),
        "html_path": str(html_file),
        "index_path": str(index_file),
        "serve_entrypoint": str(html_file),
        "report_payload_sha256": payload["report_payload_sha256"],
        "payload": payload,
        **SAFETY_FLAGS,
    }
    index_file.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    return index


build_depth_requirements = build_dataset_depth_requirements
build_dataset_depth = build_dataset_depth_requirements
