"""Research-only run registry.

Offline only.
No API key.
No account connection.
No orders.
No real capital.

The registry is an auditable index of research run bundles.
It is a catalog, not a trading signal.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from crypto_decision_lab.safety.gates import build_safe_context

RESEARCH_RUN_REGISTRY_SCHEMA_VERSION = "qrds.research_run_registry.v1"
RESEARCH_RUN_REGISTRY_ENTRY_SCHEMA_VERSION = "qrds.research_run_registry_entry.v1"


class ResearchRunRegistryError(ValueError):
    """Raised when a research run registry cannot be built safely."""


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _stable_hash(payload: dict[str, Any]) -> str:
    return sha256(_json_dumps(payload).encode("utf-8")).hexdigest()


def assert_research_only_payload(payload: dict[str, Any], *, name: str) -> None:
    """Block registry writes when a payload is not explicitly research-only."""
    if not isinstance(payload, dict):
        raise ResearchRunRegistryError(f"{name} must be a dictionary.")

    if payload.get("app_mode") != "INTERACTIVE_RESEARCH_ONLY":
        raise ResearchRunRegistryError(f"{name} is not INTERACTIVE_RESEARCH_ONLY.")

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
            raise ResearchRunRegistryError(f"{name} has unsafe flag {flag}=True.")


def build_research_run_registry_entry(
    *,
    bundle_metadata: dict[str, Any],
    manifest: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Build one research-only registry entry from bundle metadata."""
    safe = build_safe_context()
    assert_research_only_payload(bundle_metadata, name="bundle_metadata")

    if manifest is not None:
        assert_research_only_payload(manifest, name="manifest")

    base_for_id = {
        "bundle_name": bundle_metadata.get("bundle_name"),
        "bundle_dir": bundle_metadata.get("bundle_dir"),
        "manifest_sha256": bundle_metadata.get("manifest_sha256"),
        "artifact_index_sha256": bundle_metadata.get("artifact_index_sha256"),
        "run_id": manifest.get("run_id") if manifest else bundle_metadata.get("run_id"),
    }

    entry = {
        "schema": RESEARCH_RUN_REGISTRY_ENTRY_SCHEMA_VERSION,
        "entry_id": _stable_hash(base_for_id),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": manifest.get("run_id") if manifest else bundle_metadata.get("run_id"),
        "bundle_name": bundle_metadata.get("bundle_name"),
        "bundle_dir": bundle_metadata.get("bundle_dir"),
        "bundle_schema": bundle_metadata.get("schema"),
        "bundle_quality_passed": bundle_metadata.get("bundle_quality_passed", True),
        "artifact_count": bundle_metadata.get("artifact_count", 0),
        "total_artifact_bytes": bundle_metadata.get("total_artifact_bytes", 0),
        "manifest_sha256": bundle_metadata.get("manifest_sha256"),
        "artifact_index_sha256": bundle_metadata.get("artifact_index_sha256"),
        "bundle_report_sha256": bundle_metadata.get("bundle_report_sha256"),
        "symbol": manifest.get("symbol") if manifest else bundle_metadata.get("symbol"),
        "interval": manifest.get("interval") if manifest else bundle_metadata.get("interval"),
        "source": manifest.get("source") if manifest else bundle_metadata.get("source"),
        "regime": manifest.get("regime") if manifest else bundle_metadata.get("regime"),
        "dql_score": manifest.get("dql_score") if manifest else bundle_metadata.get("dql_score"),
        "dataset_row_count": manifest.get("dataset_row_count") if manifest else bundle_metadata.get("dataset_row_count"),
        "tags": list(tags or []),
        "notes": notes,
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
        assert entry[flag] == safe[flag]

    return entry


def validate_registry_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return quality issues for registry entries."""
    issues: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    if not entries:
        return [
            {
                "code": "EMPTY_REGISTRY",
                "severity": "warning",
                "index": None,
                "message": "Research run registry has no entries.",
            }
        ]

    required = (
        "schema",
        "entry_id",
        "bundle_name",
        "bundle_dir",
        "research_allowed",
        "operational_decision_allowed",
        "app_mode",
    )

    for i, entry in enumerate(entries):
        missing = [key for key in required if key not in entry]
        if missing:
            issues.append(
                {
                    "code": "MISSING_REGISTRY_ENTRY_KEYS",
                    "severity": "error",
                    "index": i,
                    "message": f"Missing registry entry keys: {missing}",
                }
            )

        if entry.get("schema") != RESEARCH_RUN_REGISTRY_ENTRY_SCHEMA_VERSION:
            issues.append(
                {
                    "code": "INVALID_REGISTRY_ENTRY_SCHEMA",
                    "severity": "error",
                    "index": i,
                    "message": "Invalid registry entry schema.",
                }
            )

        if entry.get("operational_decision_allowed") is True:
            issues.append(
                {
                    "code": "OPERATIONAL_FLAG_TRUE",
                    "severity": "error",
                    "index": i,
                    "message": "Registry entry cannot allow operational decisions.",
                }
            )

        entry_id = entry.get("entry_id")
        if entry_id in seen_ids:
            issues.append(
                {
                    "code": "DUPLICATE_REGISTRY_ENTRY_ID",
                    "severity": "error",
                    "index": i,
                    "message": "Duplicate registry entry id.",
                }
            )
        if entry_id:
            seen_ids.add(entry_id)

    return issues


def build_research_run_registry(
    entries: list[dict[str, Any]],
    *,
    registry_name: str = "qrds-research-run-registry",
) -> dict[str, Any]:
    """Build a research-only registry from entries."""
    safe = build_safe_context()

    for entry in entries:
        assert_research_only_payload(entry, name="registry_entry")

    issues = validate_registry_entries(entries)
    error_count = sum(1 for issue in issues if issue["severity"] == "error")
    warning_count = sum(1 for issue in issues if issue["severity"] == "warning")

    registry = {
        "schema": RESEARCH_RUN_REGISTRY_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "registry_name": registry_name,
        "entry_count": len(entries),
        "registry_quality_passed": error_count == 0,
        "issue_summary": {
            "total_issues": len(issues),
            "error_count": error_count,
            "warning_count": warning_count,
        },
        "issues": issues,
        "entries": entries,
        "research_allowed": True,
        "operational_decision_allowed": False,
        "app_mode": "INTERACTIVE_RESEARCH_ONLY",
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "orders_generated": False,
        "real_capital_used": False,
    }

    registry["registry_hash"] = _stable_hash(
        {
            "schema": registry["schema"],
            "registry_name": registry["registry_name"],
            "entry_ids": [entry.get("entry_id") for entry in entries],
        }
    )

    for flag in (
        "api_key_present",
        "api_key_required",
        "account_connection_required",
        "orders_generated",
        "real_capital_used",
        "operational_decision_allowed",
    ):
        assert registry[flag] == safe[flag]

    return registry


def write_research_run_registry(registry: dict[str, Any], output_path: str | Path) -> str:
    """Write a research-only registry to disk and return the path."""
    assert_research_only_payload(registry, name="registry")

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as handle:
        json.dump(registry, handle, indent=2, sort_keys=True)
        handle.write("\n")

    return str(path)


def load_research_run_registry(path: str | Path) -> dict[str, Any]:
    """Load a research run registry from disk."""
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8") as handle:
        registry = json.load(handle)

    assert_research_only_payload(registry, name="registry")
    return registry


def build_research_run_registry_report(registry: dict[str, Any]) -> dict[str, Any]:
    """Build a quality report for a research run registry."""
    safe = build_safe_context()
    assert_research_only_payload(registry, name="registry")

    entries = registry.get("entries", [])
    issues = validate_registry_entries(entries)

    error_count = sum(1 for issue in issues if issue["severity"] == "error")
    warning_count = sum(1 for issue in issues if issue["severity"] == "warning")

    report = {
        "schema": "qrds.research_run_registry_report.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "registry_name": registry.get("registry_name"),
        "entry_count": len(entries),
        "registry_quality_passed": error_count == 0,
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
