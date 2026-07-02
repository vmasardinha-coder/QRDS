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
    "live order",
)


def _symbols(symbols: str | Iterable[str]) -> list[str]:
    if isinstance(symbols, str):
        return [s.strip() for s in symbols.split(",") if s.strip()]
    return [str(s).strip() for s in symbols if str(s).strip()]


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        if isinstance(value, bool):
            return int(value)
        return int(float(value))
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _repo_root() -> Path:
    here = Path.cwd().resolve()
    for p in [here, *here.parents]:
        if (p / "crypto_decision_lab").exists():
            return p
    return here


def _resolve_report_path(path: str | Path) -> Path:
    p = Path(str(path))
    candidates = [p]
    root = _repo_root()
    candidates.extend([root / p, root / "crypto_decision_lab" / p])
    raw = str(p)
    if raw.startswith("crypto_decision_lab/"):
        stripped = Path(raw.split("/", 1)[1])
        candidates.extend([root / stripped, root / "crypto_decision_lab" / stripped])
    for c in candidates:
        if c.exists():
            return c
    return p


def _load_json(path: str | Path) -> dict[str, Any]:
    resolved = _resolve_report_path(path)
    if not resolved.exists():
        return {"_resolved_path": str(resolved), "status": "MISSING_FILE"}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload["_resolved_path"] = str(resolved)
            payload.setdefault("status", "REPORT_PRESENT")
            return payload
    except Exception as exc:
        return {"_resolved_path": str(resolved), "status": "UNREADABLE_FILE", "error": str(exc)}
    return {"_resolved_path": str(resolved), "status": "UNSUPPORTED_JSON_SHAPE"}


def _nested(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("payload")
    return value if isinstance(value, dict) else {}


def _field(payload: dict[str, Any], *names: str, default: Any = 0) -> Any:
    nested = _nested(payload)
    for name in names:
        if name in payload:
            value = payload.get(name)
            if isinstance(value, list):
                return len(value)
            return value
        if name in nested:
            value = nested.get(name)
            if isinstance(value, list):
                return len(value)
            return value
    return default


def _report_kind(payload: dict[str, Any], path: str | Path) -> str:
    nested = _nested(payload)
    name = str(
        payload.get("report_name")
        or payload.get("schema")
        or nested.get("report_name")
        or nested.get("schema")
        or Path(path).stem
    ).lower().replace("-", "_").replace(".", "_")
    mapping = {
        "dataset_evidence_scan": "dataset_evidence_scan",
        "dataset_evidence_scanner": "dataset_evidence_scan",
        "dataset_evidence_explorer": "dataset_evidence_explorer",
        "dataset_depth_requirements": "dataset_depth_requirements",
        "dataset_manifest": "dataset_manifest",
        "data_profile": "data_profile",
        "data_readiness": "data_readiness",
        "data_gap_remediation": "data_gap_remediation",
        "data_coverage": "data_coverage",
        "data_quality": "data_quality",
        "data_audit": "data_audit",
    }
    for needle, kind in mapping.items():
        if needle in name:
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
    for item in reports:
        payload = _load_json(item)
        resolved = str(payload.get("_resolved_path") or item)
        if resolved in seen:
            continue
        seen.add(resolved)
        kind = _report_kind(payload, resolved)
        rows.append(
            {
                "kind": kind,
                "path": resolved,
                "status": payload.get("status", "REPORT_PRESENT"),
                "gate_answer": str(_field(payload, "gate_answer", default="UNKNOWN_RESEARCH_ONLY")),
                "dataset_file_count": _safe_int(_field(payload, "dataset_file_count", "dataset_files", default=0)),
                "symbols_with_files": _safe_int(_field(payload, "symbols_with_files", "symbols_with_files_count", default=0)),
                "total_rows": _safe_int(_field(payload, "total_rows", "total_observed_rows", "row_count", default=0)),
                "mean_score": _safe_float(
                    _field(
                        payload,
                        "mean_depth_score",
                        "mean_scanner_score",
                        "mean_explorer_score",
                        "mean_readiness_score",
                        "mean_profile_score",
                        default=0.0,
                    )
                ),
                "payload": payload,
            }
        )
    return rows


def _symbol_from_text(value: Any, symbols: list[str]) -> str | None:
    low = str(value).lower().replace("_", "-")
    for s in symbols:
        token = s.lower().replace("_", "-")
        if token in low or token.replace("-", "") in low.replace("-", ""):
            return s
    return None


def _rows_by_symbol_from_payload(payload: dict[str, Any], symbols: list[str]) -> dict[str, int]:
    nested = _nested(payload)
    result = {s: 0 for s in symbols}

    rows_by_symbol = payload.get("rows_by_symbol") or nested.get("rows_by_symbol")
    if isinstance(rows_by_symbol, dict):
        for k, v in rows_by_symbol.items():
            s = _symbol_from_text(k, symbols)
            if s:
                result[s] = max(result[s], _safe_int(v))

    for key in ("symbol_profiles", "dataset_rows"):
        value = payload.get(key) or nested.get(key)
        if isinstance(value, list):
            for item in value:
                if not isinstance(item, dict):
                    continue
                s = _symbol_from_text(item.get("symbol") or item.get("path") or "", symbols)
                if not s:
                    continue
                result[s] += _safe_int(item.get("row_count") or item.get("rows") or item.get("total_rows"))

    return result


def _observed_rows_by_symbol(input_reports: list[dict[str, Any]], symbols: list[str]) -> dict[str, int]:
    observed = {s: 0 for s in symbols}
    preferred = [
        r for r in input_reports
        if r.get("kind") in {"dataset_evidence_scan", "dataset_evidence_explorer", "dataset_depth_requirements"}
    ] or input_reports

    for row in preferred:
        extracted = _rows_by_symbol_from_payload(row.get("payload") or {}, symbols)
        for s in symbols:
            observed[s] = max(observed[s], extracted.get(s, 0))

    total = max([_safe_int(r.get("total_rows")) for r in preferred] or [0])
    symbols_with = max([_safe_int(r.get("symbols_with_files")) for r in preferred] or [0])
    if total > 0 and all(v == 0 for v in observed.values()) and symbols_with:
        per = total // max(symbols_with, 1)
        for s in symbols[:symbols_with]:
            observed[s] = per

    return observed


def _source_summary(input_reports: list[dict[str, Any]]) -> dict[str, int]:
    preferred = [
        r for r in input_reports
        if r.get("kind") in {"dataset_evidence_scan", "dataset_evidence_explorer", "dataset_depth_requirements"}
    ] or input_reports
    return {
        "dataset_file_count": max([_safe_int(r.get("dataset_file_count")) for r in preferred] or [0]),
        "symbols_with_files": max([_safe_int(r.get("symbols_with_files")) for r in preferred] or [0]),
        "total_rows": max([_safe_int(r.get("total_rows")) for r in preferred] or [0]),
    }


def _priority(gap: int, target: int) -> str:
    if gap <= 0:
        return "LOW"
    ratio = gap / max(target, 1)
    if ratio >= 0.75:
        return "HIGH"
    if ratio >= 0.25:
        return "MEDIUM"
    return "LOW"


def _build_actions(symbols: list[str], observed: dict[str, int], min_rows_per_symbol: int, interval: str) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for symbol in symbols:
        obs = _safe_int(observed.get(symbol))
        gap = max(min_rows_per_symbol - obs, 0)
        slug = symbol.lower().replace("-", "_")
        actions.append(
            {
                "symbol": symbol,
                "interval": interval,
                "observed_rows": obs,
                "target_rows": min_rows_per_symbol,
                "gap_rows": gap,
                "priority": _priority(gap, min_rows_per_symbol),
                "target_path_pattern": f"crypto_decision_lab/data/research/{slug}_{interval}_*.jsonl",
                "required_fields": ["timestamp", "open", "high", "low", "close", "volume", "source", "interval", "symbol"],
                "acceptance_checks": [
                    "monotonic timestamps",
                    "duplicate timestamp scan",
                    "null-rate sample",
                    "source and interval metadata",
                    "sha256 lineage capture",
                    "research-only fixture/cache classification",
                ],
            }
        )
    return actions


def _criterion(criterion_id: str, status: str, ready: bool, observed: Any, threshold: str, blocker: str = "") -> dict[str, Any]:
    return {
        "criterion_id": criterion_id,
        "status": status,
        "ready": bool(ready),
        "observed": observed,
        "threshold": threshold,
        "blocker": blocker,
    }


def _build_criteria(input_reports: list[dict[str, Any]], actions: list[dict[str, Any]], summary: dict[str, int]) -> list[dict[str, Any]]:
    high_gaps = sum(1 for a in actions if a["priority"] == "HIGH")
    medium_gaps = sum(1 for a in actions if a["priority"] == "MEDIUM")
    return [
        _criterion(
            "upstream_evidence_present",
            "PASS" if input_reports else "FAIL",
            bool(input_reports),
            len(input_reports),
            ">= 1 explicit upstream report",
            "Need 9K/9L/9M reports." if not input_reports else "",
        ),
        _criterion(
            "symbol_coverage_observed",
            "PASS" if summary["symbols_with_files"] >= len(actions) else "WARN",
            summary["symbols_with_files"] >= len(actions),
            f"{summary['symbols_with_files']}/{len(actions)}",
            "all requested symbols represented",
            "Some symbols need explicit dataset evidence." if summary["symbols_with_files"] < len(actions) else "",
        ),
        _criterion(
            "row_depth_gap_computed",
            "PASS" if actions else "FAIL",
            bool(actions),
            sum(a["gap_rows"] for a in actions),
            "gap rows computed per symbol",
            "Need symbol target plan." if not actions else "",
        ),
        _criterion(
            "high_priority_gap_state",
            "WARN" if high_gaps else "PASS",
            high_gaps == 0,
            high_gaps,
            "0 high priority depth gaps for mature data readiness",
            "High priority depth expansion remains." if high_gaps else "",
        ),
        _criterion(
            "lineage_requirements_defined",
            "PASS",
            True,
            "sha256/source/interval/timestamp checks",
            "lineage requirements present",
            "",
        ),
        _criterion(
            "refresh_policy_defined",
            "PASS",
            True,
            "offline/public/cache fixture workflow only",
            "refresh policy present",
            "",
        ),
        _criterion(
            "research_only_lock",
            "PASS",
            True,
            "ACTIVE",
            "policy lock active",
            "",
        ),
    ]


def _sha_payload(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _assert_research_only(rendered: str) -> None:
    low = rendered.lower()
    for term in FORBIDDEN_RENDERED_PHRASES:
        if term in low:
            raise ValueError(f"Operational language is not allowed in Data Acquisition Depth Plan: {term}")


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(x) for x in row) + "|")
    return "\n".join(out)


def render_markdown(payload: dict[str, Any]) -> str:
    md = f"""# QRDS/QOS • Gate BTC • Research-only
## Data Acquisition / Depth Expansion Plan

Formal research-data depth expansion plan. This artifact transforms observed depth gaps into dataset collection requirements. It cannot unlock operational use.

**Gate answer:** {payload['gate_answer']}

**Policy lock:** {payload['policy_lock']} • **Mode:** {payload['app_mode']}

## Summary

- Input reports: {payload['input_report_count']}
- Dataset files observed upstream: {payload['dataset_file_count']}
- Symbols with files: {payload['symbols_with_files']}/{len(payload['symbols'])}
- Total observed rows: {payload['total_rows']}
- Target rows per symbol: {payload['min_rows_per_symbol']}
- High priority gaps: {payload['high_priority_gap_count']}
- Medium priority gaps: {payload['medium_priority_gap_count']}
- Criteria ready: {payload['criteria_ready_count']}/{payload['criteria_total_count']}
- Mean plan score: {payload['mean_plan_score']}

Research-only guardrail: no exchange account, no orders, no portfolio allocation output, no executable instruction, no live-fund workflow.

## Depth expansion actions

{_table(
    ['symbol', 'interval', 'observed_rows', 'target_rows', 'gap_rows', 'priority', 'target_path_pattern'],
    [[a['symbol'], a['interval'], a['observed_rows'], a['target_rows'], a['gap_rows'], a['priority'], a['target_path_pattern']] for a in payload['actions']],
)}

## Criteria

{_table(
    ['criterion_id', 'status', 'ready', 'observed', 'threshold', 'blocker'],
    [[c['criterion_id'], c['status'], c['ready'], c['observed'], c['threshold'], c['blocker']] for c in payload['criteria']],
)}

## Input reports

{_table(
    ['kind', 'status', 'dataset_files', 'symbols_with_files', 'total_rows', 'path'],
    [[r['kind'], r['status'], r['dataset_file_count'], r['symbols_with_files'], r['total_rows'], r['path']] for r in payload['input_reports']] or [['NONE', 'MISSING', 0, 0, 0, 'MISSING']],
)}

## Safety flags

{_table(['flag', 'value'], [[k, v] for k, v in SAFETY_FLAGS.items()])}

Generated at {payload['generated_at']} • SHA256 {payload['report_payload_sha256']}
"""
    _assert_research_only(md)
    return md


def render_html(payload: dict[str, Any]) -> str:
    def esc(x: Any) -> str:
        return html.escape(str(x))

    action_rows = "\n".join(
        f"<tr><td>{esc(a['symbol'])}</td><td>{esc(a['interval'])}</td><td>{esc(a['observed_rows'])}</td><td>{esc(a['target_rows'])}</td><td>{esc(a['gap_rows'])}</td><td>{esc(a['priority'])}</td><td><code>{esc(a['target_path_pattern'])}</code></td></tr>"
        for a in payload["actions"]
    )
    criteria_rows = "\n".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td><td>{esc(c['blocker'])}</td></tr>"
        for c in payload["criteria"]
    )
    report_rows = "\n".join(
        f"<tr><td>{esc(r['kind'])}</td><td>{esc(r['status'])}</td><td>{esc(r['dataset_file_count'])}</td><td>{esc(r['symbols_with_files'])}</td><td>{esc(r['total_rows'])}</td><td><code>{esc(r['path'])}</code></td></tr>"
        for r in payload["input_reports"]
    ) or "<tr><td>NONE</td><td>MISSING</td><td>0</td><td>0</td><td>0</td><td>MISSING</td></tr>"
    flag_rows = "\n".join(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>" for k, v in SAFETY_FLAGS.items())

    page = f"""<!doctype html><html><head><meta charset='utf-8'><title>QRDS Data Acquisition Depth Plan</title>
<style>
body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}
.card{{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}}
.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px 8px 8px 0}}
table{{border-collapse:collapse;width:100%;background:white;margin:14px 0}} th,td{{border:1px solid #d9deea;padding:8px;text-align:left;font-size:14px}} th{{background:#eef2ff}}
.badge{{display:inline-block;background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}}
</style></head><body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1>
<h2>Data Acquisition / Depth Expansion Plan</h2>
<p>Formal research-data depth expansion plan. This artifact turns observed depth gaps into dataset collection requirements. It cannot unlock operational use.</p>
<div class='card'>
<p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p>
<p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>
<div class='kpi'><b>Input reports</b><br>{esc(payload['input_report_count'])}</div>
<div class='kpi'><b>Dataset files observed</b><br>{esc(payload['dataset_file_count'])}</div>
<div class='kpi'><b>Symbols with files</b><br>{esc(payload['symbols_with_files'])}/{esc(len(payload['symbols']))}</div>
<div class='kpi'><b>Total rows</b><br>{esc(payload['total_rows'])}</div>
<div class='kpi'><b>Target rows/symbol</b><br>{esc(payload['min_rows_per_symbol'])}</div>
<div class='kpi'><b>High priority gaps</b><br>{esc(payload['high_priority_gap_count'])}</div>
<div class='kpi'><b>Criteria ready</b><br>{esc(payload['criteria_ready_count'])}/{esc(payload['criteria_total_count'])}</div>
<div class='kpi'><b>Mean plan score</b><br>{esc(payload['mean_plan_score'])}</div>
<p class='badge'>Research-only guardrail active</p>
<p>No exchange account, no orders, no portfolio allocation output, no executable instruction, no live-fund workflow.</p>
</div>
<h2>Depth expansion actions</h2><table><thead><tr><th>symbol</th><th>interval</th><th>observed rows</th><th>target rows</th><th>gap rows</th><th>priority</th><th>target path pattern</th></tr></thead><tbody>{action_rows}</tbody></table>
<h2>Criteria</h2><table><thead><tr><th>criterion</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th><th>blocker</th></tr></thead><tbody>{criteria_rows}</tbody></table>
<h2>Input reports</h2><table><thead><tr><th>kind</th><th>status</th><th>dataset files</th><th>symbols with files</th><th>total rows</th><th>path</th></tr></thead><tbody>{report_rows}</tbody></table>
<h2>Safety flags</h2><table><thead><tr><th>flag</th><th>value</th></tr></thead><tbody>{flag_rows}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p>
</body></html>"""
    _assert_research_only(page)
    return page


def build_data_acquisition_depth_plan(
    output_dir: str | Path,
    symbols: str | Iterable[str] = "BTC-USDT,ETH-USDT,SOL-USDT",
    reports: Iterable[str | Path] | None = None,
    min_rows_per_symbol: int = 5000,
    interval: str = "1h",
    **_: Any,
) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    symbol_list = _symbols(symbols)
    input_reports = normalize_reports(reports)
    summary = _source_summary(input_reports)
    observed = _observed_rows_by_symbol(input_reports, symbol_list)
    actions = _build_actions(symbol_list, observed, int(min_rows_per_symbol), interval)
    criteria = _build_criteria(input_reports, actions, summary)
    ready_count = sum(1 for c in criteria if c["ready"])
    high_gaps = sum(1 for a in actions if a["priority"] == "HIGH")
    medium_gaps = sum(1 for a in actions if a["priority"] == "MEDIUM")
    mean_score = round(ready_count / len(criteria), 4) if criteria else 0.0

    if not input_reports:
        gate_answer = "NO_DATA_ACQUISITION_DEPTH_PLAN_NO_INPUT_REPORTS_RESEARCH_ONLY"
    elif high_gaps:
        gate_answer = "DATA_ACQUISITION_DEPTH_PLAN_HIGH_PRIORITY_GAPS_RESEARCH_ONLY"
    elif medium_gaps:
        gate_answer = "DATA_ACQUISITION_DEPTH_PLAN_MEDIUM_PRIORITY_GAPS_RESEARCH_ONLY"
    else:
        gate_answer = "DATA_ACQUISITION_DEPTH_PLAN_REQUIREMENTS_OBSERVED_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.data_acquisition_depth_plan.v1",
        "report_name": "qrds-data-acquisition-depth-plan",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "symbols": symbol_list,
        "interval": interval,
        "min_rows_per_symbol": int(min_rows_per_symbol),
        "input_report_count": len(input_reports),
        "dataset_file_count": summary["dataset_file_count"],
        "symbols_with_files": summary["symbols_with_files"],
        "total_rows": summary["total_rows"],
        "observed_rows_by_symbol": observed,
        "actions": actions,
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_plan_score": mean_score,
        "high_priority_gap_count": high_gaps,
        "medium_priority_gap_count": medium_gaps,
        "input_reports": [{k: v for k, v in r.items() if k != "payload"} for r in input_reports],
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    report_path = out / "data_acquisition_depth_plan.json"
    md_path = out / "data_acquisition_depth_plan.md"
    html_path = out / "index.html"
    index_path = out / "data_acquisition_depth_plan_index.json"

    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")
    index = {
        "schema": "qrds.data_acquisition_depth_plan_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "symbols": payload["symbols"],
        "input_report_count": payload["input_report_count"],
        "dataset_file_count": payload["dataset_file_count"],
        "symbols_with_files": payload["symbols_with_files"],
        "total_rows": payload["total_rows"],
        "min_rows_per_symbol": payload["min_rows_per_symbol"],
        "high_priority_gap_count": payload["high_priority_gap_count"],
        "medium_priority_gap_count": payload["medium_priority_gap_count"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_plan_score": payload["mean_plan_score"],
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


build_plan = build_data_acquisition_depth_plan
