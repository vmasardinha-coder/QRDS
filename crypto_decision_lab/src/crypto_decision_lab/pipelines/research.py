"""Research-only end-to-end pipeline orchestrator.

Offline only.
No API key.
No account connection.
No orders.
No real capital.

This module connects the current research stack:

DQL
→ Features
→ Regime Diagnostics
→ Target Labels
→ Integrated Research Dataset
→ Export
→ Manifest
→ Bundle
→ Registry

The output is an auditable research run, not a trading signal.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from crypto_decision_lab.datasets.research import (
    build_integrated_dataset_report,
    build_integrated_research_dataset,
)
from crypto_decision_lab.dql.report import build_dql_report
from crypto_decision_lab.features.engineering import build_feature_matrix
from crypto_decision_lab.features.quality import build_feature_quality_report
from crypto_decision_lab.regimes.diagnostics import build_regime_report
from crypto_decision_lab.runs.bundle import build_research_run_bundle, build_research_run_bundle_report
from crypto_decision_lab.runs.registry import (
    build_research_run_registry,
    build_research_run_registry_entry,
    build_research_run_registry_report,
    write_research_run_registry,
)
from crypto_decision_lab.safety.gates import build_safe_context
from crypto_decision_lab.targets.labels import build_target_label_report, build_target_labels
from crypto_decision_lab.targets.quality import build_target_quality_report

RESEARCH_PIPELINE_RUN_SCHEMA_VERSION = "qrds.research_pipeline_run.v1"
RESEARCH_PIPELINE_REPORT_SCHEMA_VERSION = "qrds.research_pipeline_report.v1"
RESEARCH_PIPELINE_EXPORT_SCHEMA_VERSION = "qrds.research_pipeline_export.v1"


class ResearchPipelineError(ValueError):
    """Raised when the research pipeline cannot run safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _assert_research_only_payload(payload: dict[str, Any], *, name: str) -> None:
    if not isinstance(payload, dict):
        raise ResearchPipelineError(f"{name} must be a dictionary.")

    if payload.get("app_mode") != "INTERACTIVE_RESEARCH_ONLY":
        raise ResearchPipelineError(f"{name} is not INTERACTIVE_RESEARCH_ONLY.")

    must_be_false = (
        "api_key_required",
        "api_key_present",
        "account_connection_required",
        "orders_generated",
        "real_capital_used",
        "operational_decision_allowed",
    )

    for flag in must_be_false:
        if payload.get(flag) is True:
            raise ResearchPipelineError(f"{name} has unsafe flag {flag}=True.")


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return str(path)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            json.dump(row, handle, sort_keys=True, default=str)
            handle.write("\n")
    return str(path)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames: list[str] = []
    seen: set[str] = set()

    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)

    with path.open("w", encoding="utf-8", newline="") as handle:
        if fieldnames:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return str(path)


def _build_pipeline_export_report(
    *,
    jsonl_path: str,
    csv_path: str,
    row_count: int,
    symbol: str,
    interval: str,
    source: str,
) -> dict[str, Any]:
    safe = build_safe_context()

    jsonl_file = Path(jsonl_path)
    csv_file = Path(csv_path)

    issues: list[dict[str, Any]] = []
    for file_path in (jsonl_file, csv_file):
        if not file_path.exists():
            issues.append(
                {
                    "code": "MISSING_PIPELINE_EXPORT_FILE",
                    "severity": "error",
                    "index": None,
                    "message": f"Missing export file: {file_path}",
                }
            )
        elif row_count > 0 and file_path.stat().st_size <= 0:
            issues.append(
                {
                    "code": "EMPTY_PIPELINE_EXPORT_FILE",
                    "severity": "error",
                    "index": None,
                    "message": f"Empty export file: {file_path}",
                }
            )

    error_count = sum(1 for issue in issues if issue["severity"] == "error")
    warning_count = sum(1 for issue in issues if issue["severity"] == "warning")

    report = {
        "schema": RESEARCH_PIPELINE_EXPORT_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "symbol": symbol,
        "interval": interval,
        "source": source,
        "row_count": row_count,
        "artifact_count": 2,
        "jsonl_path": jsonl_path,
        "csv_path": csv_path,
        "export_quality_passed": error_count == 0,
        "issue_summary": {
            "total_issues": len(issues),
            "error_count": error_count,
            "warning_count": warning_count,
        },
        "issues": issues,
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


def _build_minimal_manifest(
    *,
    run_id: str,
    symbol: str,
    interval: str,
    source: str,
    pipeline_commit: str,
    dql_report: dict[str, Any],
    feature_quality_report: dict[str, Any],
    regime_report: dict[str, Any],
    target_quality_report: dict[str, Any],
    dataset_report: dict[str, Any],
    export_report: dict[str, Any],
    artifact_paths: list[str],
) -> dict[str, Any]:
    safe = build_safe_context()

    manifest = {
        "schema": "qrds.research_run_manifest.v1",
        "run_id": run_id,
        "generated_at": _utc_now(),
        "pipeline_commit": pipeline_commit,
        "symbol": symbol,
        "interval": interval,
        "source": source,
        "schemas": {
            "pipeline_run": RESEARCH_PIPELINE_RUN_SCHEMA_VERSION,
            "dql": dql_report.get("schema"),
            "feature_quality": feature_quality_report.get("schema"),
            "regime": regime_report.get("schema"),
            "target_quality": target_quality_report.get("schema"),
            "dataset": dataset_report.get("schema"),
            "export": export_report.get("schema"),
        },
        "dql_score": dql_report.get("dql_score"),
        "dql_error_count": dql_report.get("issue_summary", {}).get("error_count"),
        "feature_quality_passed": feature_quality_report.get("feature_quality_passed"),
        "regime": regime_report.get("regime"),
        "target_quality_passed": target_quality_report.get("target_quality_passed"),
        "dataset_quality_passed": dataset_report.get("dataset_quality_passed"),
        "dataset_row_count": dataset_report.get("row_count"),
        "export_quality_passed": export_report.get("export_quality_passed"),
        "export_artifact_count": export_report.get("artifact_count"),
        "artifact_paths": artifact_paths,
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
        assert manifest[flag] == safe[flag]

    return manifest


def validate_research_pipeline_run(run: dict[str, Any]) -> list[dict[str, Any]]:
    """Return issues for a full research pipeline run object."""
    issues: list[dict[str, Any]] = []

    required = (
        "schema",
        "run_id",
        "symbol",
        "interval",
        "source",
        "dataset_row_count",
        "research_allowed",
        "operational_decision_allowed",
        "app_mode",
        "paths",
        "reports",
    )

    missing = [key for key in required if key not in run]
    if missing:
        issues.append(
            {
                "code": "MISSING_PIPELINE_RUN_KEYS",
                "severity": "error",
                "index": None,
                "message": f"Missing pipeline run keys: {missing}",
            }
        )

    if run.get("schema") != RESEARCH_PIPELINE_RUN_SCHEMA_VERSION:
        issues.append(
            {
                "code": "INVALID_PIPELINE_RUN_SCHEMA",
                "severity": "error",
                "index": None,
                "message": "Invalid research pipeline run schema.",
            }
        )

    if run.get("operational_decision_allowed") is True:
        issues.append(
            {
                "code": "OPERATIONAL_FLAG_TRUE",
                "severity": "error",
                "index": None,
                "message": "Research pipeline run cannot allow operational decisions.",
            }
        )

    if int(run.get("dataset_row_count", 0) or 0) <= 0:
        issues.append(
            {
                "code": "EMPTY_PIPELINE_DATASET",
                "severity": "error",
                "index": None,
                "message": "Research pipeline produced no dataset rows.",
            }
        )

    paths = run.get("paths", {})
    for key in ("jsonl_path", "csv_path", "manifest_path", "registry_path"):
        value = paths.get(key)
        if not value or not Path(value).exists():
            issues.append(
                {
                    "code": "MISSING_PIPELINE_ARTIFACT",
                    "severity": "error",
                    "index": None,
                    "message": f"Missing pipeline artifact path: {key}.",
                }
            )

    return issues


def build_research_pipeline_report(run: dict[str, Any]) -> dict[str, Any]:
    """Build a quality report for a full research pipeline run."""
    safe = build_safe_context()
    _assert_research_only_payload(run, name="pipeline_run")

    issues = validate_research_pipeline_run(run)
    error_count = sum(1 for issue in issues if issue["severity"] == "error")
    warning_count = sum(1 for issue in issues if issue["severity"] == "warning")

    report = {
        "schema": RESEARCH_PIPELINE_REPORT_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "run_id": run.get("run_id"),
        "symbol": run.get("symbol"),
        "interval": run.get("interval"),
        "source": run.get("source"),
        "dataset_row_count": run.get("dataset_row_count"),
        "pipeline_quality_passed": error_count == 0,
        "issue_summary": {
            "total_issues": len(issues),
            "error_count": error_count,
            "warning_count": warning_count,
        },
        "issues": issues,
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


def run_research_pipeline(
    *,
    candles: list[dict[str, Any]],
    symbol: str,
    interval: str,
    source: str,
    output_dir: str | Path,
    expected_interval_ms: int = 3_600_000,
    pipeline_commit: str = "unknown",
    run_id: str | None = None,
    horizons: tuple[int, ...] = (1, 3),
    up_threshold: float = 0.02,
    down_threshold: float = -0.02,
    registry_name: str = "qrds-research-run-registry",
    tags: list[str] | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Run the full research-only pipeline for one candle fixture."""
    safe = build_safe_context()

    if not candles:
        raise ResearchPipelineError("candles cannot be empty.")

    run_id = run_id or f"research-run-{uuid4().hex[:12]}"
    run_dir = Path(output_dir) / run_id
    export_dir = run_dir / "exports"
    bundle_output_dir = run_dir / "bundles"
    registry_dir = run_dir / "registry"

    dql_report = build_dql_report(
        candles=candles,
        symbol=symbol,
        interval=interval,
        source=source,
        expected_interval_ms=expected_interval_ms,
    )
    _assert_research_only_payload(dql_report, name="dql_report")

    if dql_report.get("issue_summary", {}).get("error_count", 1) > 0:
        raise ResearchPipelineError("DQL report has errors; pipeline blocked.")

    feature_rows = build_feature_matrix(candles, dql_report=dql_report)
    feature_quality_report = build_feature_quality_report(
        feature_rows,
        symbol=symbol,
        interval=interval,
        source=source,
    )
    _assert_research_only_payload(feature_quality_report, name="feature_quality_report")

    regime_report = build_regime_report(
        feature_rows,
        symbol=symbol,
        interval=interval,
        source=source,
    )
    _assert_research_only_payload(regime_report, name="regime_report")

    target_labels = build_target_labels(
        feature_rows,
        regime_report=regime_report,
        horizons=horizons,
        up_threshold=up_threshold,
        down_threshold=down_threshold,
    )

    target_label_report = build_target_label_report(
        target_labels,
        symbol=symbol,
        interval=interval,
        source=source,
        regime=regime_report["regime"],
    )
    _assert_research_only_payload(target_label_report, name="target_label_report")

    target_quality_report = build_target_quality_report(
        target_labels,
        symbol=symbol,
        interval=interval,
        source=source,
    )
    _assert_research_only_payload(target_quality_report, name="target_quality_report")

    if not target_labels:
        raise ResearchPipelineError("Target labels are empty; pipeline blocked.")

    integrated_dataset = build_integrated_research_dataset(
        candles=candles,
        feature_rows=feature_rows,
        target_labels=target_labels,
        dql_report=dql_report,
        regime_report=regime_report,
    )

    dataset_report = build_integrated_dataset_report(
        integrated_dataset,
        symbol=symbol,
        interval=interval,
        source=source,
    )
    _assert_research_only_payload(dataset_report, name="dataset_report")

    jsonl_path = _write_jsonl(export_dir / "integrated_research_dataset.jsonl", integrated_dataset)
    csv_path = _write_csv(export_dir / "integrated_research_dataset.csv", integrated_dataset)

    export_report = _build_pipeline_export_report(
        jsonl_path=jsonl_path,
        csv_path=csv_path,
        row_count=len(integrated_dataset),
        symbol=symbol,
        interval=interval,
        source=source,
    )
    _assert_research_only_payload(export_report, name="export_report")

    manifest = _build_minimal_manifest(
        run_id=run_id,
        symbol=symbol,
        interval=interval,
        source=source,
        pipeline_commit=pipeline_commit,
        dql_report=dql_report,
        feature_quality_report=feature_quality_report,
        regime_report=regime_report,
        target_quality_report=target_quality_report,
        dataset_report=dataset_report,
        export_report=export_report,
        artifact_paths=[jsonl_path, csv_path],
    )

    manifest_preview_path = _write_json(run_dir / "manifest_preview.json", manifest)

    bundle = build_research_run_bundle(
        manifest=manifest,
        artifact_paths=[jsonl_path, csv_path],
        output_dir=bundle_output_dir,
        bundle_name=f"{run_id}-bundle",
    )
    _assert_research_only_payload(bundle, name="bundle")

    bundle_report = build_research_run_bundle_report(bundle)
    _assert_research_only_payload(bundle_report, name="bundle_report")

    registry_entry = build_research_run_registry_entry(
        bundle_metadata=bundle,
        manifest=manifest,
        tags=tags or ["pipeline", "research-only"],
        notes=notes,
    )
    _assert_research_only_payload(registry_entry, name="registry_entry")

    registry = build_research_run_registry([registry_entry], registry_name=registry_name)
    _assert_research_only_payload(registry, name="registry")

    registry_path = write_research_run_registry(
        registry,
        registry_dir / "research_run_registry.json",
    )

    registry_report = build_research_run_registry_report(registry)
    _assert_research_only_payload(registry_report, name="registry_report")

    run = {
        "schema": RESEARCH_PIPELINE_RUN_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "run_id": run_id,
        "pipeline_commit": pipeline_commit,
        "symbol": symbol,
        "interval": interval,
        "source": source,
        "feature_row_count": len(feature_rows),
        "target_row_count": len(target_labels),
        "dataset_row_count": len(integrated_dataset),
        "regime": regime_report.get("regime"),
        "dql_score": dql_report.get("dql_score"),
        "paths": {
            "run_dir": str(run_dir),
            "jsonl_path": jsonl_path,
            "csv_path": csv_path,
            "manifest_preview_path": manifest_preview_path,
            "manifest_path": bundle.get("manifest_path"),
            "bundle_dir": bundle.get("bundle_dir"),
            "bundle_report_path": bundle.get("bundle_report_path"),
            "registry_path": registry_path,
        },
        "reports": {
            "dql": dql_report,
            "feature_quality": feature_quality_report,
            "regime": regime_report,
            "target_label": target_label_report,
            "target_quality": target_quality_report,
            "dataset": dataset_report,
            "export": export_report,
            "bundle": bundle_report,
            "registry": registry_report,
        },
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
        assert run[flag] == safe[flag]

    pipeline_report = build_research_pipeline_report(run)
    run["reports"]["pipeline"] = pipeline_report

    pipeline_report_path = _write_json(run_dir / "pipeline_report.json", pipeline_report)
    run["paths"]["pipeline_report_path"] = pipeline_report_path

    return run
