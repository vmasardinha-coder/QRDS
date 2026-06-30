"""Research-only integrated dataset export utilities.

Offline only.
No API key.
No account connection.
No orders.
No real capital.

This module exports approved integrated research datasets to local files.
Exports are research artifacts, not trading signals.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.safety.gates import build_safe_context

EXPORT_REPORT_SCHEMA_VERSION = "qrds.research_dataset_export.v1"
ALLOWED_EXPORT_FORMATS = ("jsonl", "csv")


class ResearchDatasetExportError(ValueError):
    """Raised when research dataset export cannot proceed safely."""


def assert_dataset_report_approved(dataset_report: dict[str, Any]) -> None:
    """Require an approved integrated dataset report before export."""
    if not isinstance(dataset_report, dict):
        raise ResearchDatasetExportError("Dataset report must be a dictionary.")

    if dataset_report.get("app_mode") != "INTERACTIVE_RESEARCH_ONLY":
        raise ResearchDatasetExportError("Dataset report is not INTERACTIVE_RESEARCH_ONLY.")

    must_be_false = (
        "api_key_required",
        "api_key_present",
        "account_connection_required",
        "orders_generated",
        "real_capital_used",
        "operational_decision_allowed",
    )

    for flag in must_be_false:
        if dataset_report.get(flag) is True:
            raise ResearchDatasetExportError(f"Dataset report has unsafe flag {flag}=True.")

    if dataset_report.get("dataset_quality_passed") is not True:
        raise ResearchDatasetExportError("Dataset quality did not pass; export blocked.")

    if dataset_report.get("issue_summary", {}).get("error_count", 1) > 0:
        raise ResearchDatasetExportError("Dataset report has errors; export blocked.")


def infer_export_format(output_path: str | Path, export_format: str | None = None) -> str:
    """Infer export format from explicit value or file suffix."""
    if export_format is not None:
        fmt = export_format.lower().strip()
    else:
        suffix = Path(output_path).suffix.lower().lstrip(".")
        fmt = suffix

    if fmt not in ALLOWED_EXPORT_FORMATS:
        raise ResearchDatasetExportError(
            f"Unsupported export format {fmt!r}. Allowed: {ALLOWED_EXPORT_FORMATS}."
        )

    return fmt


def _ordered_fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    """Return deterministic CSV columns preserving first-seen key order."""
    fieldnames: list[str] = []
    seen: set[str] = set()

    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)

    return fieldnames


def write_jsonl(rows: list[dict[str, Any]], output_path: str | Path) -> Path:
    """Write rows as deterministic JSON Lines."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False))
            handle.write("\n")

    return path


def write_csv(rows: list[dict[str, Any]], output_path: str | Path) -> Path:
    """Write rows as CSV with deterministic field order."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = _ordered_fieldnames(rows)

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n", restval="")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    return path


def export_integrated_research_dataset(
    rows: list[dict[str, Any]],
    *,
    dataset_report: dict[str, Any],
    output_path: str | Path,
    export_format: str | None = None,
) -> dict[str, Any]:
    """Export an approved integrated research dataset to a local file."""
    safe = build_safe_context()
    assert_dataset_report_approved(dataset_report)

    if not rows:
        raise ResearchDatasetExportError("Cannot export an empty integrated research dataset.")

    if not all(isinstance(row, dict) for row in rows):
        raise ResearchDatasetExportError("All dataset rows must be dictionaries.")

    fmt = infer_export_format(output_path, export_format)

    if fmt == "jsonl":
        path = write_jsonl(rows, output_path)
    elif fmt == "csv":
        path = write_csv(rows, output_path)
    else:  # defensive only; infer_export_format already validates.
        raise ResearchDatasetExportError(f"Unsupported export format {fmt!r}.")

    bytes_written = path.stat().st_size

    report = {
        "schema": EXPORT_REPORT_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "symbol": dataset_report.get("symbol"),
        "interval": dataset_report.get("interval"),
        "source": dataset_report.get("source"),
        "format": fmt,
        "output_path": str(path),
        "row_count": len(rows),
        "bytes_written": bytes_written,
        "export_completed": True,
        "research_allowed": True,
        "operational_decision_allowed": False,
        "app_mode": "INTERACTIVE_RESEARCH_ONLY",
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "orders_generated": False,
        "real_capital_used": False,
    }

    for flag in (
        "api_key_present",
        "api_key_required",
        "account_connection_required",
        "orders_generated",
        "real_capital_used",
        "operational_decision_allowed",
    ):
        assert report[flag] == safe[flag]

    return report
