from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PHASE_META = {
    416: (
        "certificate_retention_evidence_aging_policy_research_only",
        "PHASE416_CERTIFICATE_RETENTION_POLICY_SEALED_RESEARCH_ONLY",
    ),
    417: (
        "artifact_freshness_audit_research_only",
        "PHASE417_ARTIFACT_FRESHNESS_AUDIT_PASS_RESEARCH_ONLY",
    ),
    418: (
        "deterministic_reproducibility_spotcheck_research_only",
        "PHASE418_REPRODUCIBILITY_SPOTCHECK_PASS_RESEARCH_ONLY",
    ),
    419: (
        "documentation_tracking_drift_audit_research_only",
        "PHASE419_DOCUMENTATION_DRIFT_AUDIT_PASS_RESEARCH_ONLY",
    ),
    420: (
        "reliability_retention_midpoint_checkpoint_research_only",
        "PHASE420_RELIABILITY_RETENTION_MIDPOINT_PASS_RESEARCH_ONLY",
    ),
    421: (
        "readonly_governance_evidence_index_research_only",
        "PHASE421_GOVERNANCE_EVIDENCE_INDEX_READY_RESEARCH_ONLY",
    ),
    422: (
        "future_manual_scientific_approval_prerequisites_audit_research_only",
        "PHASE422_MANUAL_APPROVAL_PREREQUISITES_AUDITED_RESEARCH_ONLY",
    ),
    423: (
        "approval_absence_scientific_family_closed_guard_research_only",
        "PHASE423_APPROVAL_ABSENT_FAMILY_CLOSED_RESEARCH_ONLY",
    ),
    424: (
        "reliability_governance_unified_portal_research_only",
        "PHASE424_RELIABILITY_GOVERNANCE_PORTAL_READY_RESEARCH_ONLY",
    ),
    425: (
        "reliability_governance_integrated_checkpoint_research_only",
        "PHASE425_INTEGRATED_CHECKPOINT_READY_RESEARCH_ONLY",
    ),
}

LOCKS = {
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "action_status": "NO_ACTION_RESEARCH_ONLY",
    "decision_layer_allowed": False,
    "canonical_data_writes": 0,
    "orders_allowed": False,
    "capital_allowed": False,
    "position_size": 0,
    "capital_used": 0,
    "real_orders_created": 0,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        content.replace("\r\n", "\n").rstrip() + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_json(path: Path, payload: Any) -> None:
    write_text(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_sha(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def assert_locked(payload: dict[str, Any]) -> None:
    locks = payload.get("locks")
    if not isinstance(locks, dict):
        raise ValueError("Input artifact has no locks object")

    mismatches = {
        key: (locks.get(key), expected)
        for key, expected in LOCKS.items()
        if locks.get(key) != expected
    }
    if mismatches:
        raise ValueError(f"Research-only lock mismatch: {mismatches}")

    if payload.get("strategy_approved") is not False:
        raise ValueError("strategy_approved must remain False")


def base_payload(
    phase: int,
    inputs: list[tuple[Path, dict[str, Any]]],
) -> dict[str, Any]:
    slug, gate = PHASE_META[phase]
    return {
        "schema_version": "1.0.0",
        "phase": phase,
        "slug": slug,
        "generated_at_utc": utc_now(),
        "gate": gate,
        "phase_status": "READY_RESEARCH_ONLY",
        "batch_window": "416-425",
        "entering_decision": (
            "RELIABILITY_RETENTION_AND_GOVERNANCE_EVIDENCE_"
            "ONLY_RESEARCH_ONLY"
        ),
        "locks": dict(LOCKS),
        "strategy_approved": False,
        "scientific_family_opened": False,
        "new_hypotheses_created": 0,
        "trading_signal_generated": False,
        "recommendation_generated": False,
        "allocation_generated": False,
        "private_api_used": False,
        "network_used": False,
        "capital_used": 0,
        "position_size": 0,
        "real_orders_created": 0,
        "canonical_data_writes": 0,
        "inputs": [
            {
                "phase": payload.get("phase"),
                "path": path.as_posix(),
                "sha256": sha256_file(path),
                "gate": payload.get("gate"),
            }
            for path, payload in inputs
        ],
    }


def build_phase(
    phase: int,
    input_paths: list[Path],
    output_dir: Path,
    *,
    project_root: Path,
    git_root: Path,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if phase not in PHASE_META:
        raise ValueError(f"Unsupported phase: {phase}")

    context = dict(context or {})
    loaded = [(path, read_json(path)) for path in input_paths]
    for _, payload in loaded:
        assert_locked(payload)

    payloads = [payload for _, payload in loaded]
    result = base_payload(phase, loaded)

    if phase == 416:
        source = payloads[0]
        if source.get("integrated_checkpoint_ready") is not True:
            raise ValueError("Phase 415 checkpoint is not ready")
        policy = {
            "certificate_retention_mode": "IMMUTABLE_SHA256_REFERENCE",
            "minimum_retention_days": 3650,
            "aging_observation_only": True,
            "automatic_expiration_allowed": False,
            "automatic_deletion_allowed": False,
            "manual_review_required": True,
            "source_phase415_sha256": sha256_file(loaded[0][0]),
        }
        result.update(
            {
                "retention_policy": policy,
                "retention_policy_sha256": stable_sha(policy),
                "retention_policy_sealed": True,
            }
        )

    elif phase == 417:
        required_paths = [
            project_root
            / "artifacts"
            / "phase405_mandatory_global_full_suite_integrated_checkpoint_research_only"
            / "phase405_mandatory_global_full_suite_integrated_checkpoint_research_only.json",
            project_root
            / "artifacts"
            / "phase415_post_global_suite_integrated_tracking_checkpoint_research_only"
            / "phase415_post_global_suite_integrated_tracking_checkpoint_research_only.json",
            project_root
            / "docs"
            / "reports"
            / "project_tracking"
            / "QRDS_INTEGRATED_TEST_MILESTONE_406_415.md",
            project_root
            / "docs"
            / "reports"
            / "project_tracking"
            / "qrds_progress_snapshot_phase415.json",
        ]
        evidence = {
            path.relative_to(project_root).as_posix(): {
                "exists": path.is_file(),
                "sha256": sha256_file(path) if path.is_file() else None,
            }
            for path in required_paths
        }
        result.update(
            {
                "freshness_evidence": evidence,
                "freshness_audit_pass": all(
                    item["exists"] and bool(item["sha256"])
                    for item in evidence.values()
                ),
                "evidence_mutated": False,
                "aging_policy_observation_only": True,
            }
        )
        if not result["freshness_audit_pass"]:
            raise ValueError("Artifact freshness audit failed")

    elif phase == 418:
        source = {
            "phase415_sha256": sha256_file(loaded[0][0]),
            "retention_policy_sha256": payloads[1].get(
                "retention_policy_sha256"
            ),
            "freshness_evidence": payloads[2].get("freshness_evidence"),
        }
        first = stable_sha(source)
        second = stable_sha(
            json.loads(
                json.dumps(source, ensure_ascii=False, sort_keys=True)
            )
        )
        result.update(
            {
                "spotcheck_hash_a": first,
                "spotcheck_hash_b": second,
                "reproducibility_spotcheck_pass": first == second,
                "source_evidence_mutated": False,
            }
        )
        if not result["reproducibility_spotcheck_pass"]:
            raise ValueError("Reproducibility spot-check failed")

    elif phase == 419:
        required_markers = {
            (
                project_root
                / "docs"
                / "reports"
                / "project_tracking"
                / "QRDS_ROADMAP_416_425_RESEARCH_ONLY.md"
            ): "416",
            (
                project_root
                / "docs"
                / "reports"
                / "project_tracking"
                / "QRDS_PROGRESS_TABLE_BY_TENS_PHASE415.md"
            ): "406",
            (
                project_root
                / "docs"
                / "reports"
                / "project_tracking"
                / "QRDS_MASTER_PROGRESS_BY_TENS_PHASE415.md"
            ): "415",
        }
        checks: dict[str, bool] = {}
        for path, marker in required_markers.items():
            present = path.is_file()
            contains = (
                marker in path.read_text(encoding="utf-8-sig")
                if present
                else False
            )
            checks[path.relative_to(project_root).as_posix()] = (
                present and contains
            )
        result.update(
            {
                "documentation_checks": checks,
                "documentation_tracking_drift_audit_pass": all(
                    checks.values()
                ),
                "automatic_document_rewrite_performed": False,
            }
        )
        if not result["documentation_tracking_drift_audit_pass"]:
            raise ValueError("Documentation/tracking drift audit failed")

    elif phase == 420:
        checks = {
            "retention_policy": payloads[0].get(
                "retention_policy_sealed"
            ) is True,
            "freshness": payloads[1].get("freshness_audit_pass") is True,
            "reproducibility": payloads[2].get(
                "reproducibility_spotcheck_pass"
            ) is True,
            "documentation": payloads[3].get(
                "documentation_tracking_drift_audit_pass"
            ) is True,
        }
        result.update(
            {
                "midpoint_checks": checks,
                "midpoint_checkpoint_pass": all(checks.values()),
                "global_suite_required_at_phase425": True,
                "global_suite_reason": (
                    "TEST_MANIFEST_MATERIAL_CHANGE_NEW_PHASE_TEST_FILES"
                ),
            }
        )
        if not result["midpoint_checkpoint_pass"]:
            raise ValueError("Phase 420 midpoint failed")

    elif phase == 421:
        index = {
            "mode": "READ_ONLY",
            "midpoint_gate": payloads[0].get("gate"),
            "midpoint_pass": payloads[0].get(
                "midpoint_checkpoint_pass"
            ),
            "automatic_mutation_allowed": False,
            "decision_authority_granted": False,
            "capital_authority_granted": False,
        }
        result.update(
            {
                "governance_evidence_index": index,
                "governance_evidence_index_sha256": stable_sha(index),
                "governance_evidence_index_ready": True,
            }
        )
        write_json(output_dir / "governance_evidence_index.json", index)

    elif phase == 422:
        prerequisites = {
            "midpoint_pass": payloads[0].get(
                "midpoint_checkpoint_pass"
            ) is True,
            "governance_index_ready": payloads[1].get(
                "governance_evidence_index_ready"
            ) is True,
            "manual_approval_document_present": False,
            "explicit_user_approval_present": False,
            "strategy_approved": False,
        }
        result.update(
            {
                "approval_prerequisites": prerequisites,
                "approval_prerequisites_audited": True,
                "approval_prerequisites_satisfied": False,
                "approval_granted": False,
                "scientific_family_opening_allowed": False,
            }
        )

    elif phase == 423:
        result.update(
            {
                "approval_present": False,
                "approval_absence_verified": payloads[0].get(
                    "approval_granted"
                ) is False,
                "scientific_family_opening_blocked": True,
                "scientific_family_opened": False,
                "new_hypotheses_created": 0,
            }
        )
        if not result["approval_absence_verified"]:
            raise ValueError("Approval absence guard failed")

    elif phase == 424:
        checks = {
            "midpoint": payloads[0].get(
                "midpoint_checkpoint_pass"
            ) is True,
            "governance_index": payloads[1].get(
                "governance_evidence_index_ready"
            ) is True,
            "prerequisites_audited": payloads[2].get(
                "approval_prerequisites_audited"
            ) is True,
            "approval_absent": payloads[3].get(
                "approval_absence_verified"
            ) is True,
        }
        result.update(
            {
                "portal_checks": checks,
                "portal_ready": all(checks.values()),
                "portal_path": "index.html",
            }
        )
        if not result["portal_ready"]:
            raise ValueError("Phase 424 portal inputs failed")

        html = (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<title>QRDS Phase 424</title></head><body>"
            "<h1>Reliability Retention and Governance</h1>"
            "<p><strong>BLOCKED_RESEARCH_ONLY</strong></p>"
            "<p>NO_ACTION_RESEARCH_ONLY</p>"
            "<p>CAPITAL R$ 0</p><p>REAL ORDERS 0</p>"
            "<pre>"
            + json.dumps(checks, indent=2, sort_keys=True)
            + "</pre></body></html>"
        )
        write_text(output_dir / "index.html", html)

    elif phase == 425:
        checks = {
            str(number): payload.get("phase_status")
            == "READY_RESEARCH_ONLY"
            for number, payload in zip(range(416, 425), payloads)
        }
        result.update(
            {
                "integrated_phase_checks": checks,
                "integrated_checkpoint_ready": all(checks.values()),
                "targeted_suite_executed": False,
                "targeted_suite_pass": None,
                "global_full_suite_required": True,
                "global_full_suite_executed": False,
                "global_full_suite_pass": None,
                "global_suite_reason": (
                    "TEST_MANIFEST_MATERIAL_CHANGE_NEW_PHASE_TEST_FILES"
                ),
                "next_tracking_checkpoint": 435,
            }
        )
        if not result["integrated_checkpoint_ready"]:
            raise ValueError("Phase 425 integration failed")

    output_dir.mkdir(parents=True, exist_ok=True)
    slug, _ = PHASE_META[phase]
    artifact = output_dir / f"phase{phase}_{slug}.json"
    write_json(artifact, result)
    return result


def summary_markdown(payload: dict[str, Any]) -> str:
    selected = {
        key: value
        for key, value in payload.items()
        if key not in {"inputs", "locks", "generated_at_utc"}
    }
    return (
        f"# Phase {payload['phase']} — {payload['slug']}\n\n"
        "## Gate\n\n"
        f"```text\n{payload['gate']}\n```\n\n"
        "## Result\n\n"
        "```json\n"
        + json.dumps(
            selected,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n```\n\n"
        "## Permanent restrictions\n\n"
        "```text\n"
        "operational_status=BLOCKED_RESEARCH_ONLY\n"
        "action_status=NO_ACTION_RESEARCH_ONLY\n"
        "decision_layer_allowed=False\n"
        "strategy_approved=False\n"
        "scientific_family_opened=False\n"
        "capital_used=0\n"
        "real_orders_created=0\n"
        "canonical_data_writes=0\n"
        "```\n"
    )
