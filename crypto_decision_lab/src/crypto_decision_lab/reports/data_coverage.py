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


def _resolve_report_path(path: str | Path) -> Path:
    """Resolve report paths from repo root or package cwd.

    Wrappers may pass paths like crypto_decision_lab/artifacts/...
    while the CLI may run from /workspaces/QRDS/crypto_decision_lab.
    This resolver keeps the Python layer tolerant without auto-discovering reports.
    """
    p = Path(path)
    if p.exists():
        return p

    candidates = [
        Path.cwd() / p,
        Path.cwd().parent / p,
        Path.cwd() / "crypto_decision_lab" / p,
        Path.cwd().parent / "crypto_decision_lab" / p,
    ]

    raw = str(p)
    if raw.startswith("crypto_decision_lab/"):
        stripped = Path(raw.split("/", 1)[1])
        candidates.extend([
            Path.cwd() / stripped,
            Path.cwd().parent / stripped,
        ])

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return p


def _load_json(path: str | Path) -> dict[str, Any]:
    p = _resolve_report_path(path)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {
            "report_name": p.stem,
            "gate_answer": "UNREADABLE_INPUT_REPORT_RESEARCH_ONLY",
            "ready": False,
            "report_payload_sha256": "UNREADABLE",
        }


def _report_kind(payload: dict[str, Any], path: str | Path) -> str:
    name = str(payload.get("report_name") or payload.get("schema") or Path(path).stem)
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
        "evidence_stack": "evidence_stack",
    }
    low = name.lower().replace("-", "_").replace(".", "_")
    for needle, kind in mapping.items():
        if needle in low:
            return kind
    fallback = Path(path).stem.lower().replace("-", "_").replace(".", "_")
    for needle, kind in mapping.items():
        if needle in fallback:
            return kind
    return fallback


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def _collect_reports(reports: Iterable[str | Path] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not reports:
        return rows

    seen: set[str] = set()
    for report in reports:
        p = _resolve_report_path(report)
        key = str(p)
        if key in seen:
            continue
        seen.add(key)

        payload = _load_json(p)
        rows.append(
            {
                "kind": _report_kind(payload, p),
                "path": str(p),
                "status": "REPORT_PRESENT" if p.exists() else "MISSING_FILE",
                "ready": bool(payload.get("ready") or payload.get("formal_oos_ready") == "YES"),
                "gate_answer": str(payload.get("gate_answer") or "UNKNOWN_RESEARCH_ONLY"),
                "score": _as_float(
                    payload.get("mean_coverage_score")
                    or payload.get("mean_research_readiness_score")
                    or payload.get("mean_symbol_evidence_score")
                    or payload.get("mean_latest_score")
                    or payload.get("mean_risk_score")
                    or payload.get("mean_security_score")
                    or payload.get("mean_oos_score")
                    or payload.get("mean_paper_score")
                    or payload.get("mean_score")
                    or 0.0
                ),
                "dataset_row_count": _as_int(payload.get("dataset_row_count") or payload.get("row_count") or 0),
                "split_count": _as_int(payload.get("split_count") or payload.get("walk_forward_split_count") or 0),
                "sha256": str(payload.get("report_payload_sha256") or payload.get("sha256") or "MISSING")[:16],
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



def normalize_reports(reports: Iterable[str | Path] | None) -> list[dict[str, Any]]:
    """Normalize only explicitly provided report paths.

    This function intentionally does not auto-discover local artifacts.
    Stack discovery belongs to the from_stack shell wrapper.
    """
    return _collect_reports(reports)


def _build_criteria(input_reports: list[dict[str, Any]], symbols: list[str]) -> list[dict[str, Any]]:
    report_count = len(input_reports)
    kinds = {r["kind"] for r in input_reports}
    avg_score = sum(r["score"] for r in input_reports) / report_count if report_count else 0.0
    max_rows = max([r["dataset_row_count"] for r in input_reports] or [0])
    max_splits = max([r["split_count"] for r in input_reports] or [0])

    expected_core = {
        "evidence_quality",
        "evidence_drilldown",
        "evidence_timeline",
        "research_promotion",
        "human_review",
        "oos_validation",
        "paper_trading",
    }
    core_present = len(expected_core.intersection(kinds))

    criteria = [
        _criterion(
            "input_evidence_stack",
            "PASS" if report_count >= 7 else "FAIL",
            report_count >= 7,
            f"{report_count}/7",
            ">= 7 prior research reports preferred",
            "" if report_count >= 7 else "Need the upstream evidence stack before data-coverage promotion.",
        ),
        _criterion(
            "core_gate_presence",
            "PASS" if core_present >= 7 else "FAIL",
            core_present >= 7,
            f"{core_present}/7",
            "8L through 8R core gates present",
            "" if core_present >= 7 else "Need all core evidence gates represented.",
        ),
        _criterion(
            "symbol_scope",
            "PASS" if len(symbols) >= 1 else "FAIL",
            len(symbols) >= 1,
            len(symbols),
            ">= 1 symbol",
            "" if symbols else "Need at least one research symbol.",
        ),
        _criterion(
            "dataset_volume_observed",
            "PASS" if max_rows >= 1000 else "WARN",
            max_rows >= 1000,
            max_rows,
            ">= 1000 explicit rows preferred",
            "" if max_rows >= 1000 else "Need explicit dataset row coverage from the research runner.",
        ),
        _criterion(
            "walk_forward_coverage",
            "PASS" if max_splits >= 6 else "WARN",
            max_splits >= 6,
            max_splits,
            ">= 6 explicit walk-forward splits preferred",
            "" if max_splits >= 6 else "Need explicit split coverage from the research runner.",
        ),
        _criterion(
            "prior_evidence_score",
            "PASS" if avg_score >= 0.60 else "WARN",
            avg_score >= 0.60,
            round(avg_score, 4),
            ">= 0.60 preliminary research score preferred",
            "" if avg_score >= 0.60 else "Need stronger upstream evidence before coverage is considered mature.",
        ),
        _criterion(
            "lineage_traceability",
            "PASS" if any(r["sha256"] != "MISSING" for r in input_reports) else "FAIL",
            any(r["sha256"] != "MISSING" for r in input_reports),
            "present" if any(r["sha256"] != "MISSING" for r in input_reports) else "missing",
            "artifact hashes present",
            "" if any(r["sha256"] != "MISSING" for r in input_reports) else "Need hashed artifacts for lineage.",
        ),
    ]
    return criteria


def _assert_research_only(rendered: str) -> None:
    low = rendered.lower()
    for term in FORBIDDEN_RENDERED_PHRASES:
        if term in low:
            raise ValueError(f"Operational language is not allowed in Data Coverage Gate: {term}")


def _sha(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _render_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(x) for x in row) + "|")
    return "\n".join(out)


def render_markdown(payload: dict[str, Any]) -> str:
    criteria = payload["criteria"]
    reports = payload["input_reports"]
    flags = payload["safety_flags"]

    md = f"""# QRDS/QOS • Gate BTC • Research-only
## Data Coverage Gate

Formal data-coverage review packet for the evidence stack. This screen records research coverage, lineage, and blockers; it cannot unlock operational use.

**Gate answer:** {payload["gate_answer"]}

**Policy lock:** {payload["policy_lock"]} • **Mode:** {payload["app_mode"]}

## Summary

- Input reports: {payload["input_report_count"]}/{payload["preferred_report_count"]}
- Criteria ready: {payload["criteria_ready_count"]}/{payload["criteria_total_count"]}
- Mean coverage score: {payload["mean_coverage_score"]}
- Symbols: {", ".join(payload["symbols"])}

Research-only guardrail: no execution, no exchange account, no portfolio allocation output, no trade instruction, no live-fund workflow.

## Validation criteria

{_render_table(
    ["criterion_id", "status", "ready", "observed", "threshold", "blocker"],
    [[c["criterion_id"], c["status"], c["ready"], c["observed"], c["threshold"], c["blocker"]] for c in criteria],
)}

## Input reports

{_render_table(
    ["kind", "status", "ready", "gate_answer", "sha256"],
    [[r["kind"], r["status"], r["ready"], r["gate_answer"], r["sha256"]] for r in reports] if reports else [["NONE", "MISSING", False, "MISSING_INPUT_REPORT", "MISSING"]],
)}

## Safety flags

{_render_table(["flag", "value"], [[k, v] for k, v in flags.items()])}

Generated at {payload["generated_at"]} • SHA256 {payload["report_payload_sha256"]}
"""
    _assert_research_only(md)
    return md


def render_html(payload: dict[str, Any]) -> str:
    def esc(x: Any) -> str:
        return html.escape(str(x))

    criteria_rows = "\n".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td><td>{esc(c['blocker'])}</td></tr>"
        for c in payload["criteria"]
    )
    report_rows = "\n".join(
        f"<tr><td>{esc(r['kind'])}</td><td>{esc(r['status'])}</td><td>{esc(r['ready'])}</td><td>{esc(r['gate_answer'])}</td><td>{esc(r['sha256'])}</td></tr>"
        for r in payload["input_reports"]
    ) or "<tr><td>NONE</td><td>MISSING</td><td>False</td><td>MISSING_INPUT_REPORT</td><td>MISSING</td></tr>"
    flag_rows = "\n".join(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>" for k, v in payload["safety_flags"].items())

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>QRDS Data Coverage Gate</title>
<style>
body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}
.card{{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px 8px 8px 0}}
table{{border-collapse:collapse;width:100%;background:white}}
th,td{{border:1px solid #d9deea;padding:8px;text-align:left;font-size:14px}}
th{{background:#eef2ff}}
.badge{{display:inline-block;border-radius:999px;background:#fee2e2;padding:6px 10px;font-weight:700}}
</style>
</head>
<body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1>
<h2>Data Coverage Gate</h2>
<p>Formal data-coverage review packet for the evidence stack. This page records research coverage and blockers; it cannot unlock operational use.</p>
<div class="card">
<p><b>Gate answer:</b> {esc(payload["gate_answer"])}</p>
<p><b>Policy lock:</b> {esc(payload["policy_lock"])} • <b>Mode:</b> {esc(payload["app_mode"])}</p>
<div class="kpi"><b>Input reports</b><br>{esc(payload["input_report_count"])}/{esc(payload["preferred_report_count"])}</div>
<div class="kpi"><b>Criteria ready</b><br>{esc(payload["criteria_ready_count"])}/{esc(payload["criteria_total_count"])}</div>
<div class="kpi"><b>Mean coverage score</b><br>{esc(payload["mean_coverage_score"])}</div>
<div class="kpi"><b>Symbols</b><br>{esc(", ".join(payload["symbols"]))}</div>
<p class="badge">Research-only guardrail active</p>
<p>No execution, no exchange account, no portfolio allocation output, no trade instruction, no live-fund workflow.</p>
</div>

<h2>Validation criteria</h2>
<table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th><th>blocker</th></tr></thead><tbody>{criteria_rows}</tbody></table>

<h2>Input reports</h2>
<table><thead><tr><th>kind</th><th>status</th><th>ready</th><th>gate_answer</th><th>sha256</th></tr></thead><tbody>{report_rows}</tbody></table>

<h2>Safety flags</h2>
<table><thead><tr><th>flag</th><th>value</th></tr></thead><tbody>{flag_rows}</tbody></table>

<p>Generated at {esc(payload["generated_at"])} • SHA256 {esc(payload["report_payload_sha256"])}</p>
</body>
</html>
"""
    _assert_research_only(page)
    return page


def build_data_coverage(
    output_dir: str | Path,
    symbols: str | Iterable[str],
    reports: Iterable[str | Path] | None = None,
) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    symbol_list = _symbols(symbols)
    input_reports = _collect_reports(reports)
    criteria = _build_criteria(input_reports, symbol_list)

    ready_count = sum(1 for c in criteria if c["ready"])
    total_count = len(criteria)
    mean_score = round(ready_count / total_count if total_count else 0.0, 4)

    if not input_reports:
        gate_answer = "NO_DATA_COVERAGE_NO_INPUT_REPORTS_RESEARCH_ONLY"
    elif mean_score >= 0.75 and len(input_reports) >= 7:
        gate_answer = "DATA_COVERAGE_PARTIAL_MORE_RESEARCH_REQUIRED_RESEARCH_ONLY"
    else:
        gate_answer = "DATA_COVERAGE_INCOMPLETE_MORE_COLLECTION_REQUIRED_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.data_coverage_gate.v1",
        "report_name": "qrds-data-coverage-gate",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "symbols": symbol_list,
        "input_report_count": len(input_reports),
        "preferred_report_count": 7,
        "criteria_ready_count": ready_count,
        "criteria_total_count": total_count,
        "mean_coverage_score": mean_score,
        "formal_data_coverage_ready": "NO",
        "criteria": criteria,
        "input_reports": input_reports,
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }

    payload["report_payload_sha256"] = _sha(payload)

    report_path = out / "data_coverage_gate.json"
    markdown_path = out / "data_coverage_gate.md"
    html_path = out / "index.html"
    index_path = out / "data_coverage_index.json"

    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    index = {
        "schema": "qrds.data_coverage_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "symbols": payload["symbols"],
        "input_report_count": payload["input_report_count"],
        "preferred_report_count": payload["preferred_report_count"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_coverage_score": payload["mean_coverage_score"],
        "report_path": str(report_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "index_path": str(index_path),
        "serve_entrypoint": str(html_path),
        "report_payload_sha256": payload["report_payload_sha256"],
        **SAFETY_FLAGS,
    }
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")

    # Backward-compatible return shape expected by existing tests and callers.
    index["payload"] = payload
    return index
