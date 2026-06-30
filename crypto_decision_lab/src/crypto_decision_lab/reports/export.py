"""Edge report artifact export utilities.

Offline/research-only.
No API key.
No account connection.
No authenticated exchange access.
No orders.
No real capital.
No operational decisions.

This module writes Edge Report v1 artifacts to disk with stable metadata,
hashes and a compact export index.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from crypto_decision_lab.contracts.research import (
    ResearchContractError,
    assert_research_only_artifact,
    build_research_safety_stamp,
    collect_research_contract_issues,
)
from crypto_decision_lab.reports.edge import (
    EDGE_REPORT_SCHEMA_VERSION,
    summarize_edge_report_for_console,
    validate_edge_report_v1,
)

EDGE_REPORT_EXPORT_INDEX_SCHEMA_VERSION = "qrds.edge_report_export_index.v1"


class EdgeReportExportError(ValueError):
    """Raised when Edge Report v1 artifacts cannot be exported safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def compute_json_payload_sha256(payload: Any) -> str:
    """Compute deterministic SHA-256 for a JSON-compatible payload."""
    return sha256(_json_dumps(payload).encode("utf-8")).hexdigest()


def compute_file_sha256(path: str | Path) -> str:
    """Compute SHA-256 for a local file."""
    file_path = Path(path)

    if not file_path.exists() or not file_path.is_file():
        raise EdgeReportExportError(f"Cannot hash missing file: {file_path}")

    digest = sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")

    return str(path)


def assert_edge_report_exportable(edge_report: dict[str, Any]) -> None:
    """Block export of unsafe or invalid Edge Report v1 artifacts."""
    try:
        assert_research_only_artifact(
            edge_report,
            name="edge_report",
            require_schema=True,
            require_app_mode=False,
            require_research_allowed=False,
        )
    except ResearchContractError as exc:
        raise EdgeReportExportError(str(exc)) from exc

    if edge_report.get("schema") != EDGE_REPORT_SCHEMA_VERSION:
        raise EdgeReportExportError("Only Edge Report v1 artifacts can be exported.")

    issues = validate_edge_report_v1(edge_report)
    if any(issue["severity"] == "error" for issue in issues):
        raise EdgeReportExportError(f"Edge Report v1 has validation errors: {issues}")

def build_edge_report_export_index(
    *,
    edge_report: dict[str, Any],
    summary: dict[str, Any],
    report_path: str | Path,
    summary_path: str | Path,
    report_id: str,
) -> dict[str, Any]:
    """Build a compact export index for Edge Report artifacts."""
    assert_edge_report_exportable(edge_report)
    assert_research_only_artifact(
        summary,
        name="edge_report_summary",
        require_schema=True,
        require_app_mode=False,
        require_research_allowed=True,
    )

    report_file = Path(report_path)
    summary_file = Path(summary_path)
    stamp = build_research_safety_stamp()

    index = {
        "schema": EDGE_REPORT_EXPORT_INDEX_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "report_id": report_id,
        "edge_report_schema": edge_report.get("schema"),
        "edge_status": edge_report.get("edge_status"),
        "target_or_return_column": edge_report.get("target_or_return_column"),
        "dataset_row_count": edge_report.get("dataset_row_count"),
        "report_path": str(report_file),
        "summary_path": str(summary_file),
        "report_file_sha256": compute_file_sha256(report_file),
        "summary_file_sha256": compute_file_sha256(summary_file),
        "report_file_bytes": report_file.stat().st_size,
        "summary_file_bytes": summary_file.stat().st_size,
        "edge_report_payload_sha256": compute_json_payload_sha256(edge_report),
        "summary_payload_sha256": compute_json_payload_sha256(summary),
        **stamp,
    }

    return index


def validate_edge_report_export_index(index: dict[str, Any]) -> list[dict[str, Any]]:
    """Return quality issues for an Edge Report export index."""
    issues = collect_research_contract_issues(
        index,
        name="edge_report_export_index",
        require_schema=True,
        require_app_mode=True,
        require_research_allowed=True,
    )

    if index.get("schema") != EDGE_REPORT_EXPORT_INDEX_SCHEMA_VERSION:
        issues.append(
            {
                "code": "INVALID_EDGE_REPORT_EXPORT_INDEX_SCHEMA",
                "severity": "error",
                "name": "edge_report_export_index",
                "message": "Invalid Edge Report export index schema.",
            }
        )

    required_paths = ("report_path", "summary_path")
    for path_key in required_paths:
        path_value = index.get(path_key)
        if not path_value:
            issues.append(
                {
                    "code": "MISSING_EDGE_EXPORT_PATH",
                    "severity": "error",
                    "name": "edge_report_export_index",
                    "message": f"Missing {path_key}.",
                }
            )
        elif not Path(path_value).exists():
            issues.append(
                {
                    "code": "MISSING_EDGE_EXPORT_FILE",
                    "severity": "error",
                    "name": "edge_report_export_index",
                    "message": f"Exported file not found: {path_value}",
                }
            )

    return issues


def write_edge_report_artifacts(
    edge_report: dict[str, Any],
    *,
    output_dir: str | Path,
    report_id: str = "edge-report",
) -> dict[str, Any]:
    """Write Edge Report v1 JSON, console summary and export index."""
    assert_edge_report_exportable(edge_report)

    root = Path(output_dir) / report_id
    report_path = root / "edge_report.json"
    summary_path = root / "edge_summary.json"
    index_path = root / "edge_export_index.json"

    summary = summarize_edge_report_for_console(edge_report)

    _write_json(report_path, edge_report)
    _write_json(summary_path, summary)

    index = build_edge_report_export_index(
        edge_report=edge_report,
        summary=summary,
        report_path=report_path,
        summary_path=summary_path,
        report_id=report_id,
    )
    _write_json(index_path, index)

    index["index_path"] = str(index_path)
    _write_json(index_path, index)

    issues = validate_edge_report_export_index(index)
    if any(issue["severity"] == "error" for issue in issues):
        raise EdgeReportExportError(f"Edge Report export index has validation errors: {issues}")

    return index


def load_edge_report_artifacts(index_path: str | Path) -> dict[str, Any]:
    """Load Edge Report export index, report and summary."""
    path = Path(index_path)

    if not path.exists() or not path.is_file():
        raise EdgeReportExportError(f"Edge export index not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        index = json.load(handle)

    issues = validate_edge_report_export_index(index)
    if any(issue["severity"] == "error" for issue in issues):
        raise EdgeReportExportError(f"Edge Report export index has validation errors: {issues}")

    with Path(index["report_path"]).open("r", encoding="utf-8") as handle:
        edge_report = json.load(handle)

    with Path(index["summary_path"]).open("r", encoding="utf-8") as handle:
        summary = json.load(handle)

    assert_edge_report_exportable(edge_report)

    return {
        "index": index,
        "edge_report": edge_report,
        "summary": summary,
        "research_allowed": True,
        "operational_decision_allowed": False,
        "app_mode": "INTERACTIVE_RESEARCH_ONLY",
    }
