"""Multi-Asset Report Aggregator for QRDS.

Offline/research-only.
No API key.
No account connection.
No authenticated exchange access.
No orders.
No real capital.
No operational decisions.

This module aggregates multiple symbol-level research report packs into a
research-only multi-asset overview. It does not generate allocation, signals,
orders, recommendations or portfolio decisions.
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
from crypto_decision_lab.reports.pack import (
    load_research_report_pack,
)

MULTI_ASSET_REPORT_SCHEMA_VERSION = "qrds.multi_asset_report.v1"
MULTI_ASSET_REPORT_INDEX_SCHEMA_VERSION = "qrds.multi_asset_report_index.v1"

EDGE_STATUS_ORDER = {
    "NO_EVIDENCE": 0,
    "INCONCLUSIVE": 1,
    "WEAK_EVIDENCE": 2,
    "PROMISING_RESEARCH_ONLY": 3,
}


class MultiAssetReportError(ValueError):
    """Raised when multi-asset report aggregation cannot complete safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _payload_sha256(payload: Any) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(data.encode("utf-8")).hexdigest()


def _read_json(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise MultiAssetReportError(f"JSON artifact not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise MultiAssetReportError(f"JSON artifact must contain an object: {file_path}")

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
        raise MultiAssetReportError(f"{name} violates research-only contract: {errors}")


def _score_value(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def load_report_pack_entries(index_paths: Iterable[str | Path]) -> list[dict[str, Any]]:
    """Load symbol-level report packs from index paths."""
    entries: list[dict[str, Any]] = []

    for i, index_path in enumerate(index_paths):
        loaded = load_research_report_pack(index_path)
        pack = loaded["pack"]
        index = loaded["index"]
        artifact_map = loaded["artifact_map"]

        for name, payload in (
            (f"loaded_pack[{i}].pack", pack),
            (f"loaded_pack[{i}].index", index),
            (f"loaded_pack[{i}].artifact_map", artifact_map),
        ):
            _assert_research_payload(payload, name=name)

        symbol = str(pack.get("symbol") or f"unknown-{i}")
        entries.append(
            {
                "symbol": symbol,
                "interval": pack.get("interval"),
                "source": pack.get("source"),
                "run_id": pack.get("run_id"),
                "report_id": pack.get("report_id"),
                "edge_status": pack.get("edge_status"),
                "edge_score": pack.get("edge_score"),
                "dataset_row_count": pack.get("dataset_row_count"),
                "split_count": pack.get("split_count"),
                "return_column": pack.get("return_column"),
                "integration_health_passed": pack.get("integration_health_passed"),
                "pack_index_path": str(index_path),
                "pack_path": index.get("pack_path"),
                "markdown_path": index.get("markdown_path"),
                "artifact_map_path": index.get("artifact_map_path"),
                "pack_payload_sha256": _payload_sha256(pack),
                "hypothetical_only": True,
                **build_research_safety_stamp(),
            }
        )

    if not entries:
        raise MultiAssetReportError("At least one report pack index must be provided.")

    return entries


def build_multi_asset_report(
    entries: list[dict[str, Any]],
    *,
    report_name: str = "qrds-multi-asset-report",
) -> dict[str, Any]:
    """Build a research-only multi-asset report from symbol entries."""
    if not entries:
        raise MultiAssetReportError("entries cannot be empty.")

    for i, entry in enumerate(entries):
        _assert_research_payload(entry, name=f"multi_asset_entry[{i}]")
        if entry.get("integration_health_passed") is not True:
            raise MultiAssetReportError(f"Entry {i} integration health did not pass.")

    edge_status_counts: dict[str, int] = {}
    edge_scores: list[float] = []
    dataset_rows: list[float] = []
    split_counts: list[float] = []

    for entry in entries:
        status = str(entry.get("edge_status"))
        edge_status_counts[status] = edge_status_counts.get(status, 0) + 1

        score = _score_value(entry.get("edge_score"))
        if score is not None:
            edge_scores.append(score)

        rows = _score_value(entry.get("dataset_row_count"))
        if rows is not None:
            dataset_rows.append(rows)

        splits = _score_value(entry.get("split_count"))
        if splits is not None:
            split_counts.append(splits)

    ranked_entries = sorted(
        entries,
        key=lambda entry: (
            -EDGE_STATUS_ORDER.get(str(entry.get("edge_status")), -1),
            -(_score_value(entry.get("edge_score")) or -999.0),
            str(entry.get("symbol")),
        ),
    )

    rankings = [
        {
            "rank": rank,
            "symbol": entry["symbol"],
            "edge_status": entry.get("edge_status"),
            "edge_score": entry.get("edge_score"),
            "ranking_basis": "edge_status_then_edge_score_research_only",
        }
        for rank, entry in enumerate(ranked_entries, start=1)
    ]

    report = {
        "schema": MULTI_ASSET_REPORT_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "report_name": report_name,
        "asset_count": len(entries),
        "symbols": [entry["symbol"] for entry in entries],
        "edge_status_counts": edge_status_counts,
        "mean_edge_score": mean(edge_scores) if edge_scores else None,
        "total_dataset_row_count": int(sum(dataset_rows)) if dataset_rows else None,
        "mean_split_count": mean(split_counts) if split_counts else None,
        "rankings": rankings,
        "entries": entries,
        "caveats": [
            "Research-only multi-asset aggregation; not an allocation model.",
            "Rankings are descriptive research summaries, not trading recommendations.",
            "No position sizing, portfolio weights or execution instructions are produced.",
            "Inputs are offline/local research report packs unless expanded later.",
        ],
        "allocation_generated": False,
        "portfolio_decision_generated": False,
        "hypothetical_only": True,
        **build_research_safety_stamp(),
    }

    return report


def validate_multi_asset_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Return quality issues for a multi-asset report."""
    issues = collect_research_contract_issues(
        report,
        name="multi_asset_report",
        require_schema=True,
        require_app_mode=True,
        require_research_allowed=True,
    )

    if report.get("schema") != MULTI_ASSET_REPORT_SCHEMA_VERSION:
        issues.append(
            {
                "code": "INVALID_MULTI_ASSET_REPORT_SCHEMA",
                "severity": "error",
                "name": "multi_asset_report",
                "message": "Invalid multi-asset report schema.",
            }
        )

    if int(report.get("asset_count", 0) or 0) <= 0:
        issues.append(
            {
                "code": "EMPTY_MULTI_ASSET_REPORT",
                "severity": "error",
                "name": "multi_asset_report",
                "message": "Multi-asset report must include at least one asset.",
            }
        )

    if not report.get("rankings"):
        issues.append(
            {
                "code": "MISSING_MULTI_ASSET_RANKINGS",
                "severity": "error",
                "name": "multi_asset_report",
                "message": "Multi-asset report must include research rankings.",
            }
        )

    for flag in ("allocation_generated", "portfolio_decision_generated"):
        if report.get(flag) is True:
            issues.append(
                {
                    "code": "UNSAFE_MULTI_ASSET_DECISION_FLAG",
                    "severity": "error",
                    "name": "multi_asset_report",
                    "message": f"{flag} must remain False.",
                }
            )

    return issues


def render_multi_asset_report_markdown(report: dict[str, Any]) -> str:
    """Render a human-readable markdown multi-asset report."""
    lines = [
        "# QRDS Multi-Asset Research Report",
        "",
        "## Status",
        "",
        f"- Report name: `{report.get('report_name')}`",
        f"- Mode: `{report.get('app_mode')}`",
        f"- Asset count: `{report.get('asset_count')}`",
        f"- Symbols: `{', '.join(report.get('symbols', []))}`",
        f"- Mean edge score: `{report.get('mean_edge_score')}`",
        "",
        "## Edge status counts",
        "",
    ]

    for status, count in sorted(report.get("edge_status_counts", {}).items()):
        lines.append(f"- `{status}`: `{count}`")

    lines.extend(
        [
            "",
            "## Research rankings",
            "",
            "| Rank | Symbol | Edge status | Edge score |",
            "|---:|---|---|---:|",
        ]
    )

    for ranking in report.get("rankings", []):
        lines.append(
            f"| {ranking.get('rank')} | `{ranking.get('symbol')}` | "
            f"`{ranking.get('edge_status')}` | `{ranking.get('edge_score')}` |"
        )

    lines.extend(
        [
            "",
            "## Asset entries",
            "",
            "| Symbol | Dataset rows | Splits | Pack |",
            "|---|---:|---:|---|",
        ]
    )

    for entry in report.get("entries", []):
        lines.append(
            f"| `{entry.get('symbol')}` | `{entry.get('dataset_row_count')}` | "
            f"`{entry.get('split_count')}` | `{entry.get('pack_path')}` |"
        )

    lines.extend(
        [
            "",
            "## Caveats",
            "",
        ]
    )
    for caveat in report.get("caveats", []):
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


def write_multi_asset_report(
    *,
    pack_index_paths: Iterable[str | Path],
    output_dir: str | Path,
    report_name: str = "qrds-multi-asset-report",
) -> dict[str, Any]:
    """Write multi-asset report JSON, markdown and index."""
    entries = load_report_pack_entries(pack_index_paths)
    report = build_multi_asset_report(entries, report_name=report_name)

    issues = validate_multi_asset_report(report)
    if any(issue["severity"] == "error" for issue in issues):
        raise MultiAssetReportError(f"Multi-asset report validation errors: {issues}")

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    report_path = root / "multi_asset_research_report.json"
    markdown_path = root / "multi_asset_research_report.md"
    entries_path = root / "multi_asset_entries.json"
    index_path = root / "multi_asset_research_index.json"

    _write_json(report_path, report)
    _write_text(markdown_path, render_multi_asset_report_markdown(report))
    _write_json(entries_path, {"schema": "qrds.multi_asset_entries.v1", "entries": entries, **build_research_safety_stamp()})

    index = {
        "schema": MULTI_ASSET_REPORT_INDEX_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "report_name": report_name,
        "report_path": str(report_path),
        "markdown_path": str(markdown_path),
        "entries_path": str(entries_path),
        "report_file_sha256": compute_file_sha256(report_path),
        "markdown_file_sha256": compute_file_sha256(markdown_path),
        "entries_file_sha256": compute_file_sha256(entries_path),
        "asset_count": report["asset_count"],
        "symbols": report["symbols"],
        "allocation_generated": False,
        "portfolio_decision_generated": False,
        **build_research_safety_stamp(),
    }
    _write_json(index_path, index)

    index["index_path"] = str(index_path)
    _write_json(index_path, index)

    return index


def load_multi_asset_report(index_path: str | Path) -> dict[str, Any]:
    """Load multi-asset report from index."""
    index = _read_json(index_path)
    if index.get("schema") != MULTI_ASSET_REPORT_INDEX_SCHEMA_VERSION:
        raise MultiAssetReportError("Invalid multi-asset report index schema.")

    report = _read_json(index["report_path"])
    entries_payload = _read_json(index["entries_path"])
    markdown = Path(index["markdown_path"]).read_text(encoding="utf-8")

    issues = validate_multi_asset_report(report)
    if any(issue["severity"] == "error" for issue in issues):
        raise MultiAssetReportError(f"Loaded multi-asset report validation errors: {issues}")

    return {
        "index": index,
        "report": report,
        "entries": entries_payload.get("entries", []),
        "markdown": markdown,
        **build_research_safety_stamp(),
    }
