"""Scenario Stress Pack for QRDS multi-asset research.

Offline/research-only.
No API key.
No account connection.
No authenticated exchange access.
No orders.
No real capital.
No operational decisions.

This module applies descriptive stress scenarios to multi-asset research
summaries. It does not generate allocations, signals, orders, recommendations
or portfolio decisions.
"""

from __future__ import annotations

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
from crypto_decision_lab.reports.export import compute_file_sha256
from crypto_decision_lab.reports.multi_asset import load_multi_asset_report

SCENARIO_STRESS_SCENARIO_SCHEMA_VERSION = "qrds.scenario_stress_scenario.v1"
SCENARIO_STRESS_RESULT_SCHEMA_VERSION = "qrds.scenario_stress_result.v1"
SCENARIO_STRESS_PACK_SCHEMA_VERSION = "qrds.scenario_stress_pack.v1"
SCENARIO_STRESS_PACK_INDEX_SCHEMA_VERSION = "qrds.scenario_stress_pack_index.v1"

EDGE_STATUS_ORDER = {
    "NO_EVIDENCE": 0,
    "INCONCLUSIVE": 1,
    "WEAK_EVIDENCE": 2,
    "PROMISING_RESEARCH_ONLY": 3,
}

EDGE_STATUS_BY_ORDER = {
    value: key
    for key, value in EDGE_STATUS_ORDER.items()
}


class ScenarioStressPackError(ValueError):
    """Raised when scenario stress pack cannot be built safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _payload_sha256(payload: Any) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(data.encode("utf-8")).hexdigest()


def _read_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise ScenarioStressPackError(f"JSON artifact not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise ScenarioStressPackError(f"JSON artifact must contain an object: {file_path}")

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


def _assert_research_payload(payload: dict[str, Any], *, name: str) -> None:
    issues = collect_research_contract_issues(
        payload,
        name=name,
        require_schema=False,
        require_app_mode=False,
        require_research_allowed=False,
    )
    errors = [issue for issue in issues if issue["severity"] == "error"]
    if errors:
        raise ScenarioStressPackError(f"{name} violates research-only contract: {errors}")


def _to_float(value: Any, *, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number


def build_default_stress_scenarios() -> list[dict[str, Any]]:
    """Build default descriptive stress scenarios."""
    stamp = build_research_safety_stamp()

    scenarios = [
        {
            "scenario_id": "base_observed",
            "name": "Base observed research state",
            "description": "No additional stress applied.",
            "score_multiplier": 1.0,
            "score_penalty": 0.0,
            "edge_status_downgrade_steps": 0,
            "dataset_row_penalty_threshold": 0,
            "dataset_row_penalty": 0.0,
        },
        {
            "scenario_id": "cost_slippage_pressure",
            "name": "Cost/slippage pressure",
            "description": "Applies a mild score haircut to represent conservative cost/slippage pressure.",
            "score_multiplier": 0.80,
            "score_penalty": 0.25,
            "edge_status_downgrade_steps": 1,
            "dataset_row_penalty_threshold": 0,
            "dataset_row_penalty": 0.0,
        },
        {
            "scenario_id": "data_scarcity_penalty",
            "name": "Data scarcity penalty",
            "description": "Penalizes assets with very short research datasets.",
            "score_multiplier": 0.90,
            "score_penalty": 0.0,
            "edge_status_downgrade_steps": 0,
            "dataset_row_penalty_threshold": 20,
            "dataset_row_penalty": 0.75,
        },
        {
            "scenario_id": "combined_research_stress",
            "name": "Combined research stress",
            "description": "Combines score haircut, status downgrade and data scarcity penalty.",
            "score_multiplier": 0.65,
            "score_penalty": 0.50,
            "edge_status_downgrade_steps": 1,
            "dataset_row_penalty_threshold": 20,
            "dataset_row_penalty": 0.75,
        },
    ]

    return [
        {
            "schema": SCENARIO_STRESS_SCENARIO_SCHEMA_VERSION,
            "generated_at": _utc_now(),
            "allocation_generated": False,
            "portfolio_decision_generated": False,
            "hypothetical_only": True,
            **scenario,
            **stamp,
        }
        for scenario in scenarios
    ]


def validate_stress_scenario(scenario: dict[str, Any]) -> list[dict[str, Any]]:
    """Return quality issues for one stress scenario."""
    issues = collect_research_contract_issues(
        scenario,
        name="stress_scenario",
        require_schema=True,
        require_app_mode=True,
        require_research_allowed=True,
    )

    if scenario.get("schema") != SCENARIO_STRESS_SCENARIO_SCHEMA_VERSION:
        issues.append(
            {
                "code": "INVALID_STRESS_SCENARIO_SCHEMA",
                "severity": "error",
                "name": "stress_scenario",
                "message": "Invalid scenario stress schema.",
            }
        )

    if _to_float(scenario.get("score_multiplier"), default=-1.0) < 0:
        issues.append(
            {
                "code": "INVALID_STRESS_SCORE_MULTIPLIER",
                "severity": "error",
                "name": "stress_scenario",
                "message": "score_multiplier cannot be negative.",
            }
        )

    if _to_float(scenario.get("score_penalty"), default=-1.0) < 0:
        issues.append(
            {
                "code": "INVALID_STRESS_SCORE_PENALTY",
                "severity": "error",
                "name": "stress_scenario",
                "message": "score_penalty cannot be negative.",
            }
        )

    for flag in ("allocation_generated", "portfolio_decision_generated"):
        if scenario.get(flag) is True:
            issues.append(
                {
                    "code": "UNSAFE_STRESS_DECISION_FLAG",
                    "severity": "error",
                    "name": "stress_scenario",
                    "message": f"{flag} must remain False.",
                }
            )

    return issues


def _downgrade_status(status: str, steps: int) -> str:
    order = EDGE_STATUS_ORDER.get(status, 0)
    downgraded = max(0, order - max(0, int(steps)))
    return EDGE_STATUS_BY_ORDER[downgraded]


def apply_stress_scenario_to_entry(
    entry: dict[str, Any],
    scenario: dict[str, Any],
) -> dict[str, Any]:
    """Apply one descriptive stress scenario to one asset entry."""
    _assert_research_payload(entry, name="multi_asset_entry")
    scenario_issues = validate_stress_scenario(scenario)
    if any(issue["severity"] == "error" for issue in scenario_issues):
        raise ScenarioStressPackError(f"Invalid stress scenario: {scenario_issues}")

    original_score = _to_float(entry.get("edge_score"), default=0.0)
    dataset_rows = int(_to_float(entry.get("dataset_row_count"), default=0.0))
    threshold = int(_to_float(scenario.get("dataset_row_penalty_threshold"), default=0.0))
    dataset_penalty = _to_float(scenario.get("dataset_row_penalty"), default=0.0) if threshold and dataset_rows < threshold else 0.0

    stressed_score = max(
        0.0,
        original_score * _to_float(scenario.get("score_multiplier"), default=1.0)
        - _to_float(scenario.get("score_penalty"), default=0.0)
        - dataset_penalty,
    )

    original_status = str(entry.get("edge_status"))
    stressed_status = _downgrade_status(
        original_status,
        int(_to_float(scenario.get("edge_status_downgrade_steps"), default=0.0)),
    )

    if stressed_score <= 0:
        stressed_status = "NO_EVIDENCE"

    return {
        "schema": SCENARIO_STRESS_RESULT_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "scenario_id": scenario.get("scenario_id"),
        "scenario_name": scenario.get("name"),
        "symbol": entry.get("symbol"),
        "original_edge_status": original_status,
        "stressed_edge_status": stressed_status,
        "original_edge_score": original_score,
        "stressed_edge_score": stressed_score,
        "score_delta": stressed_score - original_score,
        "dataset_row_count": dataset_rows,
        "dataset_row_penalty_applied": dataset_penalty,
        "pack_index_path": entry.get("pack_index_path"),
        "allocation_generated": False,
        "portfolio_decision_generated": False,
        "hypothetical_only": True,
        **build_research_safety_stamp(),
    }


def build_scenario_stress_pack(
    multi_asset_report: dict[str, Any],
    *,
    scenarios: list[dict[str, Any]] | None = None,
    pack_name: str = "qrds-scenario-stress-pack",
) -> dict[str, Any]:
    """Build scenario stress pack from a multi-asset report."""
    _assert_research_payload(multi_asset_report, name="multi_asset_report")

    entries = multi_asset_report.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ScenarioStressPackError("multi_asset_report must include entries.")

    selected_scenarios = scenarios if scenarios is not None else build_default_stress_scenarios()
    if not selected_scenarios:
        raise ScenarioStressPackError("At least one stress scenario is required.")

    scenario_results: list[dict[str, Any]] = []
    for scenario in selected_scenarios:
        for entry in entries:
            scenario_results.append(apply_stress_scenario_to_entry(entry, scenario))

    by_scenario: list[dict[str, Any]] = []
    for scenario in selected_scenarios:
        results = [
            result
            for result in scenario_results
            if result["scenario_id"] == scenario["scenario_id"]
        ]
        scores = [result["stressed_edge_score"] for result in results]
        status_counts: dict[str, int] = {}
        for result in results:
            status = result["stressed_edge_status"]
            status_counts[status] = status_counts.get(status, 0) + 1

        by_scenario.append(
            {
                "scenario_id": scenario["scenario_id"],
                "scenario_name": scenario["name"],
                "asset_count": len(results),
                "mean_stressed_edge_score": mean(scores) if scores else None,
                "min_stressed_edge_score": min(scores) if scores else None,
                "max_stressed_edge_score": max(scores) if scores else None,
                "stressed_status_counts": status_counts,
            }
        )

    worst_case_by_symbol: list[dict[str, Any]] = []
    for entry in entries:
        symbol = entry.get("symbol")
        results = [result for result in scenario_results if result["symbol"] == symbol]
        worst = sorted(
            results,
            key=lambda result: (
                EDGE_STATUS_ORDER.get(result["stressed_edge_status"], 0),
                result["stressed_edge_score"],
            ),
        )[0]
        worst_case_by_symbol.append(
            {
                "symbol": symbol,
                "worst_scenario_id": worst["scenario_id"],
                "worst_stressed_edge_status": worst["stressed_edge_status"],
                "worst_stressed_edge_score": worst["stressed_edge_score"],
                "original_edge_status": worst["original_edge_status"],
                "original_edge_score": worst["original_edge_score"],
            }
        )

    return {
        "schema": SCENARIO_STRESS_PACK_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "pack_name": pack_name,
        "source_multi_asset_schema": multi_asset_report.get("schema"),
        "asset_count": len(entries),
        "scenario_count": len(selected_scenarios),
        "result_count": len(scenario_results),
        "symbols": [entry.get("symbol") for entry in entries],
        "scenarios": selected_scenarios,
        "scenario_summaries": by_scenario,
        "worst_case_by_symbol": worst_case_by_symbol,
        "results": scenario_results,
        "caveats": [
            "Scenario stress is descriptive research only.",
            "Stress rankings are not allocation instructions.",
            "No orders, signals, recommendations or operational decisions are produced.",
            "Scenario parameters are simple heuristics and not calibrated execution models.",
        ],
        "allocation_generated": False,
        "portfolio_decision_generated": False,
        "hypothetical_only": True,
        **build_research_safety_stamp(),
    }


def validate_scenario_stress_pack(pack: dict[str, Any]) -> list[dict[str, Any]]:
    """Return quality issues for scenario stress pack."""
    issues = collect_research_contract_issues(
        pack,
        name="scenario_stress_pack",
        require_schema=True,
        require_app_mode=True,
        require_research_allowed=True,
    )

    if pack.get("schema") != SCENARIO_STRESS_PACK_SCHEMA_VERSION:
        issues.append(
            {
                "code": "INVALID_SCENARIO_STRESS_PACK_SCHEMA",
                "severity": "error",
                "name": "scenario_stress_pack",
                "message": "Invalid scenario stress pack schema.",
            }
        )

    if int(pack.get("asset_count", 0) or 0) <= 0:
        issues.append(
            {
                "code": "EMPTY_SCENARIO_STRESS_ASSET_SET",
                "severity": "error",
                "name": "scenario_stress_pack",
                "message": "Scenario stress pack must include assets.",
            }
        )

    if int(pack.get("scenario_count", 0) or 0) <= 0:
        issues.append(
            {
                "code": "EMPTY_SCENARIO_STRESS_SCENARIO_SET",
                "severity": "error",
                "name": "scenario_stress_pack",
                "message": "Scenario stress pack must include scenarios.",
            }
        )

    for flag in ("allocation_generated", "portfolio_decision_generated"):
        if pack.get(flag) is True:
            issues.append(
                {
                    "code": "UNSAFE_STRESS_PACK_DECISION_FLAG",
                    "severity": "error",
                    "name": "scenario_stress_pack",
                    "message": f"{flag} must remain False.",
                }
            )

    return issues


def render_scenario_stress_markdown(pack: dict[str, Any]) -> str:
    """Render stress pack markdown."""
    lines = [
        "# QRDS Scenario Stress Pack",
        "",
        "## Status",
        "",
        f"- Pack name: `{pack.get('pack_name')}`",
        f"- Mode: `{pack.get('app_mode')}`",
        f"- Asset count: `{pack.get('asset_count')}`",
        f"- Scenario count: `{pack.get('scenario_count')}`",
        f"- Symbols: `{', '.join(str(symbol) for symbol in pack.get('symbols', []))}`",
        "",
        "## Scenario summaries",
        "",
        "| Scenario | Mean stressed score | Min | Max | Status counts |",
        "|---|---:|---:|---:|---|",
    ]

    for summary in pack.get("scenario_summaries", []):
        lines.append(
            f"| `{summary.get('scenario_id')}` | `{summary.get('mean_stressed_edge_score')}` | "
            f"`{summary.get('min_stressed_edge_score')}` | `{summary.get('max_stressed_edge_score')}` | "
            f"`{summary.get('stressed_status_counts')}` |"
        )

    lines.extend(
        [
            "",
            "## Worst case by symbol",
            "",
            "| Symbol | Worst scenario | Original status | Stressed status | Stressed score |",
            "|---|---|---|---|---:|",
        ]
    )

    for item in pack.get("worst_case_by_symbol", []):
        lines.append(
            f"| `{item.get('symbol')}` | `{item.get('worst_scenario_id')}` | "
            f"`{item.get('original_edge_status')}` | `{item.get('worst_stressed_edge_status')}` | "
            f"`{item.get('worst_stressed_edge_score')}` |"
        )

    lines.extend(["", "## Caveats", ""])
    for caveat in pack.get("caveats", []):
        lines.append(f"- {caveat}")

    lines.extend(
        [
            "",
            "## Safety",
            "",
            "```text",
            "allocation_generated = False",
            "portfolio_decision_generated = False",
            "operational_decision_allowed = False",
            "orders_generated = False",
            "real_capital_used = False",
            "trading_signal_generated = False",
            "executable_signal_generated = False",
            "recommendation_generated = False",
            "```",
            "",
        ]
    )

    return "\n".join(lines)


def write_scenario_stress_pack(
    *,
    multi_asset_index_path: str | Path,
    output_dir: str | Path,
    pack_name: str = "qrds-scenario-stress-pack",
) -> dict[str, Any]:
    """Write scenario stress pack artifacts from a multi-asset report index."""
    loaded = load_multi_asset_report(multi_asset_index_path)
    multi_asset_report = loaded["report"]
    pack = build_scenario_stress_pack(multi_asset_report, pack_name=pack_name)

    issues = validate_scenario_stress_pack(pack)
    if any(issue["severity"] == "error" for issue in issues):
        raise ScenarioStressPackError(f"Scenario stress pack validation errors: {issues}")

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    pack_path = root / "scenario_stress_pack.json"
    markdown_path = root / "scenario_stress_report.md"
    results_path = root / "scenario_stress_results.json"
    index_path = root / "scenario_stress_index.json"

    _write_json(pack_path, pack)
    _write_text(markdown_path, render_scenario_stress_markdown(pack))
    _write_json(
        results_path,
        {
            "schema": "qrds.scenario_stress_results.v1",
            "results": pack["results"],
            **build_research_safety_stamp(),
        },
    )

    index = {
        "schema": SCENARIO_STRESS_PACK_INDEX_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "pack_name": pack_name,
        "source_multi_asset_index_path": str(multi_asset_index_path),
        "pack_path": str(pack_path),
        "markdown_path": str(markdown_path),
        "results_path": str(results_path),
        "pack_file_sha256": compute_file_sha256(pack_path),
        "markdown_file_sha256": compute_file_sha256(markdown_path),
        "results_file_sha256": compute_file_sha256(results_path),
        "asset_count": pack["asset_count"],
        "scenario_count": pack["scenario_count"],
        "result_count": pack["result_count"],
        "symbols": pack["symbols"],
        "pack_payload_sha256": _payload_sha256(pack),
        "allocation_generated": False,
        "portfolio_decision_generated": False,
        **build_research_safety_stamp(),
    }
    _write_json(index_path, index)

    index["index_path"] = str(index_path)
    _write_json(index_path, index)

    return index


def load_scenario_stress_pack(index_path: str | Path) -> dict[str, Any]:
    """Load scenario stress pack from index."""
    index = _read_json(index_path)
    if index.get("schema") != SCENARIO_STRESS_PACK_INDEX_SCHEMA_VERSION:
        raise ScenarioStressPackError("Invalid scenario stress pack index schema.")

    pack = _read_json(index["pack_path"])
    results = _read_json(index["results_path"])
    markdown = Path(index["markdown_path"]).read_text(encoding="utf-8")

    issues = validate_scenario_stress_pack(pack)
    if any(issue["severity"] == "error" for issue in issues):
        raise ScenarioStressPackError(f"Loaded scenario stress pack validation errors: {issues}")

    return {
        "index": index,
        "pack": pack,
        "results": results,
        "markdown": markdown,
        **build_research_safety_stamp(),
    }
