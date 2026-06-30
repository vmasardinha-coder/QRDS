"""Research Report Pack v1 for QRDS.

Offline/research-only.
No API key.
No account connection.
No authenticated exchange access.
No orders.
No real capital.
No operational decisions.

This module turns already-generated research artifacts into a human-readable
markdown report pack plus a machine-readable index.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from crypto_decision_lab.contracts.research import (
    build_research_safety_stamp,
    collect_research_contract_issues,
)
from crypto_decision_lab.reports.export import compute_file_sha256

RESEARCH_REPORT_PACK_SCHEMA_VERSION = "qrds.research_report_pack.v1"
RESEARCH_REPORT_PACK_INDEX_SCHEMA_VERSION = "qrds.research_report_pack_index.v1"


class ResearchReportPackError(ValueError):
    """Raised when research report pack cannot be built safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise ResearchReportPackError(f"JSON artifact not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise ResearchReportPackError(f"JSON artifact must contain object: {file_path}")

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


def _payload_sha256(payload: Any) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(data.encode("utf-8")).hexdigest()


def _artifact_safe(payload: dict[str, Any], *, name: str) -> None:
    issues = collect_research_contract_issues(
        payload,
        name=name,
        require_schema=False,
        require_app_mode=False,
        require_research_allowed=False,
    )
    errors = [issue for issue in issues if issue["severity"] == "error"]
    if errors:
        raise ResearchReportPackError(f"{name} violates research-only contract: {errors}")


def load_full_research_artifacts(root_dir: str | Path) -> dict[str, dict[str, Any]]:
    """Load artifacts produced by full_research CLI."""
    root = Path(root_dir)

    summary = _read_json(root / "full_research_summary.json")
    health = _read_json(root / "integration_health_report.json")
    registry = _read_json(root / "contract_freeze_registry.json")
    edge_console_summary = _read_json(root / "edge_console_summary.json")

    edge_export_index_path = summary.get("edge_export_index_path")
    if not edge_export_index_path:
        raise ResearchReportPackError("full_research_summary missing edge_export_index_path.")

    edge_export_index = _read_json(edge_export_index_path)
    edge_report = _read_json(edge_export_index["report_path"])
    edge_summary = _read_json(edge_export_index["summary_path"])

    artifacts = {
        "full_research_summary": summary,
        "integration_health_report": health,
        "contract_freeze_registry": registry,
        "edge_console_summary": edge_console_summary,
        "edge_export_index": edge_export_index,
        "edge_report": edge_report,
        "edge_summary": edge_summary,
    }

    for name, payload in artifacts.items():
        _artifact_safe(payload, name=name)

    return artifacts


def build_research_report_pack(
    artifacts: dict[str, dict[str, Any]],
    *,
    pack_name: str = "qrds-research-report-pack",
) -> dict[str, Any]:
    """Build a compact machine-readable report pack payload."""
    summary = artifacts["full_research_summary"]
    edge_report = artifacts["edge_report"]
    health = artifacts["integration_health_report"]
    registry = artifacts["contract_freeze_registry"]

    pack = {
        "schema": RESEARCH_REPORT_PACK_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "pack_name": pack_name,
        "project": "QRDS / QOS",
        "mode": "INTERACTIVE_RESEARCH_ONLY",
        "source_summary_schema": summary.get("schema"),
        "edge_report_schema": edge_report.get("schema"),
        "contract_registry_schema": registry.get("schema"),
        "run_id": summary.get("run_id"),
        "report_id": summary.get("report_id"),
        "symbol": summary.get("symbol"),
        "interval": summary.get("interval"),
        "source": summary.get("source"),
        "horizons": summary.get("horizons"),
        "dataset_row_count": summary.get("dataset_row_count"),
        "split_count": summary.get("split_count"),
        "return_column": summary.get("return_column"),
        "edge_status": summary.get("edge_status"),
        "edge_score": summary.get("edge_score"),
        "integration_health_passed": health.get("integration_health_passed"),
        "artifact_schemas": {
            name: payload.get("schema")
            for name, payload in sorted(artifacts.items())
        },
        "artifact_payload_hashes": {
            name: _payload_sha256(payload)
            for name, payload in sorted(artifacts.items())
        },
        "caveats": [
            "Research-only pack; not a trading recommendation.",
            "No orders, no executable signals and no real capital.",
            "Current replay remains fixture/offline-based unless explicitly expanded later.",
            "Costs, slippage, benchmark and execution assumptions must be read as research artifacts only.",
        ],
        **build_research_safety_stamp(),
    }

    return pack


def render_research_report_markdown(pack: dict[str, Any], artifacts: dict[str, dict[str, Any]]) -> str:
    """Render a human-readable markdown report."""
    edge_report = artifacts["edge_report"]
    edge_score = edge_report.get("edge_score", {})
    backtest_summary = edge_report.get("backtest_summary", {})
    baseline_summary = edge_report.get("baseline_summary") or {}
    health = artifacts["integration_health_report"]
    summary = artifacts["full_research_summary"]

    lines = [
        "# QRDS Research Report Pack v1",
        "",
        "## Status",
        "",
        f"- Project: `{pack.get('project')}`",
        f"- Mode: `{pack.get('mode')}`",
        f"- Run ID: `{pack.get('run_id')}`",
        f"- Symbol: `{pack.get('symbol')}`",
        f"- Interval: `{pack.get('interval')}`",
        f"- Edge status: `{pack.get('edge_status')}`",
        f"- Edge score: `{pack.get('edge_score')}`",
        f"- Integration health passed: `{pack.get('integration_health_passed')}`",
        "",
        "## Research chain",
        "",
        "```text",
        "OKX/local fixture",
        "↓",
        "public adapter/cache",
        "↓",
        "research pipeline",
        "↓",
        "walk-forward",
        "↓",
        "baseline/backtest skeleton",
        "↓",
        "edge report export",
        "↓",
        "report pack",
        "```",
        "",
        "## Dataset",
        "",
        f"- Dataset rows: `{pack.get('dataset_row_count')}`",
        f"- Splits: `{pack.get('split_count')}`",
        f"- Return column: `{pack.get('return_column')}`",
        f"- Horizons: `{pack.get('horizons')}`",
        "",
        "## Edge summary",
        "",
        f"- Edge status: `{edge_report.get('edge_status')}`",
        f"- Score: `{edge_score.get('score')}` / `{edge_score.get('max_score')}`",
        f"- Mean hypothetical total return: `{backtest_summary.get('mean_total_return')}`",
        f"- Worst max drawdown: `{backtest_summary.get('worst_max_drawdown')}`",
        f"- Active hypothetical events: `{backtest_summary.get('total_active_events')}`",
        "",
        "## Baseline summary",
        "",
        f"- Mean MAE: `{baseline_summary.get('mean_mae')}`",
        f"- Mean RMSE: `{baseline_summary.get('mean_rmse')}`",
        f"- Mean accuracy: `{baseline_summary.get('mean_accuracy')}`",
        "",
        "## Integration health",
        "",
        f"- Passed: `{health.get('integration_health_passed')}`",
        f"- Artifact count: `{health.get('artifact_count')}`",
        f"- Error count: `{health.get('issue_summary', {}).get('error_count')}`",
        "",
        "## Artifact paths",
        "",
        f"- Pipeline JSONL: `{summary.get('pipeline_jsonl_path')}`",
        f"- Edge report: `{summary.get('edge_report_path')}`",
        f"- Edge summary: `{summary.get('edge_summary_path')}`",
        f"- Edge export index: `{summary.get('edge_export_index_path')}`",
        "",
        "## Caveats",
        "",
    ]

    for caveat in pack.get("caveats", []):
        lines.append(f"- {caveat}")

    lines.extend(
        [
            "",
            "## Safety",
            "",
            "```text",
            "operational_decision_allowed = False",
            "api_key_required = False",
            "api_key_present = False",
            "account_connection_required = False",
            "orders_generated = False",
            "real_capital_used = False",
            "orders_allowed = False",
            "trading_signal_generated = False",
            "executable_signal_generated = False",
            "recommendation_generated = False",
            "```",
            "",
        ]
    )

    return "\n".join(lines)


def validate_research_report_pack(pack: dict[str, Any]) -> list[dict[str, Any]]:
    """Return quality issues for the report pack payload."""
    issues = collect_research_contract_issues(
        pack,
        name="research_report_pack",
        require_schema=True,
        require_app_mode=True,
        require_research_allowed=True,
    )

    if pack.get("schema") != RESEARCH_REPORT_PACK_SCHEMA_VERSION:
        issues.append(
            {
                "code": "INVALID_RESEARCH_REPORT_PACK_SCHEMA",
                "severity": "error",
                "name": "research_report_pack",
                "message": "Invalid research report pack schema.",
            }
        )

    if not pack.get("edge_status"):
        issues.append(
            {
                "code": "MISSING_RESEARCH_REPORT_PACK_EDGE_STATUS",
                "severity": "error",
                "name": "research_report_pack",
                "message": "Research report pack missing edge_status.",
            }
        )

    if pack.get("integration_health_passed") is not True:
        issues.append(
            {
                "code": "RESEARCH_REPORT_PACK_HEALTH_NOT_PASSED",
                "severity": "error",
                "name": "research_report_pack",
                "message": "Research report pack integration health did not pass.",
            }
        )

    return issues


def write_research_report_pack(
    *,
    full_research_dir: str | Path,
    output_dir: str | Path,
    pack_name: str = "qrds-research-report-pack",
) -> dict[str, Any]:
    """Write report pack JSON, markdown and index."""
    artifacts = load_full_research_artifacts(full_research_dir)
    pack = build_research_report_pack(artifacts, pack_name=pack_name)
    issues = validate_research_report_pack(pack)
    if any(issue["severity"] == "error" for issue in issues):
        raise ResearchReportPackError(f"Research report pack validation errors: {issues}")

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    pack_path = root / "research_report_pack.json"
    markdown_path = root / "research_report.md"
    artifact_map_path = root / "artifact_map.json"
    index_path = root / "research_report_pack_index.json"

    artifact_map = {
        "schema": "qrds.research_report_artifact_map.v1",
        "generated_at": _utc_now(),
        "full_research_dir": str(full_research_dir),
        "artifacts": {
            name: {
                "schema": payload.get("schema"),
                "payload_sha256": _payload_sha256(payload),
            }
            for name, payload in sorted(artifacts.items())
        },
        **build_research_safety_stamp(),
    }

    _write_json(pack_path, pack)
    _write_text(markdown_path, render_research_report_markdown(pack, artifacts))
    _write_json(artifact_map_path, artifact_map)

    index = {
        "schema": RESEARCH_REPORT_PACK_INDEX_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "pack_name": pack_name,
        "pack_path": str(pack_path),
        "markdown_path": str(markdown_path),
        "artifact_map_path": str(artifact_map_path),
        "pack_file_sha256": compute_file_sha256(pack_path),
        "markdown_file_sha256": compute_file_sha256(markdown_path),
        "artifact_map_file_sha256": compute_file_sha256(artifact_map_path),
        "edge_status": pack.get("edge_status"),
        "integration_health_passed": pack.get("integration_health_passed"),
        **build_research_safety_stamp(),
    }
    _write_json(index_path, index)

    index["index_path"] = str(index_path)
    _write_json(index_path, index)

    return index


def load_research_report_pack(index_path: str | Path) -> dict[str, Any]:
    """Load a written report pack from its index."""
    index = _read_json(index_path)

    if index.get("schema") != RESEARCH_REPORT_PACK_INDEX_SCHEMA_VERSION:
        raise ResearchReportPackError("Invalid research report pack index schema.")

    for key in ("pack_path", "artifact_map_path"):
        path = Path(index[key])
        if not path.exists():
            raise ResearchReportPackError(f"Report pack file missing: {path}")

    markdown = Path(index["markdown_path"])
    if not markdown.exists():
        raise ResearchReportPackError(f"Report markdown missing: {markdown}")

    pack = _read_json(index["pack_path"])
    artifact_map = _read_json(index["artifact_map_path"])
    markdown_text = markdown.read_text(encoding="utf-8")

    return {
        "index": index,
        "pack": pack,
        "artifact_map": artifact_map,
        "markdown": markdown_text,
        **build_research_safety_stamp(),
    }
