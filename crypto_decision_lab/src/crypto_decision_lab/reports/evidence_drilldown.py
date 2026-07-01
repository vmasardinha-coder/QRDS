"""Evidence Drilldown / Data Coverage Gate for QRDS/QOS.

Sprint 8M sits after Sprint 8L. It explains why an Evidence Quality Gate
asset is PASS, WATCH, or FAIL from a research-readiness perspective only.
It deliberately does not produce trading signals, executable signals,
recommendations, allocations, position sizing, orders, portfolio decisions,
or real-capital actions.
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
from crypto_decision_lab.reports.evidence_quality import (
    EvidenceQualityError,
    build_evidence_quality_gate,
    build_fixture_upstream_inputs,
)

EVIDENCE_DRILLDOWN_SCHEMA_VERSION = "qrds.evidence_drilldown.v1"
EVIDENCE_DRILLDOWN_INDEX_SCHEMA_VERSION = "qrds.evidence_drilldown_index.v1"

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

DRILLDOWN_DIMENSIONS = (
    "data_volume",
    "walk_forward_splits",
    "stress_stability",
    "edge_quality",
    "artifact_lineage",
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

NEXT_REQUIRED_GATES = [
    "data_coverage_gate",
    "data_quality_reliability_gate",
    "out_of_sample_validation_gate",
    "paper_trading_gate",
    "risk_model_gate",
    "human_approval_gate",
    "explicit_policy_change_from_research_only",
]


class EvidenceDrilldownError(ValueError):
    """Raised when a drilldown artifact cannot be built safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _payload_sha256(payload: Any) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(data.encode("utf-8")).hexdigest()


def _read_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise EvidenceDrilldownError(f"JSON artifact not found: {file_path}")
    with file_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise EvidenceDrilldownError(f"JSON artifact must contain an object: {file_path}")
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


def _as_int(value: Any, default: int = 0) -> int:
    number = _as_float(value)
    if number is None:
        return default
    return int(number)


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _status_from_score(score: float, *, pass_threshold: float, watch_threshold: float) -> str:
    if score >= pass_threshold:
        return "PASS"
    if score >= watch_threshold:
        return "WATCH"
    return "FAIL"


def _dimension_status(score: float) -> str:
    return _status_from_score(score, pass_threshold=0.75, watch_threshold=0.50)


def _dimension_explanation(dimension: str, score: float, status: str) -> str:
    base = {
        "data_volume": "Volume de dados disponível para pesquisa.",
        "walk_forward_splits": "Quantidade de janelas walk-forward sustentando a leitura.",
        "stress_stability": "Retenção de edge/score sob cenários de stress.",
        "edge_quality": "Qualidade do edge reportado antes de qualquer camada operacional.",
        "artifact_lineage": "Rastreabilidade mínima do artefato usado como entrada.",
    }.get(dimension, "Dimensão de pesquisa.")
    if status == "PASS":
        return f"{base} Suficiente para continuar pesquisa, sem virar decisão."
    if status == "WATCH":
        return f"{base} Parcial; manter em observação e reforçar evidência."
    return f"{base} Fraco; bloquear avanço para gates posteriores."


def _next_action_for_dimension(dimension: str, status: str, gap: Any) -> str:
    if status == "PASS":
        return "Preservar rastreabilidade e repetir validação em novos ciclos de pesquisa."
    if dimension == "data_volume":
        return f"Aumentar cobertura de candles/linhas antes de interpretar modelos; lacuna atual: {gap}."
    if dimension == "walk_forward_splits":
        return f"Adicionar janelas walk-forward antes de promover a hipótese; lacuna atual: {gap}."
    if dimension == "stress_stability":
        return f"Reexecutar stress pack e investigar queda de estabilidade; lacuna atual: {gap}."
    if dimension == "edge_quality":
        return "Revisar benchmark/edge report e comparar contra baseline antes de avançar."
    if dimension == "artifact_lineage":
        return "Anexar hashes, schemas e caminhos dos artefatos de origem antes de confiar no resultado."
    return "Coletar evidência adicional em modo research-only."


def _artifact_lineage_score(report: dict[str, Any]) -> float:
    source_hash = report.get("source_payload_sha256")
    if isinstance(source_hash, dict) and source_hash.get("multi_asset_report"):
        return 1.0
    if report.get("report_payload_sha256"):
        return 0.75
    return 0.35


def _score_gap(score: float, target: float) -> float:
    return round(max(0.0, target - score), 4)


def _dimension_row(name: str, *, score: float, status: str, raw_value: Any, target: Any, gap: Any) -> dict[str, Any]:
    return {
        "dimension": name,
        "score": round(_clip01(score), 4),
        "status": status,
        "raw_value": raw_value,
        "target": target,
        "gap_to_target": gap,
        "explanation": _dimension_explanation(name, score, status),
        "next_research_action": _next_action_for_dimension(name, status, gap),
        "decision_scope": "research_diagnostic_only",
        "hypothetical_only": True,
        **_safe_stamp(),
    }


def _build_symbol_drilldown(
    item: dict[str, Any],
    *,
    evidence_report: dict[str, Any],
    min_dataset_rows: int,
    min_walk_forward_splits: int,
    min_stress_retention_ratio: float,
    min_research_readiness_score: float,
) -> dict[str, Any]:
    symbol = str(item.get("symbol", "UNKNOWN"))
    rows = _as_int(item.get("dataset_row_count"))
    splits = _as_int(item.get("split_count"))
    data_score = _clip01(_as_float(item.get("data_volume_score"), 0.0) or 0.0)
    split_score = _clip01(_as_float(item.get("walk_forward_split_score"), 0.0) or 0.0)
    stress_score = _clip01(_as_float(item.get("stress_stability_score"), 0.0) or 0.0)
    edge_score = _clip01(_as_float(item.get("edge_quality_score"), 0.0) or 0.0)
    readiness_score = _clip01(_as_float(item.get("research_readiness_score"), 0.0) or 0.0)
    stress_retention = _as_float(item.get("stress_retention_ratio"), None)
    lineage_score = _artifact_lineage_score(evidence_report)

    stress_gap: str | float
    if stress_retention is None:
        stress_gap = "stress_retention_missing"
    else:
        stress_gap = round(max(0.0, min_stress_retention_ratio - stress_retention), 4)

    dimensions = [
        _dimension_row(
            "data_volume",
            score=data_score,
            status=_dimension_status(data_score),
            raw_value=rows,
            target=min_dataset_rows,
            gap=max(0, min_dataset_rows - rows),
        ),
        _dimension_row(
            "walk_forward_splits",
            score=split_score,
            status=_dimension_status(split_score),
            raw_value=splits,
            target=min_walk_forward_splits,
            gap=max(0, min_walk_forward_splits - splits),
        ),
        _dimension_row(
            "stress_stability",
            score=stress_score,
            status=_dimension_status(stress_score),
            raw_value=stress_retention,
            target=min_stress_retention_ratio,
            gap=stress_gap,
        ),
        _dimension_row(
            "edge_quality",
            score=edge_score,
            status=_dimension_status(edge_score),
            raw_value=item.get("edge_status"),
            target="edge_quality_score>=0.50 and non-operational research edge",
            gap=_score_gap(edge_score, 0.50),
        ),
        _dimension_row(
            "artifact_lineage",
            score=lineage_score,
            status=_dimension_status(lineage_score),
            raw_value=list((evidence_report.get("source_payload_sha256") or {}).keys())
            if isinstance(evidence_report.get("source_payload_sha256"), dict)
            else [],
            target="source_payload_sha256.multi_asset_report present",
            gap=_score_gap(lineage_score, 0.75),
        ),
    ]

    fail_dimensions = [row["dimension"] for row in dimensions if row["status"] == "FAIL"]
    watch_dimensions = [row["dimension"] for row in dimensions if row["status"] == "WATCH"]
    blocker_list = list(item.get("blockers") or [])
    warning_list = list(item.get("warnings") or [])

    if fail_dimensions or readiness_score < min_research_readiness_score or item.get("research_readiness") == "FAIL":
        coverage_status = "FAIL"
        coverage_answer = "NO_RESEARCH_COVERAGE_NOT_READY_YET"
    elif watch_dimensions or item.get("research_readiness") == "WATCH":
        coverage_status = "WATCH"
        coverage_answer = "PARTIAL_RESEARCH_COVERAGE_NEEDS_MORE_EVIDENCE"
    else:
        coverage_status = "PASS"
        coverage_answer = "YES_RESEARCH_COVERAGE_SUPPORTS_CONTINUED_RESEARCH_ONLY"

    next_actions = [row["next_research_action"] for row in dimensions if row["status"] != "PASS"]
    if not next_actions:
        next_actions = ["Repetir a leitura em novos artefatos e só avançar para o próximo gate formal de pesquisa."]

    return {
        "symbol": symbol,
        "coverage_status": coverage_status,
        "coverage_answer": coverage_answer,
        "research_readiness": item.get("research_readiness"),
        "research_readiness_score": round(readiness_score, 4),
        "dimension_rows": dimensions,
        "fail_dimensions": fail_dimensions,
        "watch_dimensions": watch_dimensions,
        "blockers": blocker_list,
        "warnings": warning_list,
        "next_research_actions": next_actions,
        "decision_scope": "evidence_drilldown_research_only",
        "hypothetical_only": True,
        **_safe_stamp(),
    }


def _assert_research_only_payload(payload: dict[str, Any]) -> None:
    for flag in RESEARCH_ONLY_FALSE_FLAGS:
        if payload.get(flag) is not False:
            raise EvidenceDrilldownError(f"Research-only flag must be false: {flag}")

    issues = _collect_research_issues(payload, name="evidence_drilldown")
    blocking = [issue for issue in issues if issue.get("severity") in {"error", "blocker"}]
    if blocking:
        raise EvidenceDrilldownError(f"Research contract failed: {blocking}")


def build_evidence_drilldown(
    evidence_report: dict[str, Any],
    *,
    report_name: str = "qrds-evidence-drilldown-gate",
    min_dataset_rows: int | None = None,
    min_walk_forward_splits: int | None = None,
    min_stress_retention_ratio: float = 0.50,
    min_research_readiness_score: float = 0.50,
) -> dict[str, Any]:
    """Build a research-only drilldown report over the 8L Evidence Quality Gate."""
    if not isinstance(evidence_report, dict):
        raise EvidenceDrilldownError("evidence_report must be a dictionary.")
    evaluations = evidence_report.get("evaluations")
    if not isinstance(evaluations, list) or not evaluations:
        raise EvidenceDrilldownError("evidence_report must include a non-empty evaluations list.")

    thresholds = evidence_report.get("thresholds") if isinstance(evidence_report.get("thresholds"), dict) else {}
    resolved_min_rows = int(min_dataset_rows or thresholds.get("min_dataset_rows") or 1000)
    resolved_min_splits = int(min_walk_forward_splits or thresholds.get("min_walk_forward_splits") or 3)

    drilldowns = [
        _build_symbol_drilldown(
            item,
            evidence_report=evidence_report,
            min_dataset_rows=resolved_min_rows,
            min_walk_forward_splits=resolved_min_splits,
            min_stress_retention_ratio=min_stress_retention_ratio,
            min_research_readiness_score=min_research_readiness_score,
        )
        for item in evaluations
        if isinstance(item, dict)
    ]
    if not drilldowns:
        raise EvidenceDrilldownError("No valid evaluations found for evidence drilldown.")

    status_counts: dict[str, int] = {}
    dimension_counts: dict[str, dict[str, int]] = {}
    for item in drilldowns:
        status = str(item["coverage_status"])
        status_counts[status] = status_counts.get(status, 0) + 1
        for row in item["dimension_rows"]:
            dimension = str(row["dimension"])
            row_status = str(row["status"])
            bucket = dimension_counts.setdefault(dimension, {"PASS": 0, "WATCH": 0, "FAIL": 0})
            bucket[row_status] = bucket.get(row_status, 0) + 1

    pass_count = status_counts.get("PASS", 0)
    watch_count = status_counts.get("WATCH", 0)
    fail_count = status_counts.get("FAIL", 0)
    asset_count = len(drilldowns)
    mean_score = mean(item["research_readiness_score"] for item in drilldowns)

    if pass_count == asset_count:
        gate_answer = "YES_COVERAGE_DRILLDOWN_SUPPORTS_CONTINUED_RESEARCH_ONLY"
    elif pass_count + watch_count > 0:
        gate_answer = "PARTIAL_COVERAGE_DRILLDOWN_MORE_EVIDENCE_REQUIRED_RESEARCH_ONLY"
    else:
        gate_answer = "NO_COVERAGE_DRILLDOWN_NOT_READY_FOR_NEXT_RESEARCH_GATE"

    weakest_dimensions = sorted(
        dimension_counts.items(),
        key=lambda pair: (pair[1].get("FAIL", 0), pair[1].get("WATCH", 0)),
        reverse=True,
    )

    report = {
        "schema": EVIDENCE_DRILLDOWN_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "report_name": report_name,
        "gate_name": "Evidence Drilldown / Data Coverage Gate v1",
        "gate_question": "Why did the evidence pass, fail, or remain under watch for research?",
        "gate_answer": gate_answer,
        "decision_scope": "evidence_drilldown_research_only",
        "asset_count": asset_count,
        "symbols": [item["symbol"] for item in drilldowns],
        "mean_research_readiness_score": round(mean_score, 4),
        "coverage_status_counts": status_counts,
        "dimension_status_counts": dimension_counts,
        "weakest_dimensions": [
            {
                "dimension": dimension,
                "fail_count": counts.get("FAIL", 0),
                "watch_count": counts.get("WATCH", 0),
                "pass_count": counts.get("PASS", 0),
            }
            for dimension, counts in weakest_dimensions
        ],
        "thresholds": {
            "min_dataset_rows": resolved_min_rows,
            "min_walk_forward_splits": resolved_min_splits,
            "min_stress_retention_ratio": min_stress_retention_ratio,
            "min_research_readiness_score": min_research_readiness_score,
        },
        "dimensions": list(DRILLDOWN_DIMENSIONS),
        "drilldowns": drilldowns,
        "next_required_gates": list(NEXT_REQUIRED_GATES),
        "caveats": [
            "Research-only drilldown; it explains evidence gaps and does not authorize operation.",
            "A PASS means the research artifact can be investigated further, not used with real capital.",
            "Out-of-sample validation, paper trading, risk model, human approval, and explicit policy change remain mandatory.",
        ],
        "source_payload_sha256": {
            "evidence_quality_report": _payload_sha256(evidence_report),
        },
        "hypothetical_only": True,
        **_safe_stamp(),
    }
    _assert_research_only_payload(report)
    return report


def validate_evidence_drilldown(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Return validation issues for a drilldown report."""
    issues: list[dict[str, Any]] = []
    if report.get("schema") != EVIDENCE_DRILLDOWN_SCHEMA_VERSION:
        issues.append({"severity": "error", "code": "SCHEMA_MISMATCH"})

    for flag in RESEARCH_ONLY_FALSE_FLAGS:
        if report.get(flag) is not False:
            issues.append({"severity": "error", "code": f"RESEARCH_ONLY_FLAG_NOT_FALSE:{flag}"})

    if report.get("decision_scope") != "evidence_drilldown_research_only":
        issues.append({"severity": "error", "code": "INVALID_DECISION_SCOPE"})

    text_blob = json.dumps(report, sort_keys=True).lower()
    for term in FORBIDDEN_OPERATIONAL_TERMS:
        if term in text_blob:
            issues.append({"severity": "warning", "code": f"OPERATIONAL_TERM_PRESENT:{term}"})

    issues.extend(_collect_research_issues(report, name="evidence_drilldown"))
    return issues


def _format_float(value: Any) -> str:
    number = _as_float(value)
    if number is None:
        return "n/a"
    return f"{number:.3f}"


def render_evidence_drilldown_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# QRDS Evidence Drilldown / Data Coverage Gate v1",
        "",
        f"Generated at: `{report.get('generated_at')}`",
        "",
        f"Gate answer: `{report.get('gate_answer')}`",
        "",
        "Scope: research drilldown only. No operational decision, no signal, no recommendation, no allocation, no order, no real capital.",
        "",
        "## Summary",
        "",
        f"- Assets: {report.get('asset_count')}",
        f"- Mean research readiness score: {_format_float(report.get('mean_research_readiness_score'))}",
        f"- Coverage status counts: `{json.dumps(report.get('coverage_status_counts', {}), sort_keys=True)}`",
        "",
        "## Weakest dimensions",
        "",
    ]
    for item in report.get("weakest_dimensions", []):
        lines.append(
            f"- {item.get('dimension')}: FAIL={item.get('fail_count')}, WATCH={item.get('watch_count')}, PASS={item.get('pass_count')}"
        )

    lines.extend(["", "## Symbol drilldown", ""])
    for item in report.get("drilldowns", []):
        lines.extend(
            [
                f"### {item.get('symbol')}",
                "",
                f"- Coverage status: `{item.get('coverage_status')}`",
                f"- Coverage answer: `{item.get('coverage_answer')}`",
                f"- Research readiness: `{item.get('research_readiness')}`",
                f"- Research readiness score: {_format_float(item.get('research_readiness_score'))}",
                f"- Fail dimensions: `{json.dumps(item.get('fail_dimensions', []), sort_keys=True)}`",
                f"- Watch dimensions: `{json.dumps(item.get('watch_dimensions', []), sort_keys=True)}`",
                "",
                "| Dimension | Status | Score | Raw | Target | Gap | Next research action |",
                "|---|---:|---:|---:|---|---:|---|",
            ]
        )
        for row in item.get("dimension_rows", []):
            lines.append(
                "| {dimension} | {status} | {score} | {raw_value} | {target} | {gap_to_target} | {next_research_action} |".format(
                    dimension=row.get("dimension"),
                    status=row.get("status"),
                    score=_format_float(row.get("score")),
                    raw_value=row.get("raw_value"),
                    target=row.get("target"),
                    gap_to_target=row.get("gap_to_target"),
                    next_research_action=row.get("next_research_action"),
                )
            )
        lines.append("")

    lines.extend(
        [
            "## Next mandatory gates before any future operational layer",
            "",
        ]
    )
    for gate in report.get("next_required_gates", []):
        lines.append(f"- `{gate}`")
    lines.append("")
    return "\n".join(lines)


def _badge(status: Any) -> str:
    status_text = html.escape(str(status))
    return f'<span class="badge badge-{status_text.lower()}">{status_text}</span>'


def _html_table(rows: Iterable[dict[str, Any]]) -> str:
    body = []
    for row in rows:
        body.append(
            "<tr>"
            f"<td>{html.escape(str(row.get('dimension')))}</td>"
            f"<td>{_badge(row.get('status'))}</td>"
            f"<td>{html.escape(_format_float(row.get('score')))}</td>"
            f"<td>{html.escape(str(row.get('raw_value')))}</td>"
            f"<td>{html.escape(str(row.get('target')))}</td>"
            f"<td>{html.escape(str(row.get('gap_to_target')))}</td>"
            f"<td>{html.escape(str(row.get('next_research_action')))}</td>"
            "</tr>"
        )
    return "".join(body)


def render_evidence_drilldown_html(report: dict[str, Any]) -> str:
    cards = []
    for item in report.get("drilldowns", []):
        cards.append(
            f"""
            <section class="card asset-card" data-status="{html.escape(str(item.get('coverage_status')))}">
              <div class="card-head">
                <h2>{html.escape(str(item.get('symbol')))}</h2>
                {_badge(item.get('coverage_status'))}
              </div>
              <p><strong>Coverage answer:</strong> <code>{html.escape(str(item.get('coverage_answer')))}</code></p>
              <p><strong>Research readiness:</strong> <code>{html.escape(str(item.get('research_readiness')))}</code> · score {_format_float(item.get('research_readiness_score'))}</p>
              <p><strong>Fail dimensions:</strong> <code>{html.escape(json.dumps(item.get('fail_dimensions', []), sort_keys=True))}</code></p>
              <p><strong>Watch dimensions:</strong> <code>{html.escape(json.dumps(item.get('watch_dimensions', []), sort_keys=True))}</code></p>
              <table>
                <thead>
                  <tr>
                    <th>Dimension</th><th>Status</th><th>Score</th><th>Raw</th><th>Target</th><th>Gap</th><th>Next research action</th>
                  </tr>
                </thead>
                <tbody>{_html_table(item.get('dimension_rows', []))}</tbody>
              </table>
            </section>
            """
        )

    weakest = "".join(
        f"<li><strong>{html.escape(str(item.get('dimension')))}</strong>: FAIL={item.get('fail_count')}, WATCH={item.get('watch_count')}, PASS={item.get('pass_count')}</li>"
        for item in report.get("weakest_dimensions", [])
    )
    gates = "".join(f"<li><code>{html.escape(str(gate))}</code></li>" for gate in report.get("next_required_gates", []))

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>QRDS Evidence Drilldown</title>
  <style>
    :root {{ color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    body {{ margin: 0; background: #0f172a; color: #e5e7eb; }}
    header {{ padding: 28px 32px; background: linear-gradient(135deg, #111827, #1e293b); border-bottom: 1px solid #334155; }}
    main {{ padding: 24px 32px 48px; max-width: 1280px; margin: 0 auto; }}
    h1 {{ margin: 0 0 8px; font-size: 2rem; }}
    h2 {{ margin: 0; }}
    code {{ color: #bfdbfe; }}
    .subtitle {{ color: #cbd5e1; max-width: 900px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin: 20px 0; }}
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
    <h1>QRDS Evidence Drilldown / Data Coverage Gate v1</h1>
    <p class="subtitle">Research-only diagnostic layer. It explains evidence gaps after the Evidence Quality Gate. It does not create operational decisions, executable signals, recommendations, allocations, orders, or real-capital actions.</p>
    <p><strong>Gate answer:</strong> <code>{html.escape(str(report.get('gate_answer')))}</code></p>
  </header>
  <main>
    <section class="grid">
      <div class="card"><strong>Assets</strong><br><span>{report.get('asset_count')}</span></div>
      <div class="card"><strong>Mean readiness</strong><br><span>{_format_float(report.get('mean_research_readiness_score'))}</span></div>
      <div class="card"><strong>Status counts</strong><br><code>{html.escape(json.dumps(report.get('coverage_status_counts', {}), sort_keys=True))}</code></div>
      <div class="card"><strong>Scope</strong><br><code>{html.escape(str(report.get('decision_scope')))}</code></div>
    </section>

    <section class="card">
      <h2>Weakest dimensions</h2>
      <ul>{weakest}</ul>
    </section>

    <p class="note">Interpretation: PASS means only that the research artifact can continue through formal research gates. WATCH means partial evidence. FAIL means the dimension should block progression to later gates.</p>

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


def build_fixture_evidence_quality_report(symbols: list[str]) -> dict[str, Any]:
    """Build deterministic 8L-compatible evidence report for offline use/tests."""
    try:
        multi_asset, stress = build_fixture_upstream_inputs(symbols)
        return build_evidence_quality_gate(multi_asset, stress)
    except EvidenceQualityError as exc:  # pragma: no cover - defensive wrap
        raise EvidenceDrilldownError(str(exc)) from exc


def write_evidence_drilldown(
    evidence_report: dict[str, Any],
    output_dir: str | Path,
    *,
    report_name: str = "qrds-evidence-drilldown-gate",
    min_dataset_rows: int | None = None,
    min_walk_forward_splits: int | None = None,
    min_stress_retention_ratio: float = 0.50,
    min_research_readiness_score: float = 0.50,
) -> dict[str, Any]:
    """Write JSON, Markdown, HTML and index artifacts for the drilldown gate."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    report = build_evidence_drilldown(
        evidence_report,
        report_name=report_name,
        min_dataset_rows=min_dataset_rows,
        min_walk_forward_splits=min_walk_forward_splits,
        min_stress_retention_ratio=min_stress_retention_ratio,
        min_research_readiness_score=min_research_readiness_score,
    )
    report["report_payload_sha256"] = _payload_sha256(report)
    report_path = root / "evidence_drilldown_gate.json"
    markdown_path = root / "evidence_drilldown_gate.md"
    html_path = root / "index.html"
    index_path = root / "evidence_drilldown_index.json"

    _write_json(report_path, report)
    _write_text(markdown_path, render_evidence_drilldown_markdown(report))
    _write_text(html_path, render_evidence_drilldown_html(report))

    index = {
        "schema": EVIDENCE_DRILLDOWN_INDEX_SCHEMA_VERSION,
        "generated_at": report["generated_at"],
        "report_name": report["report_name"],
        "gate_answer": report["gate_answer"],
        "asset_count": report["asset_count"],
        "symbols": report["symbols"],
        "mean_research_readiness_score": report["mean_research_readiness_score"],
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


def load_evidence_report_payload(path: str | Path) -> dict[str, Any]:
    """Load an 8L Evidence Quality Gate report or index JSON."""
    payload = _read_json(path)
    if payload.get("schema") == EVIDENCE_DRILLDOWN_INDEX_SCHEMA_VERSION:
        raise EvidenceDrilldownError("Expected an Evidence Quality report/index, not a Drilldown index.")
    if payload.get("schema") == "qrds.evidence_quality_index.v1":
        for key in ("report_path", "evidence_quality_gate_path"):
            target = payload.get(key)
            if target:
                candidate = Path(path).parent / str(target)
                if candidate.exists():
                    return _read_json(candidate)
                return _read_json(target)
        raise EvidenceDrilldownError("Evidence Quality index does not include report_path.")
    if "evaluations" in payload:
        return payload
    raise EvidenceDrilldownError("Unsupported evidence report payload; expected 8L report or index.")


def parse_symbols(value: str) -> list[str]:
    symbols = [part.strip() for part in value.split(",") if part.strip()]
    if not symbols:
        raise EvidenceDrilldownError("At least one symbol is required.")
    return symbols
