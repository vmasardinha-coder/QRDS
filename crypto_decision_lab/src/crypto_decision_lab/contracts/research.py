"""Central research-only contract utilities for QRDS.

This module freezes the common research-only contract used across artifacts.

It does not refactor older modules yet. It creates a single reference point for
new modules and integration health checks.

Offline/research-only.
No API key.
No account connection.
No authenticated exchange access.
No orders.
No real capital.
No operational decisions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from crypto_decision_lab.safety.gates import build_safe_context

RESEARCH_CONTRACT_SCHEMA_VERSION = "qrds.research_contract.v1"
INTEGRATION_HEALTH_REPORT_SCHEMA_VERSION = "qrds.integration_health_report.v1"
CONTRACT_FREEZE_REGISTRY_SCHEMA_VERSION = "qrds.contract_freeze_registry.v1"

RESEARCH_APP_MODE = "INTERACTIVE_RESEARCH_ONLY"

RESEARCH_TRUE_FLAGS = (
    "research_allowed",
)

RESEARCH_FALSE_FLAGS = (
    "operational_decision_allowed",
    "api_key_required",
    "api_key_present",
    "account_connection_required",
    "authenticated_connection_used",
    "orders_generated",
    "real_orders_generated",
    "real_capital_used",
    "orders_allowed",
    "trading_signal_generated",
    "executable_signal_generated",
    "recommendation_generated",
)

CORE_FALSE_FLAGS = (
    "operational_decision_allowed",
    "api_key_required",
    "api_key_present",
    "account_connection_required",
    "orders_generated",
    "real_capital_used",
)

APPROVED_PHASES = (
    ("6A", "DQL"),
    ("6B", "Feature Engineering"),
    ("6C", "Regime Diagnostics"),
    ("6D", "Target Labels"),
    ("6E", "Integrated Research Dataset"),
    ("6F", "Dataset Export"),
    ("6G", "Research Run Manifest"),
    ("6H", "Research Run Bundle"),
    ("6I", "Research Run Registry"),
    ("6J", "Research Pipeline Orchestrator"),
    ("6K", "Offline Research CLI"),
    ("6L", "Fixture Dataset Expansion"),
    ("6M", "Public Data Adapter Contract"),
    ("6N", "OKX Public Research Adapter"),
    ("6O", "Public Data Cache Layer"),
    ("6P", "Walk-forward Splitter"),
    ("6Q", "Baseline Model Layer"),
    ("6R", "Backtest Skeleton"),
    ("6S", "Edge Report v1"),
    ("7A", "Integration Health / Contract Freeze"),
)

KNOWN_ARTIFACT_SCHEMAS = (
    "qrds.dql_report.v1",
    "qrds.research_candle_fixture.v1",
    "qrds.public_candle_batch.v1",
    "qrds.public_data_adapter_report.v1",
    "qrds.okx_public_adapter.v1",
    "qrds.public_data_cache_record.v1",
    "qrds.public_data_cache_index.v1",
    "qrds.walk_forward_split.v1",
    "qrds.walk_forward_report.v1",
    "qrds.baseline_model.v1",
    "qrds.baseline_prediction.v1",
    "qrds.baseline_evaluation.v1",
    "qrds.baseline_walk_forward_report.v1",
    "qrds.backtest_event.v1",
    "qrds.backtest_metrics.v1",
    "qrds.backtest_report.v1",
    "qrds.backtest_walk_forward_report.v1",
    "qrds.edge_report.v1",
)


class ResearchContractError(ValueError):
    """Raised when an artifact violates the frozen research-only contract."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_research_safety_stamp(*, include_extended: bool = True) -> dict[str, Any]:
    """Return the canonical QRDS research-only safety stamp."""
    safe = build_safe_context()

    stamp: dict[str, Any] = {
        "research_allowed": True,
        "operational_decision_allowed": False,
        "app_mode": RESEARCH_APP_MODE,
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "orders_generated": False,
        "real_capital_used": False,
    }

    if include_extended:
        stamp.update(
            {
                "authenticated_connection_used": False,
                "real_orders_generated": False,
                "orders_allowed": False,
                "trading_signal_generated": False,
                "executable_signal_generated": False,
                "recommendation_generated": False,
            }
        )

    for flag in CORE_FALSE_FLAGS:
        assert stamp[flag] == safe[flag]

    return stamp


def collect_research_contract_issues(
    payload: Any,
    *,
    name: str = "artifact",
    require_schema: bool = True,
    require_app_mode: bool = False,
    require_research_allowed: bool = False,
) -> list[dict[str, Any]]:
    """Collect research-only contract issues for one artifact.

    The function is deliberately tolerant of older artifacts that do not yet
    expose every extended flag. It only errors when a dangerous flag is True.
    """
    issues: list[dict[str, Any]] = []

    if not isinstance(payload, dict):
        return [
            {
                "code": "INVALID_ARTIFACT_TYPE",
                "severity": "error",
                "name": name,
                "message": "Artifact must be a dictionary.",
            }
        ]

    if require_schema and not payload.get("schema"):
        issues.append(
            {
                "code": "MISSING_SCHEMA",
                "severity": "error",
                "name": name,
                "message": "Artifact is missing schema.",
            }
        )

    if require_app_mode and payload.get("app_mode") != RESEARCH_APP_MODE:
        issues.append(
            {
                "code": "INVALID_APP_MODE",
                "severity": "error",
                "name": name,
                "message": f"Artifact app_mode must be {RESEARCH_APP_MODE}.",
            }
        )

    if require_research_allowed and payload.get("research_allowed") is not True:
        issues.append(
            {
                "code": "RESEARCH_NOT_ALLOWED",
                "severity": "error",
                "name": name,
                "message": "Artifact must set research_allowed=True.",
            }
        )

    for flag in RESEARCH_FALSE_FLAGS:
        if payload.get(flag) is True:
            issues.append(
                {
                    "code": "UNSAFE_RESEARCH_FLAG",
                    "severity": "error",
                    "name": name,
                    "flag": flag,
                    "message": f"Artifact has unsafe flag {flag}=True.",
                }
            )

    return issues


def assert_research_only_artifact(
    payload: dict[str, Any],
    *,
    name: str = "artifact",
    require_schema: bool = True,
    require_app_mode: bool = False,
    require_research_allowed: bool = False,
) -> None:
    """Raise if an artifact violates the frozen research-only contract."""
    issues = collect_research_contract_issues(
        payload,
        name=name,
        require_schema=require_schema,
        require_app_mode=require_app_mode,
        require_research_allowed=require_research_allowed,
    )
    error_count = sum(1 for issue in issues if issue["severity"] == "error")

    if error_count:
        raise ResearchContractError(f"{name} violates research-only contract: {issues}")


def build_contract_freeze_registry() -> dict[str, Any]:
    """Build a compact registry of approved phases and known artifact schemas."""
    stamp = build_research_safety_stamp()

    return {
        "schema": CONTRACT_FREEZE_REGISTRY_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "contract_schema": RESEARCH_CONTRACT_SCHEMA_VERSION,
        "app_mode": RESEARCH_APP_MODE,
        "approved_phase_count": len(APPROVED_PHASES),
        "approved_phases": [
            {"phase": phase, "name": name}
            for phase, name in APPROVED_PHASES
        ],
        "known_artifact_schema_count": len(KNOWN_ARTIFACT_SCHEMAS),
        "known_artifact_schemas": list(KNOWN_ARTIFACT_SCHEMAS),
        "frozen_false_flags": list(RESEARCH_FALSE_FLAGS),
        "frozen_true_flags": list(RESEARCH_TRUE_FLAGS),
        **stamp,
    }


def build_integration_health_report(
    artifacts: dict[str, dict[str, Any]],
    *,
    report_name: str = "integration-health",
) -> dict[str, Any]:
    """Build a research-only health report for key artifacts."""
    stamp = build_research_safety_stamp()
    artifact_results: list[dict[str, Any]] = []

    for artifact_name, artifact in artifacts.items():
        issues = collect_research_contract_issues(
            artifact,
            name=artifact_name,
            require_schema=True,
            require_app_mode=False,
            require_research_allowed=False,
        )
        error_count = sum(1 for issue in issues if issue["severity"] == "error")
        warning_count = sum(1 for issue in issues if issue["severity"] == "warning")

        artifact_results.append(
            {
                "artifact_name": artifact_name,
                "schema": artifact.get("schema") if isinstance(artifact, dict) else None,
                "issue_count": len(issues),
                "error_count": error_count,
                "warning_count": warning_count,
                "issues": issues,
                "research_contract_passed": error_count == 0,
            }
        )

    total_errors = sum(result["error_count"] for result in artifact_results)
    total_warnings = sum(result["warning_count"] for result in artifact_results)

    return {
        "schema": INTEGRATION_HEALTH_REPORT_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "report_name": report_name,
        "artifact_count": len(artifact_results),
        "artifact_results": artifact_results,
        "integration_health_passed": total_errors == 0,
        "issue_summary": {
            "total_issues": total_errors + total_warnings,
            "error_count": total_errors,
            "warning_count": total_warnings,
        },
        **stamp,
    }


def validate_contract_freeze_registry(registry: dict[str, Any]) -> list[dict[str, Any]]:
    """Return quality issues for the contract freeze registry."""
    issues = collect_research_contract_issues(
        registry,
        name="contract_freeze_registry",
        require_schema=True,
        require_app_mode=True,
        require_research_allowed=True,
    )

    if registry.get("schema") != CONTRACT_FREEZE_REGISTRY_SCHEMA_VERSION:
        issues.append(
            {
                "code": "INVALID_CONTRACT_FREEZE_SCHEMA",
                "severity": "error",
                "name": "contract_freeze_registry",
                "message": "Invalid contract freeze registry schema.",
            }
        )

    if registry.get("approved_phase_count") != len(registry.get("approved_phases", [])):
        issues.append(
            {
                "code": "PHASE_COUNT_MISMATCH",
                "severity": "error",
                "name": "contract_freeze_registry",
                "message": "approved_phase_count does not match approved_phases length.",
            }
        )

    return issues


def validate_integration_health_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Return quality issues for an integration health report."""
    issues = collect_research_contract_issues(
        report,
        name="integration_health_report",
        require_schema=True,
        require_app_mode=True,
        require_research_allowed=True,
    )

    if report.get("schema") != INTEGRATION_HEALTH_REPORT_SCHEMA_VERSION:
        issues.append(
            {
                "code": "INVALID_INTEGRATION_HEALTH_SCHEMA",
                "severity": "error",
                "name": "integration_health_report",
                "message": "Invalid integration health report schema.",
            }
        )

    if report.get("integration_health_passed") is not True:
        issues.append(
            {
                "code": "INTEGRATION_HEALTH_NOT_PASSED",
                "severity": "error",
                "name": "integration_health_report",
                "message": "Integration health report did not pass.",
            }
        )

    return issues
