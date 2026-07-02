from __future__ import annotations

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


def _symbols(symbols: str | Iterable[str]) -> list[str]:
    if isinstance(symbols, str):
        return [s.strip() for s in symbols.split(",") if s.strip()]
    return [str(s).strip() for s in symbols if str(s).strip()]


def _repo_tolerant_path(path: str | Path) -> Path:
    p = Path(path)
    if p.exists():
        return p
    candidates = [Path.cwd() / p, Path.cwd().parent / p]
    raw = str(p)
    if raw.startswith("crypto_decision_lab/"):
        stripped = Path(raw.split("/", 1)[1])
        candidates.extend([Path.cwd() / stripped, Path.cwd().parent / stripped])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return p


def _load_json(path: str | Path) -> dict[str, Any]:
    p = _repo_tolerant_path(path)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {
        "report_name": Path(path).stem,
        "gate_answer": "UNREADABLE_INPUT_RESEARCH_ARTIFACT",
        "report_payload_sha256": "UNREADABLE",
    }


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def _extract_metric(payload: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in payload and payload[name] not in (None, ""):
            return payload[name]
    nested_candidates = [
        payload.get("payload"),
        payload.get("data_audit"),
        payload.get("dataset_audit"),
        payload.get("coverage"),
    ]
    for nested in nested_candidates:
        if isinstance(nested, dict):
            for name in names:
                if name in nested and nested[name] not in (None, ""):
                    return nested[name]
    return default


def _report_kind(payload: dict[str, Any], path: str | Path) -> str:
    name = str(payload.get("report_name") or payload.get("schema") or Path(path).stem)
    low = name.lower().replace("-", "_").replace(".", "_")
    mapping = {
        "evidence_quality": "evidence_quality",
        "evidence_drilldown": "evidence_drilldown",
        "evidence_timeline": "evidence_timeline",
        "research_promotion": "research_promotion",
        "human_review": "human_review",
        "oos_validation": "oos_validation",
        "paper_trading": "paper_trading",
        "risk_model": "risk_model",
        "operational_security": "operational_security",
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


def normalize_reports(reports: Iterable[str | Path] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not reports:
        return rows
    seen: set[str] = set()
    for report in reports:
        p = _repo_tolerant_path(report)
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        payload = _load_json(p)
        exists = p.exists()
        rows.append(
            {
                "kind": _report_kind(payload, p),
                "path": str(p),
                "status": "REPORT_PRESENT" if exists else "MISSING_FILE",
                "gate_answer": str(payload.get("gate_answer") or "UNKNOWN_RESEARCH_ONLY"),
                "sha256": str(payload.get("report_payload_sha256") or payload.get("sha256") or "MISSING")[:16],
                "dataset_row_count": _as_int(_extract_metric(payload, "dataset_row_count", "row_count", "rows", default=0)),
                "split_count": _as_int(_extract_metric(payload, "split_count", "walk_forward_split_count", "walk_forward_splits", default=0)),
                "null_rate": _as_float(_extract_metric(payload, "null_rate", "missing_rate", default=0.0)),
                "duplicate_rate": _as_float(_extract_metric(payload, "duplicate_rate", default=0.0)),
                "gap_count": _as_int(_extract_metric(payload, "gap_count", "time_gap_count", default=0)),
                "freshness_lag_hours": _as_float(_extract_metric(payload, "freshness_lag_hours", "data_lag_hours", default=0.0)),
                "score": _as_float(
                    _extract_metric(
                        payload,
                        "mean_quality_score",
                        "mean_coverage_score",
                        "mean_research_readiness_score",
                        "mean_symbol_evidence_score",
                        "mean_latest_score",
                        "mean_risk_score",
                        "mean_security_score",
                        "mean_oos_score",
                        "mean_paper_score",
                        "mean_score",
                        default=0.0,
                    )
                ),
            }
        )
    return rows


def normalize_dataset_manifests(dataset_manifests: Iterable[str | Path] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not dataset_manifests:
        return rows
    seen: set[str] = set()
    for manifest in dataset_manifests:
        p = _repo_tolerant_path(manifest)
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        payload = _load_json(p)
        rows.append(
            {
                "path": str(p),
                "status": "MANIFEST_PRESENT" if p.exists() else "MISSING_FILE",
                "symbol": str(payload.get("symbol") or payload.get("asset") or "UNKNOWN"),
                "row_count": _as_int(_extract_metric(payload, "row_count", "dataset_row_count", "rows", default=0)),
                "start_time": str(payload.get("start_time") or payload.get("start") or "UNKNOWN"),
                "end_time": str(payload.get("end_time") or payload.get("end") or "UNKNOWN"),
                "null_rate": _as_float(_extract_metric(payload, "null_rate", "missing_rate", default=0.0)),
                "duplicate_rate": _as_float(_extract_metric(payload, "duplicate_rate", default=0.0)),
                "gap_count": _as_int(_extract_metric(payload, "gap_count", "time_gap_count", default=0)),
                "split_count": _as_int(_extract_metric(payload, "split_count", "walk_forward_split_count", default=0)),
                "sha256": str(payload.get("sha256") or payload.get("dataset_sha256") or "MISSING")[:16],
            }
        )
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


def _build_criteria(report_rows: list[dict[str, Any]], manifest_rows: list[dict[str, Any]], symbols: list[str]) -> list[dict[str, Any]]:
    readable_reports = sum(1 for r in report_rows if r["status"] == "REPORT_PRESENT")
    manifest_count = sum(1 for r in manifest_rows if r["status"] == "MANIFEST_PRESENT")
    max_rows = max([r["dataset_row_count"] for r in report_rows] + [r["row_count"] for r in manifest_rows] + [0])
    max_splits = max([r["split_count"] for r in report_rows] + [r["split_count"] for r in manifest_rows] + [0])
    max_gap_count = max([r["gap_count"] for r in report_rows] + [r["gap_count"] for r in manifest_rows] + [0])
    max_null_rate = max([r["null_rate"] for r in report_rows] + [r["null_rate"] for r in manifest_rows] + [0.0])
    max_duplicate_rate = max([r["duplicate_rate"] for r in report_rows] + [r["duplicate_rate"] for r in manifest_rows] + [0.0])
    hash_present = any(r["sha256"] not in ("MISSING", "UNREADABLE") for r in report_rows + manifest_rows)
    prior_avg = sum(r["score"] for r in report_rows) / len(report_rows) if report_rows else 0.0

    return [
        _criterion(
            "upstream_report_readability",
            "PASS" if readable_reports >= 7 else "FAIL",
            readable_reports >= 7,
            readable_reports,
            ">= 7 readable upstream reports",
            "" if readable_reports >= 7 else "Need readable upstream research artifacts.",
        ),
        _criterion(
            "dataset_manifest_presence",
            "PASS" if manifest_count >= len(symbols) and symbols else "WARN",
            manifest_count >= len(symbols) and bool(symbols),
            f"{manifest_count}/{len(symbols)}",
            "one explicit dataset manifest per symbol preferred",
            "Need explicit dataset profiling manifests for each research symbol.",
        ),
        _criterion(
            "explicit_row_coverage",
            "PASS" if max_rows >= 1000 else "WARN",
            max_rows >= 1000,
            max_rows,
            ">= 1000 rows observed in reports or manifests",
            "Need explicit row coverage from the dataset pipeline.",
        ),
        _criterion(
            "explicit_split_coverage",
            "PASS" if max_splits >= 6 else "WARN",
            max_splits >= 6,
            max_splits,
            ">= 6 walk-forward splits observed",
            "Need explicit split evidence from the research runner.",
        ),
        _criterion(
            "missing_value_audit",
            "PASS" if manifest_count > 0 and max_null_rate <= 0.01 else "WARN",
            manifest_count > 0 and max_null_rate <= 0.01,
            round(max_null_rate, 6),
            "<= 1% maximum missing-value rate preferred",
            "Need formal missing-value audit evidence.",
        ),
        _criterion(
            "duplicate_bar_audit",
            "PASS" if manifest_count > 0 and max_duplicate_rate == 0 else "WARN",
            manifest_count > 0 and max_duplicate_rate == 0,
            round(max_duplicate_rate, 6),
            "0 duplicate-rate preferred",
            "Need formal duplicate-bar audit evidence.",
        ),
        _criterion(
            "time_gap_audit",
            "PASS" if manifest_count > 0 and max_gap_count == 0 else "WARN",
            manifest_count > 0 and max_gap_count == 0,
            max_gap_count,
            "0 unexplained time gaps preferred",
            "Need explicit time-continuity audit evidence.",
        ),
        _criterion(
            "lineage_hash_presence",
            "PASS" if hash_present else "FAIL",
            hash_present,
            "present" if hash_present else "missing",
            "hashes present for traceability",
            "Need hashes for reproducible research lineage.",
        ),
        _criterion(
            "prior_stack_quality_context",
            "PASS" if prior_avg >= 0.60 else "WARN",
            prior_avg >= 0.60,
            round(prior_avg, 4),
            ">= 0.60 average upstream research score preferred",
            "Need stronger upstream research context before audit promotion is useful.",
        ),
    ]


def _sha(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _assert_research_only(rendered: str) -> None:
    low = rendered.lower()
    for term in FORBIDDEN_RENDERED_PHRASES:
        if term in low:
            raise ValueError(f"Operational language is not allowed in Data Audit Evidence Pack: {term}")


def _render_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(x) for x in row) + "|")
    return "\n".join(out)


def render_markdown(payload: dict[str, Any]) -> str:
    md = f"""# QRDS/QOS • Gate BTC • Research-only
## Data Audit Evidence Pack

Formal research-data audit packet for the evidence stack. This page records profiling, lineage, and blockers; it cannot unlock operational use.

**Gate answer:** {payload['gate_answer']}

**Policy lock:** {payload['policy_lock']} • **Mode:** {payload['app_mode']}

## Summary

- Input reports: {payload['input_report_count']}
- Dataset manifests: {payload['dataset_manifest_count']}/{len(payload['symbols'])}
- Criteria ready: {payload['criteria_ready_count']}/{payload['criteria_total_count']}
- Mean audit score: {payload['mean_audit_score']}
- Symbols: {', '.join(payload['symbols'])}

Research-only guardrail: no execution, no exchange account, no allocation output, no live-fund workflow.

## Audit criteria

{_render_table(
    ['criterion_id', 'status', 'ready', 'observed', 'threshold', 'blocker'],
    [[c['criterion_id'], c['status'], c['ready'], c['observed'], c['threshold'], c['blocker']] for c in payload['criteria']],
)}

## Input reports

{_render_table(
    ['kind', 'status', 'gate_answer', 'sha256'],
    [[r['kind'], r['status'], r['gate_answer'], r['sha256']] for r in payload['input_reports']] if payload['input_reports'] else [['NONE', 'MISSING', 'MISSING_INPUT_REPORT', 'MISSING']],
)}

## Dataset manifests

{_render_table(
    ['symbol', 'status', 'rows', 'splits', 'null_rate', 'duplicate_rate', 'gap_count', 'sha256'],
    [[r['symbol'], r['status'], r['row_count'], r['split_count'], r['null_rate'], r['duplicate_rate'], r['gap_count'], r['sha256']] for r in payload['dataset_manifests']] if payload['dataset_manifests'] else [['NONE', 'MISSING', 0, 0, 0.0, 0.0, 0, 'MISSING']],
)}

## Safety flags

{_render_table(['flag', 'value'], [[k, v] for k, v in payload['safety_flags'].items()])}

Generated at {payload['generated_at']} • SHA256 {payload['report_payload_sha256']}
"""
    _assert_research_only(md)
    return md


def render_html(payload: dict[str, Any]) -> str:
    def esc(value: Any) -> str:
        return html.escape(str(value))

    criteria_rows = "\n".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td><td>{esc(c['blocker'])}</td></tr>"
        for c in payload['criteria']
    )
    report_rows = "\n".join(
        f"<tr><td>{esc(r['kind'])}</td><td>{esc(r['status'])}</td><td>{esc(r['gate_answer'])}</td><td>{esc(r['sha256'])}</td></tr>"
        for r in payload['input_reports']
    ) or "<tr><td>NONE</td><td>MISSING</td><td>MISSING_INPUT_REPORT</td><td>MISSING</td></tr>"
    manifest_rows = "\n".join(
        f"<tr><td>{esc(r['symbol'])}</td><td>{esc(r['status'])}</td><td>{esc(r['row_count'])}</td><td>{esc(r['split_count'])}</td><td>{esc(r['null_rate'])}</td><td>{esc(r['duplicate_rate'])}</td><td>{esc(r['gap_count'])}</td><td>{esc(r['sha256'])}</td></tr>"
        for r in payload['dataset_manifests']
    ) or "<tr><td>NONE</td><td>MISSING</td><td>0</td><td>0</td><td>0.0</td><td>0.0</td><td>0</td><td>MISSING</td></tr>"
    flag_rows = "\n".join(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>" for k, v in payload['safety_flags'].items())

    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>QRDS Data Audit Evidence Pack</title>
<style>
body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}
.card{{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px 8px 8px 0}}
table{{border-collapse:collapse;width:100%;background:white;margin:12px 0}}
th,td{{border:1px solid #d9deea;padding:8px;text-align:left;font-size:14px}}
th{{background:#eef2ff}}
.badge{{display:inline-block;border-radius:999px;background:#fee2e2;padding:6px 10px;font-weight:700}}
</style></head><body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1>
<h2>Data Audit Evidence Pack</h2>
<p>Formal research-data audit packet for the evidence stack. This page records profiling, lineage, and blockers; it cannot unlock operational use.</p>
<div class="card">
<p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p>
<p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>
<div class="kpi"><b>Input reports</b><br>{esc(payload['input_report_count'])}</div>
<div class="kpi"><b>Dataset manifests</b><br>{esc(payload['dataset_manifest_count'])}/{esc(len(payload['symbols']))}</div>
<div class="kpi"><b>Criteria ready</b><br>{esc(payload['criteria_ready_count'])}/{esc(payload['criteria_total_count'])}</div>
<div class="kpi"><b>Mean audit score</b><br>{esc(payload['mean_audit_score'])}</div>
<div class="kpi"><b>Symbols</b><br>{esc(', '.join(payload['symbols']))}</div>
<p class="badge">Research-only guardrail active</p>
<p>No execution, no exchange account, no allocation output, no live-fund workflow.</p>
</div>
<h2>Audit criteria</h2><table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th><th>blocker</th></tr></thead><tbody>{criteria_rows}</tbody></table>
<h2>Input reports</h2><table><thead><tr><th>kind</th><th>status</th><th>gate_answer</th><th>sha256</th></tr></thead><tbody>{report_rows}</tbody></table>
<h2>Dataset manifests</h2><table><thead><tr><th>symbol</th><th>status</th><th>rows</th><th>splits</th><th>null_rate</th><th>duplicate_rate</th><th>gap_count</th><th>sha256</th></tr></thead><tbody>{manifest_rows}</tbody></table>
<h2>Safety flags</h2><table><thead><tr><th>flag</th><th>value</th></tr></thead><tbody>{flag_rows}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p>
</body></html>"""
    _assert_research_only(page)
    return page


def build_data_audit(
    output_dir: str | Path,
    symbols: str | Iterable[str],
    reports: Iterable[str | Path] | None = None,
    dataset_manifests: Iterable[str | Path] | None = None,
) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    symbol_list = _symbols(symbols)
    input_reports = normalize_reports(reports)
    manifest_rows = normalize_dataset_manifests(dataset_manifests)
    criteria = _build_criteria(input_reports, manifest_rows, symbol_list)
    ready_count = sum(1 for c in criteria if c['ready'])
    total_count = len(criteria)
    mean_score = round(ready_count / total_count if total_count else 0.0, 4)

    if not input_reports:
        gate_answer = "NO_DATA_AUDIT_NO_INPUT_REPORTS_RESEARCH_ONLY"
    elif not manifest_rows:
        gate_answer = "DATA_AUDIT_EVIDENCE_INCOMPLETE_DATASET_MANIFESTS_REQUIRED_RESEARCH_ONLY"
    elif mean_score >= 0.80:
        gate_answer = "DATA_AUDIT_PARTIAL_EVIDENCE_READY_FOR_RESEARCH_REVIEW_ONLY"
    else:
        gate_answer = "DATA_AUDIT_EVIDENCE_INCOMPLETE_MORE_PROFILING_REQUIRED_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.data_audit_evidence_pack.v1",
        "report_name": "qrds-data-audit-evidence-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "symbols": symbol_list,
        "input_report_count": len(input_reports),
        "dataset_manifest_count": len(manifest_rows),
        "criteria_ready_count": ready_count,
        "criteria_total_count": total_count,
        "mean_audit_score": mean_score,
        "formal_data_audit_ready": "NO",
        "criteria": criteria,
        "input_reports": input_reports,
        "dataset_manifests": manifest_rows,
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload['report_payload_sha256'] = _sha(payload)

    report_path = out / "data_audit_evidence_pack.json"
    markdown_path = out / "data_audit_evidence_pack.md"
    html_path = out / "index.html"
    index_path = out / "data_audit_index.json"

    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    index = {
        "schema": "qrds.data_audit_index.v1",
        "report_name": payload['report_name'],
        "generated_at": payload['generated_at'],
        "gate_answer": payload['gate_answer'],
        "policy_lock": payload['policy_lock'],
        "app_mode": payload['app_mode'],
        "symbols": payload['symbols'],
        "input_report_count": payload['input_report_count'],
        "dataset_manifest_count": payload['dataset_manifest_count'],
        "criteria_ready_count": payload['criteria_ready_count'],
        "criteria_total_count": payload['criteria_total_count'],
        "mean_audit_score": payload['mean_audit_score'],
        "report_path": str(report_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "index_path": str(index_path),
        "serve_entrypoint": str(html_path),
        "report_payload_sha256": payload['report_payload_sha256'],
        **SAFETY_FLAGS,
    }
    index['payload'] = payload
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    return index
