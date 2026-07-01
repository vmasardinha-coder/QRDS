"""Evidence Quality Gate for QRDS/QOS.

Sprint 8L adds a research-only gate that asks whether a hypothesis is
becoming reliable enough for continued research. It deliberately does not
produce trading signals, executable signals, recommendations, allocations,
orders, position sizing, portfolio decisions, or real-capital actions.
"""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

from crypto_decision_lab.contracts.research import (
    build_research_safety_stamp,
    collect_research_contract_issues,
)

EVIDENCE_QUALITY_GATE_SCHEMA_VERSION = "qrds.evidence_quality_gate.v1"
EVIDENCE_QUALITY_INDEX_SCHEMA_VERSION = "qrds.evidence_quality_index.v1"

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

EDGE_STATUS_SCORE = {
    "PROMISING_RESEARCH_ONLY": 1.0,
    "WEAK_EVIDENCE": 0.65,
    "INCONCLUSIVE": 0.35,
    "NO_EVIDENCE": 0.0,
}

NEXT_REQUIRED_GATES = [
    "data_coverage_gate",
    "data_quality_reliability_gate",
    "out_of_sample_validation_gate",
    "paper_trading_gate",
    "risk_model_gate",
    "human_approval_gate",
    "explicit_policy_change_from_research_only",
]


class EvidenceQualityError(ValueError):
    """Raised when an evidence quality artifact cannot be built safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _payload_sha256(payload: Any) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(data.encode("utf-8")).hexdigest()


def _read_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise EvidenceQualityError(f"JSON artifact not found: {file_path}")
    with file_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise EvidenceQualityError(f"JSON artifact must contain an object: {file_path}")
    return payload


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


def _as_float(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    number = _as_float(value)
    if number is None:
        return default
    return int(number)


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _score_data_volume(rows: int, *, min_dataset_rows: int) -> float:
    if rows >= max(min_dataset_rows * 2, min_dataset_rows + 1):
        return 1.0
    if rows >= min_dataset_rows:
        return 0.75
    if rows >= max(1, int(min_dataset_rows * 0.5)):
        return 0.5
    if rows > 0:
        return 0.25
    return 0.0


def _score_split_count(splits: int, *, min_walk_forward_splits: int) -> float:
    if splits >= max(min_walk_forward_splits + 2, min_walk_forward_splits):
        return 1.0
    if splits >= min_walk_forward_splits:
        return 0.75
    if splits >= 1:
        return 0.35
    return 0.0


def _score_edge(edge_status: Any, edge_score: Any) -> float:
    status_score = EDGE_STATUS_SCORE.get(str(edge_status), 0.0)
    numeric_score = _as_float(edge_score, default=None)
    if numeric_score is None:
        return status_score
    if numeric_score > 1.0:
        numeric_score = numeric_score / 100.0
    return _clip01(0.65 * status_score + 0.35 * _clip01(numeric_score))


def _stress_items(stress_report: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not stress_report:
        return {}

    by_symbol: dict[str, dict[str, Any]] = {}
    worst = stress_report.get("worst_case_by_symbol")

    if isinstance(worst, dict):
        for symbol, item in worst.items():
            if isinstance(item, dict):
                payload = dict(item)
                payload.setdefault("symbol", symbol)
                by_symbol[str(symbol)] = payload
    elif isinstance(worst, list):
        for item in worst:
            if isinstance(item, dict) and item.get("symbol"):
                by_symbol[str(item["symbol"])] = dict(item)

    for container_name in ("scenario_summaries", "results", "stress_results"):
        container = stress_report.get(container_name)
        if not isinstance(container, list):
            continue
        for item in container:
            if not isinstance(item, dict) or not item.get("symbol"):
                continue
            symbol = str(item["symbol"])
            current = by_symbol.get(symbol)
            if current is None:
                by_symbol[symbol] = dict(item)
                continue
            current_ratio = _extract_stress_retention(current)
            item_ratio = _extract_stress_retention(item)
            if item_ratio is not None and (current_ratio is None or item_ratio < current_ratio):
                by_symbol[symbol] = dict(item)

    return by_symbol


def _extract_stress_retention(item: dict[str, Any]) -> float | None:
    for key in (
        "edge_retention_ratio",
        "retention_ratio",
        "stress_retention_ratio",
        "worst_edge_retention_ratio",
    ):
        value = _as_float(item.get(key), default=None)
        if value is not None:
            return _clip01(value)

    base = _as_float(item.get("base_edge_score"), default=None)
    stressed = _as_float(
        item.get("stressed_edge_score", item.get("stress_edge_score", item.get("worst_stressed_edge_score"))),
        default=None,
    )
    if base is not None and base > 0 and stressed is not None:
        return _clip01(stressed / base)
    return None


def _score_stress(item: dict[str, Any] | None) -> tuple[float, str, float | None]:
    if not item:
        return 0.25, "UNKNOWN_STRESS_COVERAGE", None
    retention = _extract_stress_retention(item)
    if retention is not None:
        if retention >= 0.80:
            return 1.0, "STABLE_UNDER_STRESS_RESEARCH_ONLY", retention
        if retention >= 0.50:
            return 0.70, "WATCH_UNDER_STRESS_RESEARCH_ONLY", retention
        if retention >= 0.25:
            return 0.40, "FRAGILE_UNDER_STRESS_RESEARCH_ONLY", retention
        return 0.10, "UNSTABLE_UNDER_STRESS_RESEARCH_ONLY", retention

    status = str(
        item.get(
            "stressed_edge_status",
            item.get("stress_edge_status", item.get("edge_status", "UNKNOWN")),
        )
    )
    status_score = EDGE_STATUS_SCORE.get(status, 0.25)
    if status_score >= 0.65:
        return status_score, "STRESS_STATUS_ACCEPTABLE_RESEARCH_ONLY", None
    return status_score, "STRESS_STATUS_WEAK_RESEARCH_ONLY", None


def _entry_symbol(entry: dict[str, Any], fallback_index: int) -> str:
    return str(entry.get("symbol") or entry.get("asset") or f"UNKNOWN-{fallback_index}")


def _evaluate_entry(
    entry: dict[str, Any],
    *,
    stress_item: dict[str, Any] | None,
    min_dataset_rows: int,
    min_walk_forward_splits: int,
    pass_threshold: float,
    watch_threshold: float,
    fallback_index: int,
) -> dict[str, Any]:
    symbol = _entry_symbol(entry, fallback_index)
    rows = _as_int(entry.get("dataset_row_count", entry.get("row_count", entry.get("rows"))))
    splits = _as_int(entry.get("split_count", entry.get("walk_forward_split_count", entry.get("splits"))))
    edge_status = str(entry.get("edge_status", "NO_EVIDENCE"))
    edge_score_raw = entry.get("edge_score")

    data_score = _score_data_volume(rows, min_dataset_rows=min_dataset_rows)
    split_score = _score_split_count(splits, min_walk_forward_splits=min_walk_forward_splits)
    edge_score_component = _score_edge(edge_status, edge_score_raw)
    stress_score, stress_status, stress_retention = _score_stress(stress_item)

    weighted_score = _clip01(
        0.30 * data_score
        + 0.25 * split_score
        + 0.25 * stress_score
        + 0.20 * edge_score_component
    )

    blockers: list[str] = []
    warnings: list[str] = []
    if rows < min_dataset_rows:
        blockers.append("DATA_VOLUME_BELOW_RESEARCH_MINIMUM")
    if splits < min_walk_forward_splits:
        blockers.append("INSUFFICIENT_WALK_FORWARD_SPLITS")
    if stress_item is None:
        warnings.append("STRESS_COVERAGE_NOT_FOUND")
    elif stress_score < 0.50:
        blockers.append("STRESS_STABILITY_WEAK")
    if edge_status in {"NO_EVIDENCE", "INCONCLUSIVE"}:
        blockers.append(f"EDGE_STATUS_{edge_status}")

    hard_blockers = {
        "DATA_VOLUME_BELOW_RESEARCH_MINIMUM",
        "INSUFFICIENT_WALK_FORWARD_SPLITS",
        "STRESS_STABILITY_WEAK",
        "EDGE_STATUS_NO_EVIDENCE",
    }
    if any(blocker in hard_blockers for blocker in blockers) or weighted_score < watch_threshold:
        readiness = "FAIL"
        answer = "NO_NOT_RESEARCH_READY_YET"
    elif weighted_score >= pass_threshold and not blockers:
        readiness = "PASS"
        answer = "YES_RESEARCH_READY_FOR_CONTINUED_RESEARCH_ONLY"
    else:
        readiness = "WATCH"
        answer = "PARTIAL_MORE_EVIDENCE_REQUIRED_RESEARCH_ONLY"

    return {
        "symbol": symbol,
        "dataset_row_count": rows,
        "data_volume_score": round(data_score, 4),
        "split_count": splits,
        "walk_forward_split_score": round(split_score, 4),
        "edge_status": edge_status,
        "edge_score": edge_score_raw,
        "edge_quality_score": round(edge_score_component, 4),
        "stress_status": stress_status,
        "stress_retention_ratio": stress_retention,
        "stress_stability_score": round(stress_score, 4),
        "research_readiness_score": round(weighted_score, 4),
        "research_readiness": readiness,
        "gate_answer": answer,
        "blockers": blockers,
        "warnings": warnings,
        "decision_scope": "research_readiness_only",
        "hypothetical_only": True,
        **_safe_stamp(),
    }


def build_evidence_quality_gate(
    multi_asset_report: dict[str, Any],
    stress_report: dict[str, Any] | None = None,
    *,
    report_name: str = "qrds-evidence-quality-gate",
    min_dataset_rows: int = 1000,
    min_walk_forward_splits: int = 3,
    pass_threshold: float = 0.75,
    watch_threshold: float = 0.50,
) -> dict[str, Any]:
    """Build a research-only Evidence Quality Gate report."""
    if not isinstance(multi_asset_report, dict):
        raise EvidenceQualityError("multi_asset_report must be a dictionary.")
    entries = multi_asset_report.get("entries")
    if not isinstance(entries, list) or not entries:
        raise EvidenceQualityError("multi_asset_report must include a non-empty entries list.")

    stress_by_symbol = _stress_items(stress_report)
    evaluations = [
        _evaluate_entry(
            entry,
            stress_item=stress_by_symbol.get(_entry_symbol(entry, i)),
            min_dataset_rows=min_dataset_rows,
            min_walk_forward_splits=min_walk_forward_splits,
            pass_threshold=pass_threshold,
            watch_threshold=watch_threshold,
            fallback_index=i,
        )
        for i, entry in enumerate(entries)
        if isinstance(entry, dict)
    ]
    if not evaluations:
        raise EvidenceQualityError("No valid multi-asset entries found for evidence quality gate.")

    readiness_counts: dict[str, int] = {}
    for item in evaluations:
        readiness_counts[item["research_readiness"]] = readiness_counts.get(item["research_readiness"], 0) + 1

    pass_count = readiness_counts.get("PASS", 0)
    watch_count = readiness_counts.get("WATCH", 0)
    fail_count = readiness_counts.get("FAIL", 0)
    asset_count = len(evaluations)
    mean_score = mean(item["research_readiness_score"] for item in evaluations)

    if pass_count == asset_count:
        overall_answer = "YES_RESEARCH_EVIDENCE_IS_MATURING_RESEARCH_ONLY"
    elif pass_count + watch_count > 0:
        overall_answer = "PARTIAL_EVIDENCE_IS_MATURING_BUT_MORE_GATES_REQUIRED_RESEARCH_ONLY"
    else:
        overall_answer = "NO_EVIDENCE_NOT_RESEARCH_READY_YET"

    report = {
        "schema": EVIDENCE_QUALITY_GATE_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "report_name": report_name,
        "gate_name": "Evidence Quality Gate v1",
        "gate_question": "Is this hypothesis becoming reliable enough for continued research?",
        "gate_answer": overall_answer,
        "decision_scope": "research_readiness_only",
        "asset_count": asset_count,
        "symbols": [item["symbol"] for item in evaluations],
        "mean_research_readiness_score": round(mean_score, 4),
        "readiness_counts": readiness_counts,
        "pass_count": pass_count,
        "watch_count": watch_count,
        "fail_count": fail_count,
        "thresholds": {
            "min_dataset_rows": min_dataset_rows,
            "min_walk_forward_splits": min_walk_forward_splits,
            "pass_threshold": pass_threshold,
            "watch_threshold": watch_threshold,
        },
        "dimensions": [
            "data_volume",
            "walk_forward_split_count",
            "stress_stability",
            "edge_status",
            "research_readiness",
        ],
        "evaluations": evaluations,
        "next_required_gates": list(NEXT_REQUIRED_GATES),
        "caveats": [
            "Research-only evidence gate; not an operational decision layer.",
            "A PASS means only that the hypothesis is more suitable for continued research.",
            "Out-of-sample validation, paper trading, risk model, human approval and policy change remain mandatory before any operational layer.",
        ],
        "source_payload_sha256": {
            "multi_asset_report": _payload_sha256(multi_asset_report),
            "stress_report": _payload_sha256(stress_report) if stress_report else None,
        },
        "hypothetical_only": True,
        **_safe_stamp(),
    }
    return report


def validate_evidence_quality_gate(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Return validation issues for an Evidence Quality Gate report."""
    issues = collect_research_contract_issues(
        report,
        name="evidence_quality_gate",
        require_schema=True,
        require_app_mode=True,
        require_research_allowed=True,
    )
    if report.get("schema") != EVIDENCE_QUALITY_GATE_SCHEMA_VERSION:
        issues.append(
            {
                "code": "INVALID_EVIDENCE_QUALITY_SCHEMA",
                "severity": "error",
                "name": "evidence_quality_gate",
                "message": "Invalid evidence quality schema.",
            }
        )
    if report.get("decision_scope") != "research_readiness_only":
        issues.append(
            {
                "code": "INVALID_DECISION_SCOPE",
                "severity": "error",
                "name": "evidence_quality_gate",
                "message": "Evidence quality gate must remain research_readiness_only.",
            }
        )
    if not report.get("evaluations"):
        issues.append(
            {
                "code": "MISSING_EVIDENCE_EVALUATIONS",
                "severity": "error",
                "name": "evidence_quality_gate",
                "message": "Evidence quality gate must include per-symbol evaluations.",
            }
        )
    for flag in RESEARCH_ONLY_FALSE_FLAGS:
        if report.get(flag) is True:
            issues.append(
                {
                    "code": "UNSAFE_EVIDENCE_FLAG",
                    "severity": "error",
                    "name": "evidence_quality_gate",
                    "flag": flag,
                    "message": f"{flag} must remain False.",
                }
            )
    return issues


def _format_float(value: Any) -> str:
    number = _as_float(value, default=None)
    if number is None:
        return "n/a"
    return f"{number:.2f}"


def render_evidence_quality_markdown(report: dict[str, Any]) -> str:
    """Render a human-readable research-only markdown report."""
    lines = [
        "# QRDS Evidence Quality Gate v1",
        "",
        "## Gate answer",
        "",
        f"- Gate question: `{report.get('gate_question')}`",
        f"- Gate answer: `{report.get('gate_answer')}`",
        f"- Decision scope: `{report.get('decision_scope')}`",
        f"- Mode: `{report.get('app_mode')}`",
        f"- Mean research readiness score: `{report.get('mean_research_readiness_score')}`",
        "",
        "## Readiness counts",
        "",
    ]
    for key, value in sorted(report.get("readiness_counts", {}).items()):
        lines.append(f"- `{key}`: `{value}`")

    lines.extend(
        [
            "",
            "## Per-symbol evidence quality",
            "",
            "| Symbol | Rows | Splits | Edge status | Stress | Score | Readiness | Blockers |",
            "|---|---:|---:|---|---|---:|---|---|",
        ]
    )
    for item in report.get("evaluations", []):
        blockers = ", ".join(item.get("blockers", [])) or "-"
        lines.append(
            f"| `{item.get('symbol')}` | `{item.get('dataset_row_count')}` | "
            f"`{item.get('split_count')}` | `{item.get('edge_status')}` | "
            f"`{item.get('stress_status')}` | `{_format_float(item.get('research_readiness_score'))}` | "
            f"`{item.get('research_readiness')}` | `{blockers}` |"
        )

    lines.extend(
        [
            "",
            "## Next required gates before any operational layer",
            "",
        ]
    )
    for gate in report.get("next_required_gates", []):
        lines.append(f"- `{gate}`")

    lines.extend(
        [
            "",
            "## Safety flags",
            "",
            "```text",
        ]
    )
    for flag in RESEARCH_ONLY_FALSE_FLAGS:
        lines.append(f"{flag} = {report.get(flag)}")
    lines.extend(
        [
            "research_allowed = True",
            "app_mode = INTERACTIVE_RESEARCH_ONLY",
            "```",
            "",
            "This artifact is for research interpretation only. It does not produce executable signals, recommendations, allocations, orders or real-capital actions.",
            "",
        ]
    )
    return "\n".join(lines)


def render_evidence_quality_html(report: dict[str, Any]) -> str:
    """Render a standalone static HTML page for the Evidence Quality Gate."""
    rows = []
    for item in report.get("evaluations", []):
        blockers = ", ".join(item.get("blockers", [])) or "-"
        warnings = ", ".join(item.get("warnings", [])) or "-"
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('symbol')))}</td>"
            f"<td>{item.get('dataset_row_count')}</td>"
            f"<td>{item.get('split_count')}</td>"
            f"<td>{html.escape(str(item.get('edge_status')))}</td>"
            f"<td>{html.escape(str(item.get('stress_status')))}</td>"
            f"<td>{_format_float(item.get('research_readiness_score'))}</td>"
            f"<td><strong>{html.escape(str(item.get('research_readiness')))}</strong></td>"
            f"<td>{html.escape(blockers)}</td>"
            f"<td>{html.escape(warnings)}</td>"
            "</tr>"
        )

    safety_lines = "\n".join(f"{flag} = {report.get(flag)}" for flag in RESEARCH_ONLY_FALSE_FLAGS)
    next_gates = "".join(
        f"<li><code>{html.escape(str(gate))}</code></li>" for gate in report.get("next_required_gates", [])
    )
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>QRDS Evidence Quality Gate v1</title>
  <style>
    :root {{ color-scheme: dark; font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif; }}
    body {{ margin: 0; background: #0b1020; color: #edf2ff; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 32px 20px 56px; }}
    .hero {{ border: 1px solid #24304f; border-radius: 24px; padding: 28px; background: linear-gradient(135deg, #111a33, #0e162c); box-shadow: 0 20px 80px rgba(0,0,0,.35); }}
    .badge {{ display: inline-block; padding: 6px 10px; border: 1px solid #3b4d7a; border-radius: 999px; color: #b9c7ff; font-size: 13px; }}
    h1 {{ margin: 16px 0 8px; font-size: clamp(30px, 5vw, 54px); line-height: 1; }}
    h2 {{ margin-top: 30px; }}
    .answer {{ font-size: 20px; color: #d8e2ff; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; margin: 22px 0; }}
    .card {{ border: 1px solid #25375f; background: #111936; border-radius: 18px; padding: 18px; }}
    .card .label {{ color: #91a2d8; font-size: 13px; }}
    .card .value {{ font-size: 28px; font-weight: 750; margin-top: 6px; }}
    table {{ width: 100%; border-collapse: collapse; overflow: hidden; border-radius: 16px; border: 1px solid #25375f; }}
    th, td {{ padding: 12px 10px; border-bottom: 1px solid #25375f; text-align: left; vertical-align: top; }}
    th {{ background: #162141; color: #c8d4ff; font-size: 13px; }}
    tr:nth-child(even) td {{ background: rgba(255,255,255,.025); }}
    code, pre {{ background: #070b16; color: #dbe5ff; border: 1px solid #23345a; border-radius: 12px; }}
    code {{ padding: 2px 6px; }}
    pre {{ padding: 16px; overflow: auto; }}
    .note {{ color: #b5c2ed; line-height: 1.55; }}
    a {{ color: #9db7ff; }}
  </style>
</head>
<body>
<main>
  <section class=\"hero\">
    <span class=\"badge\">QRDS / QOS • INTERACTIVE_RESEARCH_ONLY • Sprint 8L</span>
    <h1>Evidence Quality Gate v1</h1>
    <p class=\"answer\"><strong>Gate answer:</strong> <code>{html.escape(str(report.get('gate_answer')))}</code></p>
    <p class=\"note\">Question: {html.escape(str(report.get('gate_question')))}</p>
  </section>

  <section class=\"cards\">
    <div class=\"card\"><div class=\"label\">Mean readiness score</div><div class=\"value\">{_format_float(report.get('mean_research_readiness_score'))}</div></div>
    <div class=\"card\"><div class=\"label\">Assets</div><div class=\"value\">{report.get('asset_count')}</div></div>
    <div class=\"card\"><div class=\"label\">PASS</div><div class=\"value\">{report.get('pass_count')}</div></div>
    <div class=\"card\"><div class=\"label\">WATCH</div><div class=\"value\">{report.get('watch_count')}</div></div>
    <div class=\"card\"><div class=\"label\">FAIL</div><div class=\"value\">{report.get('fail_count')}</div></div>
  </section>

  <h2>Per-symbol evidence quality</h2>
  <table>
    <thead><tr><th>Symbol</th><th>Rows</th><th>Splits</th><th>Edge</th><th>Stress</th><th>Score</th><th>Readiness</th><th>Blockers</th><th>Warnings</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>

  <h2>Next required gates</h2>
  <ul>{next_gates}</ul>

  <h2>Research-only safety</h2>
  <pre>{html.escape(safety_lines)}
research_allowed = True
app_mode = INTERACTIVE_RESEARCH_ONLY</pre>

  <p class=\"note\">This page measures evidence maturity for research only. It is not a signal, recommendation, allocation, order, or operational decision.</p>
</main>
</body>
</html>
"""


def _resolve_index_target(index_path: Path, payload: dict[str, Any], keys: Iterable[str]) -> dict[str, Any]:
    for key in keys:
        target = payload.get(key)
        if not isinstance(target, str) or not target:
            continue
        target_path = Path(target)
        if not target_path.is_absolute():
            target_path = index_path.parent / target_path
        if target_path.exists():
            return _read_json(target_path)
    return payload


def load_multi_asset_report_payload(path: str | Path) -> dict[str, Any]:
    """Load a multi-asset report from a report JSON or index JSON."""
    index_path = Path(path)
    payload = _read_json(index_path)
    return _resolve_index_target(
        index_path,
        payload,
        keys=("report_path", "multi_asset_report_path", "multi_asset_research_report_path"),
    )


def load_stress_report_payload(path: str | Path) -> dict[str, Any]:
    """Load a stress report from a report JSON or index JSON."""
    index_path = Path(path)
    payload = _read_json(index_path)
    return _resolve_index_target(
        index_path,
        payload,
        keys=("stress_report_path", "scenario_stress_report_path", "report_path"),
    )


def build_fixture_upstream_inputs(symbols: list[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build deterministic offline research fixtures when upstream artifacts are absent."""
    if not symbols:
        raise EvidenceQualityError("At least one symbol is required.")
    entries: list[dict[str, Any]] = []
    stress_results: list[dict[str, Any]] = []
    status_cycle = ["PROMISING_RESEARCH_ONLY", "WEAK_EVIDENCE", "INCONCLUSIVE"]
    for i, symbol in enumerate(symbols):
        edge_status = status_cycle[i % len(status_cycle)]
        edge_score = round(0.72 - 0.08 * min(i, 4), 4)
        rows = 1440 + 240 * i
        splits = 4 if i % 3 != 2 else 3
        retention = round(max(0.35, 0.82 - 0.10 * i), 4)
        entries.append(
            {
                "symbol": symbol,
                "interval": "1h",
                "source": "offline_fixture_replay",
                "edge_status": edge_status,
                "edge_score": edge_score,
                "dataset_row_count": rows,
                "split_count": splits,
                "integration_health_passed": True,
                "hypothetical_only": True,
                **_safe_stamp(),
            }
        )
        stress_results.append(
            {
                "symbol": symbol,
                "scenario": "fixture_downside_stress_research_only",
                "base_edge_score": edge_score,
                "edge_retention_ratio": retention,
                "stressed_edge_score": round(edge_score * retention, 4),
                "stressed_edge_status": edge_status if retention >= 0.50 else "INCONCLUSIVE",
                "hypothetical_only": True,
                **_safe_stamp(),
            }
        )

    multi_asset_report = {
        "schema": "qrds.multi_asset_report.v1.fixture_for_evidence_quality",
        "generated_at": _utc_now(),
        "report_name": "qrds-evidence-quality-fixture-multi-asset-input",
        "asset_count": len(entries),
        "symbols": symbols,
        "entries": entries,
        "rankings": [
            {
                "rank": i + 1,
                "symbol": entry["symbol"],
                "edge_status": entry["edge_status"],
                "edge_score": entry["edge_score"],
                "ranking_basis": "fixture_input_for_evidence_quality_research_only",
            }
            for i, entry in enumerate(entries)
        ],
        "allocation_generated": False,
        "portfolio_decision_generated": False,
        "hypothetical_only": True,
        **_safe_stamp(),
    }
    stress_report = {
        "schema": "qrds.scenario_stress_pack.v1.fixture_for_evidence_quality",
        "generated_at": _utc_now(),
        "report_name": "qrds-evidence-quality-fixture-stress-input",
        "symbols": symbols,
        "results": stress_results,
        "scenario_summaries": stress_results,
        "worst_case_by_symbol": {item["symbol"]: item for item in stress_results},
        "allocation_generated": False,
        "portfolio_decision_generated": False,
        "hypothetical_only": True,
        **_safe_stamp(),
    }
    return multi_asset_report, stress_report


def write_fixture_upstream_inputs(output_dir: str | Path, symbols: list[str]) -> dict[str, Any]:
    """Write deterministic fixture upstream inputs and return their payloads/paths."""
    root = Path(output_dir)
    multi_asset_report, stress_report = build_fixture_upstream_inputs(symbols)
    multi_path = root / "fixture_multi_asset_report.json"
    stress_path = root / "fixture_stress_report.json"
    _write_json(multi_path, multi_asset_report)
    _write_json(stress_path, stress_report)
    return {
        "multi_asset_report": multi_asset_report,
        "stress_report": stress_report,
        "multi_asset_report_path": str(multi_path),
        "stress_report_path": str(stress_path),
    }


def write_evidence_quality_gate(
    *,
    multi_asset_report: dict[str, Any],
    stress_report: dict[str, Any] | None,
    output_dir: str | Path,
    report_name: str = "qrds-evidence-quality-gate",
    min_dataset_rows: int = 1000,
    min_walk_forward_splits: int = 3,
    pass_threshold: float = 0.75,
    watch_threshold: float = 0.50,
) -> dict[str, Any]:
    """Write Evidence Quality Gate JSON, Markdown, HTML and index."""
    report = build_evidence_quality_gate(
        multi_asset_report,
        stress_report,
        report_name=report_name,
        min_dataset_rows=min_dataset_rows,
        min_walk_forward_splits=min_walk_forward_splits,
        pass_threshold=pass_threshold,
        watch_threshold=watch_threshold,
    )
    issues = validate_evidence_quality_gate(report)
    if any(issue["severity"] == "error" for issue in issues):
        raise EvidenceQualityError(f"Evidence Quality Gate validation errors: {issues}")

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    report_path = root / "evidence_quality_gate.json"
    markdown_path = root / "evidence_quality_gate.md"
    html_path = root / "index.html"
    index_path = root / "evidence_quality_index.json"

    _write_json(report_path, report)
    _write_text(markdown_path, render_evidence_quality_markdown(report))
    _write_text(html_path, render_evidence_quality_html(report))

    index = {
        "schema": EVIDENCE_QUALITY_INDEX_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "report_name": report_name,
        "report_path": str(report_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "index_path": str(index_path),
        "serve_entrypoint": str(html_path),
        "asset_count": report["asset_count"],
        "symbols": report["symbols"],
        "gate_answer": report["gate_answer"],
        "mean_research_readiness_score": report["mean_research_readiness_score"],
        "report_payload_sha256": _payload_sha256(report),
        "hypothetical_only": True,
        **_safe_stamp(),
    }
    _write_json(index_path, index)
    return index
