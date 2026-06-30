"""Research run manifest builder.

Offline only.
No API key.
No account connection.
No orders.
No real capital.

A research run manifest is the audit receipt for a QRDS/QOS research run.
It records which pipeline stage ran, which reports were used, which commit was
used, whether gates passed, and which artifacts were produced.

It is not a trading signal and never allows operational decisions.
"""

from __future__ import annotations

import hashlib
import math
import subprocess
from datetime import datetime, timezone
from typing import Any

from crypto_decision_lab.safety.gates import build_safe_context

RESEARCH_RUN_MANIFEST_SCHEMA_VERSION = "qrds.research_run_manifest.v1"

SAFE_FALSE_FLAGS = (
    "api_key_required",
    "api_key_present",
    "account_connection_required",
    "orders_generated",
    "real_capital_used",
    "operational_decision_allowed",
)

REQUIRED_MANIFEST_KEYS = (
    "schema",
    "run_id",
    "generated_at",
    "symbol",
    "interval",
    "source",
    "pipeline_commit",
    "pipeline_stages",
    "upstream_reports",
    "research_allowed",
    "operational_decision_allowed",
)


class ResearchRunManifestError(ValueError):
    """Raised when a research run manifest cannot be built safely."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bad_number(value: Any) -> bool:
    if value is None or isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return not math.isfinite(float(value))
    return False


def get_current_git_commit() -> str:
    """Return the current git commit hash, or 'unknown' when unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            check=True,
            text=True,
        )
    except Exception:
        return "unknown"

    commit = result.stdout.strip()
    return commit or "unknown"


def _stable_run_id(
    *,
    generated_at: str,
    symbol: str,
    interval: str,
    source: str,
    pipeline_commit: str,
) -> str:
    payload = "|".join([generated_at, symbol, interval, source, pipeline_commit])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def assert_report_is_research_only(report: dict[str, Any], *, name: str) -> None:
    """Block unsafe upstream reports."""
    if not isinstance(report, dict):
        raise ResearchRunManifestError(f"{name} report must be a dictionary.")

    if report.get("app_mode") != "INTERACTIVE_RESEARCH_ONLY":
        raise ResearchRunManifestError(f"{name} report is not INTERACTIVE_RESEARCH_ONLY.")

    for flag in SAFE_FALSE_FLAGS:
        if report.get(flag) is True:
            raise ResearchRunManifestError(f"{name} report has unsafe flag {flag}=True.")


def assert_dql_report_passed(dql_report: dict[str, Any]) -> None:
    assert_report_is_research_only(dql_report, name="DQL")
    error_count = dql_report.get("issue_summary", {}).get("error_count", 1)
    if error_count > 0:
        raise ResearchRunManifestError("DQL report has errors; manifest blocked.")


def assert_dataset_report_passed(dataset_report: dict[str, Any]) -> None:
    assert_report_is_research_only(dataset_report, name="Integrated dataset")
    if dataset_report.get("dataset_quality_passed") is not True:
        raise ResearchRunManifestError("Integrated dataset quality did not pass; manifest blocked.")


def assert_export_report_safe(export_report: dict[str, Any] | None) -> None:
    if export_report is None:
        return
    assert_report_is_research_only(export_report, name="Export")

    # Keep this flexible because export reports can evolve by schema version.
    # When these fields exist, they must not explicitly fail.
    for key in ("export_quality_passed", "export_passed", "export_successful"):
        if export_report.get(key) is False:
            raise ResearchRunManifestError(f"Export report has {key}=False; manifest blocked.")


def build_research_run_manifest(
    *,
    symbol: str,
    interval: str,
    source: str,
    dql_report: dict[str, Any],
    regime_report: dict[str, Any],
    dataset_report: dict[str, Any],
    export_report: dict[str, Any] | None = None,
    pipeline_commit: str | None = None,
    pipeline_stages: list[str] | None = None,
    artifacts: list[dict[str, Any]] | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Build a research-only audit manifest for one QRDS/QOS run."""
    safe = build_safe_context()

    assert_dql_report_passed(dql_report)
    assert_report_is_research_only(regime_report, name="Regime")
    assert_dataset_report_passed(dataset_report)
    assert_export_report_safe(export_report)

    generated_at = _now_iso()
    commit = pipeline_commit or get_current_git_commit()

    stages = pipeline_stages or [
        "safety",
        "dql",
        "features",
        "regime",
        "targets",
        "integrated_dataset",
        "export",
        "manifest",
    ]

    run_id = _stable_run_id(
        generated_at=generated_at,
        symbol=symbol,
        interval=interval,
        source=source,
        pipeline_commit=commit,
    )

    upstream_reports: dict[str, Any] = {
        "dql": {
            "schema": dql_report.get("schema"),
            "dql_score": dql_report.get("dql_score"),
            "error_count": dql_report.get("issue_summary", {}).get("error_count"),
        },
        "regime": {
            "schema": regime_report.get("schema"),
            "regime": regime_report.get("regime"),
            "feature_row_count": regime_report.get("feature_row_count"),
        },
        "integrated_dataset": {
            "schema": dataset_report.get("schema"),
            "row_count": dataset_report.get("row_count"),
            "dataset_quality_passed": dataset_report.get("dataset_quality_passed"),
            "error_count": dataset_report.get("issue_summary", {}).get("error_count"),
        },
    }

    if export_report is not None:
        upstream_reports["export"] = {
            "schema": export_report.get("schema"),
            "row_count": export_report.get("row_count"),
            "export_format": export_report.get("export_format"),
            "output_path": export_report.get("output_path"),
        }

    manifest = {
        "schema": RESEARCH_RUN_MANIFEST_SCHEMA_VERSION,
        "run_id": run_id,
        "generated_at": generated_at,
        "symbol": symbol,
        "interval": interval,
        "source": source,
        "pipeline_commit": commit,
        "pipeline_stages": stages,
        "upstream_reports": upstream_reports,
        "artifacts": artifacts or [],
        "notes": notes,
        "manifest_quality_passed": True,
        "research_allowed": True,
        "operational_decision_allowed": False,
        "app_mode": "INTERACTIVE_RESEARCH_ONLY",
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "orders_generated": False,
        "real_capital_used": False,
    }

    for flag in SAFE_FALSE_FLAGS:
        assert manifest[flag] == safe[flag]

    issues = validate_research_run_manifest(manifest)
    if any(issue["severity"] == "error" for issue in issues):
        raise ResearchRunManifestError(f"Manifest validation failed: {issues}")

    return manifest


def validate_research_run_manifest(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Return research run manifest quality issues."""
    if not isinstance(manifest, dict):
        return [{
            "code": "MANIFEST_NOT_DICT",
            "severity": "error",
            "message": "Manifest must be a dictionary.",
        }]

    issues: list[dict[str, Any]] = []

    missing = [key for key in REQUIRED_MANIFEST_KEYS if key not in manifest]
    if missing:
        issues.append({
            "code": "MISSING_MANIFEST_KEYS",
            "severity": "error",
            "message": f"Missing manifest keys: {missing}",
        })

    if manifest.get("schema") != RESEARCH_RUN_MANIFEST_SCHEMA_VERSION:
        issues.append({
            "code": "BAD_MANIFEST_SCHEMA",
            "severity": "error",
            "message": "Unexpected research run manifest schema.",
        })

    if manifest.get("app_mode") != "INTERACTIVE_RESEARCH_ONLY":
        issues.append({
            "code": "BAD_APP_MODE",
            "severity": "error",
            "message": "Manifest app_mode must be INTERACTIVE_RESEARCH_ONLY.",
        })

    for flag in SAFE_FALSE_FLAGS:
        if manifest.get(flag) is True:
            issues.append({
                "code": "UNSAFE_MANIFEST_FLAG",
                "severity": "error",
                "message": f"Manifest has unsafe flag {flag}=True.",
            })

    upstream = manifest.get("upstream_reports", {})
    dataset = upstream.get("integrated_dataset", {}) if isinstance(upstream, dict) else {}
    if dataset.get("dataset_quality_passed") is not True:
        issues.append({
            "code": "DATASET_QUALITY_NOT_PASSED",
            "severity": "error",
            "message": "Integrated dataset quality must pass before manifest approval.",
        })

    for key, value in manifest.items():
        if _bad_number(value):
            issues.append({
                "code": "NON_FINITE_MANIFEST_VALUE",
                "severity": "error",
                "message": f"Manifest value {key!r} is non-finite.",
            })

    return issues


def build_research_run_manifest_report(manifest: dict[str, Any]) -> dict[str, Any]:
    """Build a compact quality report for a manifest."""
    safe = build_safe_context()
    issues = validate_research_run_manifest(manifest)
    error_count = sum(1 for issue in issues if issue["severity"] == "error")
    warning_count = sum(1 for issue in issues if issue["severity"] == "warning")

    report = {
        "schema": "qrds.research_run_manifest_report.v1",
        "generated_at": _now_iso(),
        "manifest_schema": manifest.get("schema") if isinstance(manifest, dict) else None,
        "run_id": manifest.get("run_id") if isinstance(manifest, dict) else None,
        "manifest_quality_passed": error_count == 0,
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

    for flag in SAFE_FALSE_FLAGS:
        assert report[flag] == safe[flag]

    return report
