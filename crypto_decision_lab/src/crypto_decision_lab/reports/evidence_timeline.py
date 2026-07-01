"""Evidence Timeline / Gate History Registry for QRDS/QOS.

Sprint 8N sits after the 8L Evidence Quality Gate and 8M Evidence Drilldown.
It records research evidence over time so the project can distinguish a
single promising artifact from repeatable, auditable, stable research evidence.

This module deliberately does not produce trading signals, executable signals,
recommendations, allocations, position sizing, orders, portfolio decisions,
or real-capital actions.
"""
from __future__ import annotations

import html
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Sequence

from crypto_decision_lab.contracts.research import (
    build_research_safety_stamp,
    collect_research_contract_issues,
)
from crypto_decision_lab.reports.evidence_drilldown import (
    EvidenceDrilldownError,
    build_evidence_drilldown,
    build_fixture_evidence_quality_report,
)

EVIDENCE_TIMELINE_SCHEMA_VERSION = "qrds.evidence_timeline.v1"
EVIDENCE_TIMELINE_INDEX_SCHEMA_VERSION = "qrds.evidence_timeline_index.v1"

RESEARCH_ONLY_FALSE_FLAGS = (
    "operational_decision_allowed",
    "orders_generated",
    "real_capital_used",
    "trading_signal_generated",
    "executable_signal_generated",
    "recommendation_generated",
    "allocation_generated",
    "portfolio_decision_generated",
)

FORBIDDEN_OPERATIONAL_TERMS = (
    "buy",
    "sell",
    "long",
    "short",
    "leverage",
    "position size",
    "position sizing",
    "order",
    "orders",
    "portfolio allocation",
    "rebalance",
    "stop loss",
    "take profit",
    "entry price",
    "exit price",
)

REQUIRED_HISTORY_GATES = (
    "evidence_quality",
    "evidence_drilldown",
)

NEXT_REQUIRED_GATES = [
    "repeat_evidence_timeline_across_multiple_research_runs",
    "data_quality_reliability_gate",
    "out_of_sample_validation_gate",
    "paper_trading_gate",
    "risk_model_gate",
    "human_approval_gate",
    "explicit_policy_change_from_research_only",
]


class EvidenceTimelineError(ValueError):
    """Raised when a timeline artifact cannot be built safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _payload_sha256(payload: Any) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(data.encode("utf-8")).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return str(path)


def _write_text(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return str(path)


def _safe_stamp() -> dict[str, Any]:
    stamp = dict(build_research_safety_stamp())
    stamp.update(
        {
            "allocation_generated": False,
            "portfolio_decision_generated": False,
        }
    )
    for flag in RESEARCH_ONLY_FALSE_FLAGS:
        stamp[flag] = False
    return stamp


def _collect_research_issues(payload: dict[str, Any], *, name: str) -> list[dict[str, Any]]:
    try:
        return list(
            collect_research_contract_issues(
                payload,
                name=name,
                require_schema=True,
                require_app_mode=True,
                require_research_allowed=True,
            )
        )
    except TypeError:
        return list(collect_research_contract_issues(payload))


def _as_float(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _status_bucket(value: Any) -> str:
    text = str(value or "UNKNOWN").upper()
    if "PASS" in text or text.startswith("YES_"):
        return "PASS"
    if "FAIL" in text or text.startswith("NO_"):
        return "FAIL"
    if "WATCH" in text or "PARTIAL" in text:
        return "WATCH"
    return "WATCH"


def _resolve_existing_path(path_value: str | Path) -> Path:
    raw = Path(path_value)
    candidates = [raw]
    if not raw.is_absolute():
        cwd = Path.cwd()
        candidates.extend(
            [
                cwd / raw,
                cwd.parent / raw,
                cwd.parent.parent / raw,
            ]
        )
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()
    raise EvidenceTimelineError(f"JSON artifact not found: {path_value}")


def _read_json(path: str | Path) -> dict[str, Any]:
    file_path = _resolve_existing_path(path)
    with file_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise EvidenceTimelineError(f"JSON artifact must contain an object: {file_path}")
    return payload


def _resolve_report_from_index(index_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    for key in ("report_path", "evidence_quality_gate_path", "evidence_drilldown_gate_path"):
        target = payload.get(key)
        if not target:
            continue
        candidates = []
        raw = Path(str(target))
        if raw.is_absolute():
            candidates.append(raw)
        else:
            candidates.extend(
                [
                    index_path.parent / raw,
                    Path.cwd() / raw,
                    Path.cwd().parent / raw,
                    Path.cwd().parent.parent / raw,
                ]
            )
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                with candidate.open("r", encoding="utf-8") as handle:
                    resolved = json.load(handle)
                if isinstance(resolved, dict):
                    return resolved
    raise EvidenceTimelineError("Index payload does not point to a readable report_path.")


def load_report_payload(path: str | Path) -> dict[str, Any]:
    """Load a supported 8L/8M evidence report or index JSON."""
    file_path = _resolve_existing_path(path)
    payload = _read_json(file_path)
    schema = str(payload.get("schema") or "")
    if schema == EVIDENCE_TIMELINE_INDEX_SCHEMA_VERSION:
        raise EvidenceTimelineError("Expected 8L/8M evidence inputs, not a Timeline index.")
    if schema.endswith("_index.v1"):
        return _resolve_report_from_index(file_path, payload)
    if "evaluations" in payload or "drilldowns" in payload:
        return payload
    raise EvidenceTimelineError("Unsupported evidence payload; expected 8L/8M report or index.")


def load_report_payloads(paths: Sequence[str | Path]) -> list[dict[str, Any]]:
    reports = [load_report_payload(path) for path in paths]
    if not reports:
        raise EvidenceTimelineError("At least one evidence report is required.")
    return reports


def parse_paths(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def parse_symbols(value: str) -> list[str]:
    symbols = [part.strip() for part in value.split(",") if part.strip()]
    if not symbols:
        raise EvidenceTimelineError("At least one symbol is required.")
    return symbols


def build_fixture_evidence_reports(symbols: list[str]) -> list[dict[str, Any]]:
    """Build deterministic 8L and 8M reports for offline use/tests."""
    quality = build_fixture_evidence_quality_report(symbols)
    drilldown = build_evidence_drilldown(quality)
    return [quality, drilldown]


def _report_gate_type(report: dict[str, Any]) -> str:
    schema = str(report.get("schema") or "")
    name = str(report.get("report_name") or report.get("gate_name") or "").lower()
    if "evidence_drilldown" in schema or "drilldown" in name or "drilldowns" in report:
        return "evidence_drilldown"
    if "evidence_quality" in schema or "quality" in name or "evaluations" in report:
        return "evidence_quality"
    return "unknown_evidence_gate"


def _observations_from_quality(report: dict[str, Any], *, report_index: int) -> list[dict[str, Any]]:
    generated_at = str(report.get("generated_at") or _utc_now())
    observations: list[dict[str, Any]] = []
    for item in report.get("evaluations") or []:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol") or "UNKNOWN")
        score = _clip01(_as_float(item.get("research_readiness_score"), 0.0) or 0.0)
        status = _status_bucket(item.get("research_readiness"))
        observations.append(
            {
                "symbol": symbol,
                "gate_type": "evidence_quality",
                "report_index": report_index,
                "generated_at": generated_at,
                "status": status,
                "raw_status": item.get("research_readiness"),
                "score": round(score, 4),
                "gate_answer": report.get("gate_answer"),
                "blockers": list(item.get("blockers") or []),
                "warnings": list(item.get("warnings") or []),
                "dimensions": {
                    "data_volume_score": item.get("data_volume_score"),
                    "walk_forward_split_score": item.get("walk_forward_split_score"),
                    "stress_stability_score": item.get("stress_stability_score"),
                    "edge_quality_score": item.get("edge_quality_score"),
                },
                "source_report_sha256": _payload_sha256(report),
                "decision_scope": "evidence_timeline_observation_research_only",
                "hypothetical_only": True,
                **_safe_stamp(),
            }
        )
    return observations


def _observations_from_drilldown(report: dict[str, Any], *, report_index: int) -> list[dict[str, Any]]:
    generated_at = str(report.get("generated_at") or _utc_now())
    observations: list[dict[str, Any]] = []
    for item in report.get("drilldowns") or []:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol") or "UNKNOWN")
        score = _clip01(_as_float(item.get("research_readiness_score"), 0.0) or 0.0)
        status = _status_bucket(item.get("coverage_status", item.get("research_readiness")))
        dimensions = {
            str(row.get("dimension")): {
                "status": row.get("status"),
                "score": row.get("score"),
                "gap_to_target": row.get("gap_to_target"),
            }
            for row in item.get("dimension_rows") or []
            if isinstance(row, dict)
        }
        observations.append(
            {
                "symbol": symbol,
                "gate_type": "evidence_drilldown",
                "report_index": report_index,
                "generated_at": generated_at,
                "status": status,
                "raw_status": item.get("coverage_status", item.get("research_readiness")),
                "score": round(score, 4),
                "gate_answer": report.get("gate_answer"),
                "fail_dimensions": list(item.get("fail_dimensions") or []),
                "watch_dimensions": list(item.get("watch_dimensions") or []),
                "blockers": list(item.get("blockers") or []),
                "warnings": list(item.get("warnings") or []),
                "dimensions": dimensions,
                "source_report_sha256": _payload_sha256(report),
                "decision_scope": "evidence_timeline_observation_research_only",
                "hypothetical_only": True,
                **_safe_stamp(),
            }
        )
    return observations


def normalize_evidence_observations(reports: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize 8L/8M evidence artifacts into symbol-level timeline observations."""
    observations: list[dict[str, Any]] = []
    for index, report in enumerate(reports):
        if not isinstance(report, dict):
            continue
        gate_type = _report_gate_type(report)
        if gate_type == "evidence_quality":
            observations.extend(_observations_from_quality(report, report_index=index))
        elif gate_type == "evidence_drilldown":
            observations.extend(_observations_from_drilldown(report, report_index=index))
    if not observations:
        raise EvidenceTimelineError("No supported evidence observations found in the supplied reports.")
    return observations


def _consistency_rate(statuses: list[str]) -> float:
    if not statuses:
        return 0.0
    counts = Counter(statuses)
    return max(counts.values()) / len(statuses)


def _score_range(scores: list[float]) -> float:
    if not scores:
        return 0.0
    return max(scores) - min(scores)


def _timeline_status(
    *,
    observation_count: int,
    gate_types_seen: set[str],
    latest_status: str,
    latest_score: float,
    consistency_rate: float,
    regression_detected: bool,
    min_observations: int,
    min_latest_score: float,
    min_consistency_rate: float,
) -> tuple[str, str, list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []

    if observation_count < min_observations:
        blockers.append("INSUFFICIENT_HISTORY_OBSERVATIONS")
    missing_gates = [gate for gate in REQUIRED_HISTORY_GATES if gate not in gate_types_seen]
    if missing_gates:
        blockers.append("MISSING_REQUIRED_HISTORY_GATES:" + ",".join(missing_gates))
    if latest_status == "FAIL":
        blockers.append("LATEST_EVIDENCE_STATUS_FAIL")
    if latest_score < min_latest_score:
        blockers.append("LATEST_RESEARCH_SCORE_BELOW_HISTORY_MINIMUM")
    if consistency_rate < min_consistency_rate:
        warnings.append("STATUS_HISTORY_INCONSISTENT")
    if regression_detected:
        blockers.append("RESEARCH_SCORE_REGRESSION_DETECTED")

    if blockers:
        return "FAIL", "NO_HISTORY_NOT_READY_FOR_NEXT_RESEARCH_GATE_RESEARCH_ONLY", blockers + warnings
    if warnings:
        return "WATCH", "PARTIAL_HISTORY_MORE_REPEATABILITY_REQUIRED_RESEARCH_ONLY", warnings
    return "PASS", "YES_HISTORY_SUPPORTS_CONTINUED_RESEARCH_ONLY", []


def _symbol_timeline(
    symbol: str,
    observations: list[dict[str, Any]],
    *,
    min_observations: int,
    min_latest_score: float,
    min_consistency_rate: float,
    max_allowed_regression: float,
) -> dict[str, Any]:
    ordered = sorted(observations, key=lambda item: (str(item.get("generated_at")), int(item.get("report_index", 0)), str(item.get("gate_type"))))
    scores = [_clip01(_as_float(item.get("score"), 0.0) or 0.0) for item in ordered]
    statuses = [_status_bucket(item.get("status")) for item in ordered]
    gate_types_seen = {str(item.get("gate_type")) for item in ordered}
    latest = ordered[-1]
    latest_score = scores[-1]
    latest_status = statuses[-1]
    best_previous_score = max(scores[:-1]) if len(scores) > 1 else latest_score
    regression_amount = max(0.0, best_previous_score - latest_score)
    regression_detected = regression_amount > max_allowed_regression
    consistency = _consistency_rate(statuses)
    history_status, history_answer, issues = _timeline_status(
        observation_count=len(ordered),
        gate_types_seen=gate_types_seen,
        latest_status=latest_status,
        latest_score=latest_score,
        consistency_rate=consistency,
        regression_detected=regression_detected,
        min_observations=min_observations,
        min_latest_score=min_latest_score,
        min_consistency_rate=min_consistency_rate,
    )

    return {
        "symbol": symbol,
        "history_status": history_status,
        "history_answer": history_answer,
        "observation_count": len(ordered),
        "gate_types_seen": sorted(gate_types_seen),
        "latest_gate_type": latest.get("gate_type"),
        "latest_status": latest_status,
        "latest_score": round(latest_score, 4),
        "mean_score": round(mean(scores), 4),
        "min_score": round(min(scores), 4),
        "max_score": round(max(scores), 4),
        "score_range": round(_score_range(scores), 4),
        "status_sequence": statuses,
        "status_consistency_rate": round(consistency, 4),
        "regression_detected": regression_detected,
        "regression_amount": round(regression_amount, 4),
        "issues": issues,
        "observations": ordered,
        "next_research_actions": _next_research_actions(history_status, issues),
        "decision_scope": "evidence_history_research_only",
        "hypothetical_only": True,
        **_safe_stamp(),
    }


def _next_research_actions(status: str, issues: list[str]) -> list[str]:
    if status == "PASS":
        return ["Continue collecting repeatable evidence across future research runs before any later gate."]
    actions: list[str] = []
    joined = " ".join(issues)
    if "INSUFFICIENT_HISTORY_OBSERVATIONS" in joined:
        actions.append("Run the 8L/8M evidence stack across additional research cycles and register the artifacts here.")
    if "MISSING_REQUIRED_HISTORY_GATES" in joined:
        actions.append("Include both Evidence Quality and Evidence Drilldown artifacts for the same research universe.")
    if "REGRESSION" in joined:
        actions.append("Investigate score regression before progressing to out-of-sample or paper-trading gates.")
    if "INCONSISTENT" in joined:
        actions.append("Compare status changes across runs and identify unstable data/model assumptions.")
    if not actions:
        actions.append("Collect additional research-only evidence before promoting the hypothesis.")
    return actions


def _assert_research_only_payload(payload: dict[str, Any]) -> None:
    for flag in RESEARCH_ONLY_FALSE_FLAGS:
        if payload.get(flag) is not False:
            raise EvidenceTimelineError(f"Research-only flag must be false: {flag}")

    issues = _collect_research_issues(payload, name="evidence_timeline")
    blocking = [issue for issue in issues if issue.get("severity") in {"error", "blocker"}]
    if blocking:
        raise EvidenceTimelineError(f"Research contract failed: {blocking}")


def build_evidence_timeline(
    evidence_reports: Sequence[dict[str, Any]],
    *,
    report_name: str = "qrds-evidence-timeline-gate",
    min_observations: int = 3,
    min_latest_score: float = 0.50,
    min_consistency_rate: float = 0.67,
    max_allowed_regression: float = 0.15,
) -> dict[str, Any]:
    """Build a research-only evidence timeline/history report over 8L/8M artifacts."""
    if not evidence_reports:
        raise EvidenceTimelineError("At least one evidence report is required.")
    observations = normalize_evidence_observations(evidence_reports)
    by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for observation in observations:
        by_symbol[str(observation.get("symbol"))].append(observation)

    timelines = [
        _symbol_timeline(
            symbol,
            rows,
            min_observations=min_observations,
            min_latest_score=min_latest_score,
            min_consistency_rate=min_consistency_rate,
            max_allowed_regression=max_allowed_regression,
        )
        for symbol, rows in sorted(by_symbol.items())
    ]
    if not timelines:
        raise EvidenceTimelineError("No symbol timelines could be built.")

    status_counts: dict[str, int] = {}
    for item in timelines:
        status = str(item["history_status"])
        status_counts[status] = status_counts.get(status, 0) + 1

    asset_count = len(timelines)
    pass_count = status_counts.get("PASS", 0)
    watch_count = status_counts.get("WATCH", 0)
    fail_count = status_counts.get("FAIL", 0)
    mean_latest = mean(item["latest_score"] for item in timelines)
    mean_consistency = mean(item["status_consistency_rate"] for item in timelines)

    if pass_count == asset_count:
        gate_answer = "YES_EVIDENCE_HISTORY_STABLE_FOR_CONTINUED_RESEARCH_ONLY"
    elif pass_count + watch_count > 0 or fail_count < asset_count:
        gate_answer = "PARTIAL_EVIDENCE_HISTORY_MORE_RUNS_REQUIRED_RESEARCH_ONLY"
    else:
        gate_answer = "NO_EVIDENCE_HISTORY_NOT_READY_FOR_NEXT_RESEARCH_GATE_RESEARCH_ONLY"

    report = {
        "schema": EVIDENCE_TIMELINE_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "report_name": report_name,
        "gate_name": "Evidence Timeline / Gate History Registry v1",
        "gate_question": "Is the research evidence repeatable across registered gates/runs, or just one artifact?",
        "gate_answer": gate_answer,
        "decision_scope": "evidence_timeline_research_only",
        "asset_count": asset_count,
        "symbols": [item["symbol"] for item in timelines],
        "input_report_count": len(evidence_reports),
        "observation_count": len(observations),
        "history_status_counts": status_counts,
        "mean_latest_score": round(mean_latest, 4),
        "mean_status_consistency_rate": round(mean_consistency, 4),
        "thresholds": {
            "min_observations": min_observations,
            "min_latest_score": min_latest_score,
            "min_consistency_rate": min_consistency_rate,
            "max_allowed_regression": max_allowed_regression,
            "required_history_gates": list(REQUIRED_HISTORY_GATES),
        },
        "timelines": timelines,
        "next_required_gates": list(NEXT_REQUIRED_GATES),
        "caveats": [
            "This is an evidence history registry, not an operational decision layer.",
            "A stable history only supports continued research and does not authorize real capital.",
            "Out-of-sample validation, paper trading, risk model, human approval, and explicit policy change remain mandatory.",
        ],
        "source_payload_sha256": {
            f"input_report_{index}": _payload_sha256(report)
            for index, report in enumerate(evidence_reports)
        },
        "hypothetical_only": True,
        **_safe_stamp(),
    }
    _assert_research_only_payload(report)
    return report


def validate_evidence_timeline(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Return validation issues for an evidence timeline report."""
    issues: list[dict[str, Any]] = []
    if report.get("schema") != EVIDENCE_TIMELINE_SCHEMA_VERSION:
        issues.append({"severity": "error", "code": "SCHEMA_MISMATCH"})

    for flag in RESEARCH_ONLY_FALSE_FLAGS:
        if report.get(flag) is not False:
            issues.append({"severity": "error", "code": f"RESEARCH_ONLY_FLAG_NOT_FALSE:{flag}"})

    if report.get("decision_scope") != "evidence_timeline_research_only":
        issues.append({"severity": "error", "code": "INVALID_DECISION_SCOPE"})

    text_blob = json.dumps(report, sort_keys=True).lower()
    for term in FORBIDDEN_OPERATIONAL_TERMS:
        if term in text_blob:
            issues.append({"severity": "warning", "code": f"OPERATIONAL_TERM_PRESENT:{term}"})

    issues.extend(_collect_research_issues(report, name="evidence_timeline"))
    return issues


def _format_float(value: Any) -> str:
    number = _as_float(value)
    if number is None:
        return "n/a"
    return f"{number:.3f}"


def render_evidence_timeline_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# QRDS Evidence Timeline / Gate History Registry v1",
        "",
        f"Generated at: `{report.get('generated_at')}`",
        "",
        f"Gate answer: `{report.get('gate_answer')}`",
        "",
        "Scope: research history only. No operational decision, no signal, no recommendation, no allocation, no order, no real capital.",
        "",
        "## Summary",
        "",
        f"- Assets: {report.get('asset_count')}",
        f"- Input reports: {report.get('input_report_count')}",
        f"- Observations: {report.get('observation_count')}",
        f"- Mean latest score: {_format_float(report.get('mean_latest_score'))}",
        f"- Mean status consistency: {_format_float(report.get('mean_status_consistency_rate'))}",
        f"- History status counts: `{json.dumps(report.get('history_status_counts', {}), sort_keys=True)}`",
        "",
        "## Symbol timelines",
        "",
    ]
    for item in report.get("timelines", []):
        lines.extend(
            [
                f"### {item.get('symbol')}",
                "",
                f"- History status: `{item.get('history_status')}`",
                f"- History answer: `{item.get('history_answer')}`",
                f"- Observation count: {item.get('observation_count')}",
                f"- Gates seen: `{json.dumps(item.get('gate_types_seen', []), sort_keys=True)}`",
                f"- Latest score: {_format_float(item.get('latest_score'))}",
                f"- Consistency rate: {_format_float(item.get('status_consistency_rate'))}",
                f"- Regression detected: `{item.get('regression_detected')}`",
                f"- Issues: `{json.dumps(item.get('issues', []), sort_keys=True)}`",
                "",
                "| Gate | Status | Score | Generated at |",
                "|---|---:|---:|---|",
            ]
        )
        for row in item.get("observations", []):
            lines.append(
                f"| {row.get('gate_type')} | {row.get('status')} | {_format_float(row.get('score'))} | {row.get('generated_at')} |"
            )
        lines.extend(["", "Next research actions:"])
        for action in item.get("next_research_actions", []):
            lines.append(f"- {action}")
        lines.append("")

    lines.extend(["## Next mandatory gates", ""])
    for gate in report.get("next_required_gates", []):
        lines.append(f"- `{gate}`")
    lines.append("")
    return "\n".join(lines)


def _badge(status: Any) -> str:
    status_text = html.escape(str(status))
    return f'<span class="badge badge-{status_text.lower()}">{status_text}</span>'


def _html_observation_rows(rows: Iterable[dict[str, Any]]) -> str:
    output = []
    for row in rows:
        output.append(
            "<tr>"
            f"<td>{html.escape(str(row.get('gate_type')))}</td>"
            f"<td>{_badge(row.get('status'))}</td>"
            f"<td>{html.escape(_format_float(row.get('score')))}</td>"
            f"<td>{html.escape(str(row.get('generated_at')))}</td>"
            f"<td><code>{html.escape(str(row.get('source_report_sha256', ''))[:12])}</code></td>"
            "</tr>"
        )
    return "".join(output)


def render_evidence_timeline_html(report: dict[str, Any]) -> str:
    cards = []
    for item in report.get("timelines", []):
        actions = "".join(f"<li>{html.escape(str(action))}</li>" for action in item.get("next_research_actions", []))
        issues = html.escape(json.dumps(item.get("issues", []), sort_keys=True))
        gates = html.escape(json.dumps(item.get("gate_types_seen", []), sort_keys=True))
        cards.append(
            f"""
            <section class="card asset-card" data-status="{html.escape(str(item.get('history_status')))}">
              <div class="card-head">
                <h2>{html.escape(str(item.get('symbol')))}</h2>
                {_badge(item.get('history_status'))}
              </div>
              <p><strong>History answer:</strong> <code>{html.escape(str(item.get('history_answer')))}</code></p>
              <p><strong>Gates seen:</strong> <code>{gates}</code></p>
              <p><strong>Latest score:</strong> {_format_float(item.get('latest_score'))} · <strong>Consistency:</strong> {_format_float(item.get('status_consistency_rate'))} · <strong>Regression:</strong> <code>{html.escape(str(item.get('regression_detected')))}</code></p>
              <p><strong>Issues:</strong> <code>{issues}</code></p>
              <table>
                <thead><tr><th>Gate</th><th>Status</th><th>Score</th><th>Generated at</th><th>Hash</th></tr></thead>
                <tbody>{_html_observation_rows(item.get('observations', []))}</tbody>
              </table>
              <h3>Next research actions</h3>
              <ul>{actions}</ul>
            </section>
            """
        )

    gates = "".join(f"<li><code>{html.escape(str(gate))}</code></li>" for gate in report.get("next_required_gates", []))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>QRDS Evidence Timeline</title>
  <style>
    :root {{ color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    body {{ margin: 0; background: #0b1120; color: #e5e7eb; }}
    header {{ padding: 28px 32px; background: linear-gradient(135deg, #020617, #172554); border-bottom: 1px solid #334155; }}
    main {{ padding: 24px 32px 48px; max-width: 1280px; margin: 0 auto; }}
    h1 {{ margin: 0 0 8px; font-size: 2rem; }}
    h2 {{ margin: 0; }}
    h3 {{ margin: 18px 0 6px; color: #cbd5e1; }}
    code {{ color: #bfdbfe; }}
    .subtitle {{ color: #cbd5e1; max-width: 920px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin: 20px 0; }}
    .card {{ background: #111827; border: 1px solid #334155; border-radius: 18px; padding: 18px; box-shadow: 0 12px 28px rgba(0,0,0,.18); }}
    .card-head {{ display: flex; justify-content: space-between; gap: 12px; align-items: center; margin-bottom: 10px; }}
    .badge {{ display: inline-block; border-radius: 999px; padding: 4px 10px; font-weight: 800; font-size: .78rem; letter-spacing: .04em; }}
    .badge-pass {{ background: rgba(22, 163, 74, .18); color: #86efac; border: 1px solid rgba(134, 239, 172, .35); }}
    .badge-watch {{ background: rgba(234, 179, 8, .18); color: #fde68a; border: 1px solid rgba(253, 230, 138, .35); }}
    .badge-fail {{ background: rgba(220, 38, 38, .18); color: #fecaca; border: 1px solid rgba(254, 202, 202, .35); }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: .9rem; }}
    th, td {{ padding: 10px 8px; border-bottom: 1px solid #334155; vertical-align: top; text-align: left; }}
    th {{ color: #cbd5e1; font-weight: 700; }}
    .asset-card {{ overflow-x: auto; margin-bottom: 18px; }}
    .note {{ border-left: 4px solid #60a5fa; padding-left: 14px; color: #cbd5e1; }}
    .footer {{ color: #94a3b8; margin-top: 28px; }}
  </style>
</head>
<body>
  <header>
    <h1>QRDS Evidence Timeline / Gate History Registry v1</h1>
    <p class="subtitle">Research-only history layer. It checks whether evidence is repeatable across registered gates/runs. It does not create operational decisions, executable signals, recommendations, allocations, orders, or real-capital actions.</p>
    <p><strong>Gate answer:</strong> <code>{html.escape(str(report.get('gate_answer')))}</code></p>
  </header>
  <main>
    <section class="grid">
      <div class="card"><strong>Assets</strong><br><span>{report.get('asset_count')}</span></div>
      <div class="card"><strong>Input reports</strong><br><span>{report.get('input_report_count')}</span></div>
      <div class="card"><strong>Observations</strong><br><span>{report.get('observation_count')}</span></div>
      <div class="card"><strong>Mean latest score</strong><br><span>{_format_float(report.get('mean_latest_score'))}</span></div>
      <div class="card"><strong>Mean consistency</strong><br><span>{_format_float(report.get('mean_status_consistency_rate'))}</span></div>
      <div class="card"><strong>Status counts</strong><br><code>{html.escape(json.dumps(report.get('history_status_counts', {}), sort_keys=True))}</code></div>
    </section>
    <p class="note">Interpretation: this gate is a memory/audit layer. PASS still means continued research only. WATCH/FAIL means more repeatable evidence is required before later gates.</p>
    {''.join(cards)}
    <section class="card">
      <h2>Next mandatory gates</h2>
      <ul>{gates}</ul>
    </section>
    <p class="footer">Generated at {html.escape(str(report.get('generated_at')))} · payload SHA256 {html.escape(str(report.get('report_payload_sha256', 'computed-after-write')))}</p>
  </main>
</body>
</html>
"""


def write_evidence_timeline(
    evidence_reports: Sequence[dict[str, Any]],
    output_dir: str | Path,
    *,
    report_name: str = "qrds-evidence-timeline-gate",
    min_observations: int = 3,
    min_latest_score: float = 0.50,
    min_consistency_rate: float = 0.67,
    max_allowed_regression: float = 0.15,
) -> dict[str, Any]:
    """Write JSON, Markdown, HTML and index artifacts for the timeline gate."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    report = build_evidence_timeline(
        evidence_reports,
        report_name=report_name,
        min_observations=min_observations,
        min_latest_score=min_latest_score,
        min_consistency_rate=min_consistency_rate,
        max_allowed_regression=max_allowed_regression,
    )
    report["report_payload_sha256"] = _payload_sha256(report)
    report_path = root / "evidence_timeline_gate.json"
    markdown_path = root / "evidence_timeline_gate.md"
    html_path = root / "index.html"
    index_path = root / "evidence_timeline_index.json"

    _write_json(report_path, report)
    _write_text(markdown_path, render_evidence_timeline_markdown(report))
    _write_text(html_path, render_evidence_timeline_html(report))

    index = {
        "schema": EVIDENCE_TIMELINE_INDEX_SCHEMA_VERSION,
        "generated_at": report["generated_at"],
        "report_name": report["report_name"],
        "gate_answer": report["gate_answer"],
        "asset_count": report["asset_count"],
        "symbols": report["symbols"],
        "input_report_count": report["input_report_count"],
        "observation_count": report["observation_count"],
        "mean_latest_score": report["mean_latest_score"],
        "mean_status_consistency_rate": report["mean_status_consistency_rate"],
        "report_path": str(report_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "index_path": str(index_path),
        "serve_entrypoint": str(html_path),
        "report_payload_sha256": report["report_payload_sha256"],
        "hypothetical_only": True,
        **_safe_stamp(),
    }
    _write_json(index_path, index)
    return index
