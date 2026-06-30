"""Research-only run bundle builder.

Offline only.
No API key.
No account connection.
No orders.
No real capital.

A bundle is an auditable local package for one research run:
- manifest.json
- artifact_index.json
- copied export artifacts
- SHA-256 hashes
- byte counts

The bundle is a research artifact, not a trading signal.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from crypto_decision_lab.safety.gates import build_safe_context

RESEARCH_RUN_BUNDLE_SCHEMA_VERSION = "qrds.research_run_bundle.v1"
RESEARCH_ARTIFACT_INDEX_SCHEMA_VERSION = "qrds.research_artifact_index.v1"


class ResearchRunBundleError(ValueError):
    """Raised when a research run bundle cannot be built safely."""


def compute_sha256(path: str | Path) -> str:
    """Compute a deterministic SHA-256 hash for a local file."""
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise ResearchRunBundleError(f"Cannot hash missing file: {file_path}")

    digest = sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def _assert_research_only_dict(payload: dict[str, Any], *, name: str) -> None:
    if not isinstance(payload, dict):
        raise ResearchRunBundleError(f"{name} must be a dictionary.")

    if payload.get("app_mode") != "INTERACTIVE_RESEARCH_ONLY":
        raise ResearchRunBundleError(f"{name} is not INTERACTIVE_RESEARCH_ONLY.")

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
            raise ResearchRunBundleError(f"{name} has unsafe flag {flag}=True.")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def build_research_artifact_index(
    *,
    bundle_dir: str | Path,
    artifact_paths: list[str | Path],
) -> dict[str, Any]:
    """Build an index for files copied into a research bundle."""
    safe = build_safe_context()
    bundle_path = Path(bundle_dir)

    artifacts: list[dict[str, Any]] = []
    for artifact in artifact_paths:
        source_path = Path(artifact)
        if not source_path.exists() or not source_path.is_file():
            raise ResearchRunBundleError(f"Artifact does not exist: {source_path}")

        relative_name = source_path.name
        destination_path = bundle_path / "artifacts" / relative_name
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)

        artifacts.append(
            {
                "name": relative_name,
                "relative_path": str(destination_path.relative_to(bundle_path)),
                "bytes": destination_path.stat().st_size,
                "sha256": compute_sha256(destination_path),
            }
        )

    index = {
        "schema": RESEARCH_ARTIFACT_INDEX_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
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
        assert index[flag] == safe[flag]

    return index


def build_research_run_bundle(
    *,
    manifest: dict[str, Any],
    artifact_paths: list[str | Path],
    output_dir: str | Path,
    bundle_name: str,
) -> dict[str, Any]:
    """Create a local research-only bundle and return its metadata."""
    safe = build_safe_context()
    _assert_research_only_dict(manifest, name="manifest")

    if not bundle_name or "/" in bundle_name or "\\" in bundle_name:
        raise ResearchRunBundleError("bundle_name must be a simple folder name.")

    bundle_dir = Path(output_dir) / bundle_name
    bundle_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = bundle_dir / "manifest.json"
    _write_json(manifest_path, manifest)

    artifact_index = build_research_artifact_index(
        bundle_dir=bundle_dir,
        artifact_paths=artifact_paths,
    )

    artifact_index_path = bundle_dir / "artifact_index.json"
    _write_json(artifact_index_path, artifact_index)

    bundle = {
        "schema": RESEARCH_RUN_BUNDLE_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bundle_name": bundle_name,
        "bundle_dir": str(bundle_dir),
        "manifest_path": str(manifest_path),
        "manifest_sha256": compute_sha256(manifest_path),
        "artifact_index_path": str(artifact_index_path),
        "artifact_index_sha256": compute_sha256(artifact_index_path),
        "artifact_count": artifact_index["artifact_count"],
        "total_artifact_bytes": sum(item["bytes"] for item in artifact_index["artifacts"]),
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
        assert bundle[flag] == safe[flag]

    bundle_report_path = bundle_dir / "bundle_report.json"
    _write_json(bundle_report_path, bundle)
    bundle["bundle_report_path"] = str(bundle_report_path)
    bundle["bundle_report_sha256"] = compute_sha256(bundle_report_path)

    return bundle


def validate_research_bundle(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    """Return issues found in a research bundle metadata object."""
    issues: list[dict[str, Any]] = []

    required = (
        "schema",
        "bundle_name",
        "bundle_dir",
        "manifest_path",
        "artifact_index_path",
        "artifact_count",
        "research_allowed",
        "operational_decision_allowed",
        "app_mode",
    )

    missing = [key for key in required if key not in bundle]
    if missing:
        issues.append(
            {
                "code": "MISSING_BUNDLE_KEYS",
                "severity": "error",
                "index": None,
                "message": f"Missing bundle keys: {missing}",
            }
        )

    if bundle.get("schema") != RESEARCH_RUN_BUNDLE_SCHEMA_VERSION:
        issues.append(
            {
                "code": "INVALID_BUNDLE_SCHEMA",
                "severity": "error",
                "index": None,
                "message": "Invalid research bundle schema.",
            }
        )

    if bundle.get("operational_decision_allowed") is True:
        issues.append(
            {
                "code": "OPERATIONAL_FLAG_TRUE",
                "severity": "error",
                "index": None,
                "message": "Research bundle cannot allow operational decisions.",
            }
        )

    for path_key in ("manifest_path", "artifact_index_path"):
        value = bundle.get(path_key)
        if value and not Path(value).exists():
            issues.append(
                {
                    "code": "MISSING_BUNDLE_FILE",
                    "severity": "error",
                    "index": None,
                    "message": f"Missing bundle file referenced by {path_key}.",
                }
            )

    return issues


def build_research_run_bundle_report(bundle: dict[str, Any]) -> dict[str, Any]:
    """Build a quality report for a research run bundle."""
    safe = build_safe_context()
    issues = validate_research_bundle(bundle)

    error_count = sum(1 for issue in issues if issue["severity"] == "error")
    warning_count = sum(1 for issue in issues if issue["severity"] == "warning")

    report = {
        "schema": "qrds.research_run_bundle_report.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bundle_name": bundle.get("bundle_name"),
        "bundle_dir": bundle.get("bundle_dir"),
        "bundle_quality_passed": error_count == 0,
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
