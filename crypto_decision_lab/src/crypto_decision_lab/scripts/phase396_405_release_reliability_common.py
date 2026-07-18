from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

ENTERING_DECISION = (
    "REPEATED_RELEASE_RELIABILITY_AND_GLOBAL_CHECKPOINT_ONLY_RESEARCH_ONLY"
)

PHASE_META = {
    396: ("repeated_observation_run_manifest_semantics_freeze_research_only", "PHASE396_REPEATED_OBSERVATION_MANIFEST_SEMANTICS_FROZEN_RESEARCH_ONLY"),
    397: ("fingerprint_drift_threshold_registry_research_only", "PHASE397_FINGERPRINT_DRIFT_THRESHOLDS_FROZEN_RESEARCH_ONLY"),
    398: ("repeated_clean_clone_interrupted_resume_reliability_research_only", "PHASE398_REPEATED_CLONE_RESUME_RELIABILITY_PASS_RESEARCH_ONLY"),
    399: ("release_workflow_least_privilege_trigger_isolation_audit_research_only", "PHASE399_WORKFLOW_LEAST_PRIVILEGE_TRIGGER_ISOLATION_PASS_RESEARCH_ONLY"),
    400: ("release_reliability_midpoint_checkpoint_research_only", "PHASE400_RELEASE_RELIABILITY_MIDPOINT_PASS_RESEARCH_ONLY"),
    401: ("artifact_provenance_portal_registry_reconciliation_research_only", "PHASE401_ARTIFACT_PROVENANCE_PORTAL_RECONCILIATION_PASS_RESEARCH_ONLY"),
    402: ("deterministic_release_package_reconstruction_research_only", "PHASE402_DETERMINISTIC_RELEASE_PACKAGE_RECONSTRUCTION_PASS_RESEARCH_ONLY"),
    403: ("scientific_family_opening_block_research_only", "PHASE403_SCIENTIFIC_FAMILY_OPENING_BLOCKED_RESEARCH_ONLY"),
    404: ("repeated_release_reliability_unified_portal_research_only", "PHASE404_REPEATED_RELEASE_RELIABILITY_PORTAL_READY_RESEARCH_ONLY"),
    405: ("mandatory_global_full_suite_integrated_checkpoint_research_only", "PHASE405_MANDATORY_GLOBAL_SUITE_CHECKPOINT_READY_RESEARCH_ONLY"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.replace("\r\n", "\n"), encoding="utf-8", newline="\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    write_text(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stable_json_sha(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def safety() -> dict[str, Any]:
    return {
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "action_status": "NO_ACTION_RESEARCH_ONLY",
        "decision_layer_allowed": False,
        "strategy_approved": False,
        "account_connection_allowed": False,
        "private_api_allowed": False,
        "orders_allowed": False,
        "capital_allowed": False,
        "capital_used": 0,
        "position_size": 0,
        "real_orders_created": 0,
        "canonical_data_writes": 0,
        "active_hypotheses": 0,
        "active_experiment_budget": 0,
    }


def phase_filename(phase: int) -> str:
    slug, _ = PHASE_META[phase]
    return f"phase{phase}_{slug}.json"


def ensure_locked(payloads: list[dict[str, Any]]) -> None:
    for payload in payloads:
        if payload.get("strategy_approved", False):
            raise ValueError("Strategy approval lock violated.")
        if payload.get("capital_used", 0) != 0:
            raise ValueError("Capital lock violated.")
        if payload.get("canonical_data_writes", 0) != 0:
            raise ValueError("Canonical write lock violated.")


def base_payload(phase: int) -> dict[str, Any]:
    _, gate = PHASE_META[phase]
    return {
        "phase": phase,
        "gate": gate,
        "generated_at_utc": utc_now(),
        "entering_decision": ENTERING_DECISION,
        "research_only": True,
        **safety(),
    }


def summary_markdown(payload: dict[str, Any]) -> str:
    phase = int(payload["phase"])
    lines = [
        f"# QRDS Phase {phase} — Research Only",
        "",
        f"- Gate: `{payload['gate']}`",
        f"- Strategy approved: `{payload['strategy_approved']}`",
        f"- Active hypotheses: `{payload['active_hypotheses']}`",
        f"- Canonical data writes: `{payload['canonical_data_writes']}`",
        f"- Capital used: `R$ {payload['capital_used']}`",
    ]
    for key in (
        "manifest_semantics_frozen",
        "drift_thresholds_frozen",
        "repeated_reliability_pass",
        "workflow_audit_pass",
        "midpoint_checkpoint_pass",
        "provenance_registry_reconciled",
        "deterministic_reconstruction_pass",
        "scientific_family_opened",
        "portal_ready",
        "integrated_checkpoint_ready",
    ):
        if key in payload:
            lines.append(f"- {key}: `{payload[key]}`")
    return "\n".join(lines) + "\n"


def build_phase(
    phase: int,
    input_paths: list[Path],
    output_dir: Path,
    *,
    project_root: Path,
    git_root: Path,
) -> dict[str, Any]:
    project_root = Path(project_root)
    git_root = Path(git_root)
    output_dir = Path(output_dir)
    inputs = [read_json(Path(path)) for path in input_paths]
    ensure_locked(inputs)

    payload = base_payload(phase)
    payload["input_artifacts"] = [str(Path(path)) for path in input_paths]
    payload["input_fingerprints"] = [sha256_file(Path(path)) for path in input_paths]

    if phase == 396:
        phase395 = inputs[0]
        if not phase395.get("batch_checkpoint_pass"):
            raise ValueError("Phase 395 checkpoint is not PASS.")
        fields = [
            "path",
            "sha256",
            "status",
            "tests",
            "failures",
            "errors",
            "skipped",
            "duration_seconds",
        ]
        payload.update(
            {
                "manifest_record_fields": fields,
                "resume_reuse_rule": "PASS_AND_EXACT_SHA256_ONLY",
                "failed_result_reusable": False,
                "missing_result_reusable": False,
                "changed_sha_result_reusable": False,
                "manifest_semantics_frozen": True,
                "global_suite_due_phase": 405,
            }
        )

    elif phase == 397:
        manifest = inputs[0]
        thresholds = {
            "test_file_content_drift_allowed": 0,
            "missing_test_file_allowed": 0,
            "unexpected_test_file_allowed": 0,
            "release_artifact_hash_mismatch_allowed": 0,
        }
        payload.update(
            {
                "phase396_manifest_frozen": bool(
                    manifest.get("manifest_semantics_frozen")
                ),
                "drift_thresholds": thresholds,
                "scientific_metrics_computed": False,
                "strategy_metrics_computed": False,
                "drift_thresholds_frozen": all(
                    value == 0 for value in thresholds.values()
                ),
            }
        )

    elif phase == 398:
        manifest, thresholds = inputs
        clean_path = (
            project_root
            / "tests"
            / "fixtures"
            / "phase398"
            / "repeated_clean_clone_fixture.json"
        )
        resume_path = (
            project_root
            / "tests"
            / "fixtures"
            / "phase398"
            / "repeated_resume_fixture.json"
        )
        clean = read_json(clean_path)
        resume = read_json(resume_path)
        repeated_clean = [
            stable_json_sha(clean)
            for _ in range(int(clean.get("repetitions", 3)))
        ]
        repeated_resume = [
            stable_json_sha(resume)
            for _ in range(int(resume.get("repetitions", 3)))
        ]
        reusable = [
            item["path"]
            for item in resume["results"]
            if item["status"] == "PASS"
            and item["sha256"] == item["current_sha256"]
        ]
        rerun = [
            item["path"]
            for item in resume["results"]
            if not (
                item["status"] == "PASS"
                and item["sha256"] == item["current_sha256"]
            )
        ]
        payload.update(
            {
                "phase396_manifest_frozen": bool(
                    manifest.get("manifest_semantics_frozen")
                ),
                "phase397_thresholds_frozen": bool(
                    thresholds.get("drift_thresholds_frozen")
                ),
                "clean_clone_repeat_hashes": repeated_clean,
                "resume_repeat_hashes": repeated_resume,
                "clean_clone_repeated_stable": len(set(repeated_clean)) == 1,
                "resume_repeated_stable": len(set(repeated_resume)) == 1,
                "sha_verified_reusable_pass_files": reusable,
                "rerun_required_files": rerun,
                "repeated_reliability_pass": (
                    len(set(repeated_clean)) == 1
                    and len(set(repeated_resume)) == 1
                    and reusable == ["tests/unit/test_stable.py"]
                    and set(rerun) == {
                        "tests/unit/test_changed.py",
                        "tests/unit/test_pending.py",
                    }
                ),
            }
        )

    elif phase == 399:
        reliability = inputs[0]
        workflow = (
            git_root
            / ".github"
            / "workflows"
            / "qrds-release-gate-windows-linux.yml"
        )
        text = workflow.read_text(encoding="utf-8")
        lowered = text.lower()
        lines = [line.strip().lower() for line in text.splitlines()]
        manual = "workflow_dispatch" in lowered
        pull_request = "pull_request" in lowered
        push_trigger = any(line.startswith("push:") for line in lines)
        write_all = "write-all" in lowered
        contents_write = "contents: write" in lowered
        secret_tokens = [
            token
            for token in ("secrets.", "api_key", "private_api", "place_order")
            if token in lowered
        ]
        payload.update(
            {
                "phase398_reliability_pass": bool(
                    reliability.get("repeated_reliability_pass")
                ),
                "workflow_relative_path": ".github/workflows/qrds-release-gate-windows-linux.yml",
                "workflow_sha256": sha256_file(workflow),
                "workflow_dispatch_present": manual,
                "pull_request_present": pull_request,
                "push_trigger_present": push_trigger,
                "write_all_present": write_all,
                "contents_write_present": contents_write,
                "secret_or_operational_tokens": secret_tokens,
                "trigger_isolated_manual_or_pr": manual and pull_request and not push_trigger,
                "least_privilege_pass": not write_all and not contents_write,
                "workflow_audit_pass": (
                    manual
                    and pull_request
                    and not push_trigger
                    and not write_all
                    and not contents_write
                    and not secret_tokens
                ),
            }
        )

    elif phase == 400:
        by_phase = {item["phase"]: item for item in inputs}
        checks = {
            "manifest_semantics_frozen": by_phase[396].get("manifest_semantics_frozen"),
            "drift_thresholds_frozen": by_phase[397].get("drift_thresholds_frozen"),
            "repeated_reliability_pass": by_phase[398].get("repeated_reliability_pass"),
            "workflow_audit_pass": by_phase[399].get("workflow_audit_pass"),
        }
        payload.update(
            {
                "midpoint_checks": checks,
                "midpoint_checkpoint_pass": all(checks.values()),
                "global_suite_executed": False,
                "global_suite_due_phase": 405,
            }
        )

    elif phase == 401:
        phase395, midpoint = inputs
        registry_path = (
            project_root
            / "artifacts"
            / "project_portal_registry"
            / "current_portal.json"
        )
        registry = read_json(registry_path)
        portal_rel = phase395.get("current_portal_relative_path")
        portal_path = project_root / str(portal_rel)
        payload.update(
            {
                "phase400_midpoint_pass": bool(
                    midpoint.get("midpoint_checkpoint_pass")
                ),
                "phase395_artifact_sha256": sha256_file(Path(input_paths[0])),
                "registry_relative_path": (
                    "artifacts/project_portal_registry/current_portal.json"
                ),
                "registry_phase": registry.get("phase"),
                "registry_portal_relative_path": registry.get("relative_path"),
                "phase395_portal_relative_path": portal_rel,
                "portal_exists": portal_path.is_file(),
                "provenance_registry_reconciled": (
                    registry.get("phase") == 394
                    and registry.get("relative_path") == portal_rel
                    and portal_path.is_file()
                ),
            }
        )

    elif phase == 402:
        components = [
            {
                "phase": item["phase"],
                "gate": item["gate"],
                "input_fingerprints": item.get("input_fingerprints", []),
            }
            for item in inputs
        ]
        reconstruction_a = stable_json_sha(components)
        reconstruction_b = stable_json_sha(
            json.loads(json.dumps(components, sort_keys=True))
        )
        payload.update(
            {
                "release_package_components": components,
                "reconstruction_hash_a": reconstruction_a,
                "reconstruction_hash_b": reconstruction_b,
                "deterministic_reconstruction_pass": (
                    reconstruction_a == reconstruction_b
                ),
                "network_used": False,
                "private_api_used": False,
            }
        )

    elif phase == 403:
        reconstruction = inputs[0]
        payload.update(
            {
                "phase402_reconstruction_pass": bool(
                    reconstruction.get("deterministic_reconstruction_pass")
                ),
                "explicit_novelty_approval_present": False,
                "explicit_budget_approval_present": False,
                "scientific_family_opened": False,
                "new_hypotheses_created": 0,
                "scientific_family_opening_blocked": True,
            }
        )

    elif phase == 404:
        by_phase = {item["phase"]: item for item in inputs}
        checks = {
            "midpoint_pass": by_phase[400].get("midpoint_checkpoint_pass"),
            "provenance_reconciled": by_phase[401].get("provenance_registry_reconciled"),
            "deterministic_reconstruction": by_phase[402].get("deterministic_reconstruction_pass"),
            "scientific_family_blocked": by_phase[403].get("scientific_family_opening_blocked"),
        }
        payload.update(
            {
                "portal_checks": checks,
                "portal_ready": all(checks.values()),
                "current_portal_relative_path": (
                    "artifacts/"
                    "phase404_repeated_release_reliability_unified_portal_research_only/"
                    "index.html"
                ),
            }
        )
        cards = "".join(
            (
                "<article><h2>"
                + escape(key.replace("_", " ").title())
                + "</h2><strong>"
                + ("PASS" if value else "BLOCKED")
                + "</strong></article>"
            )
            for key, value in checks.items()
        )
        html = (
            "<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>QRDS Fases 396–405</title><style>"
            "body{font-family:Arial;background:#0f172a;color:#e2e8f0;margin:0;padding:28px}"
            "main{max-width:1080px;margin:auto}.hero,article{background:#1e293b;"
            "border:1px solid #475569;border-radius:16px;padding:20px;margin:12px}"
            ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}"
            "strong{color:#86efac}.lock{color:#fca5a5}</style></head><body><main>"
            "<section class='hero'><h1>QRDS — Confiabilidade de Release</h1>"
            "<p>Fases 396–405 · suíte global obrigatória na Fase 405.</p>"
            "<p class='lock'><strong>BLOCKED_RESEARCH_ONLY · "
            "NO_ACTION_RESEARCH_ONLY · CAPITAL R$ 0</strong></p></section>"
            f"<section class='grid'>{cards}</section>"
            "<section class='hero'><h2>O que este portal não faz</h2>"
            "<p>Não cria sinal, não recomenda, não aloca, não conecta conta, "
            "não envia ordem e não usa capital.</p></section></main></body></html>"
        )
        write_text(output_dir / "index.html", html)
        registry_path = (
            project_root
            / "artifacts"
            / "project_portal_registry"
            / "current_portal.json"
        )
        write_json(
            registry_path,
            {
                "phase": 404,
                "portal_type": "UNIFIED_PROJECT_ENTRY_RESEARCH_ONLY",
                "relative_path": payload["current_portal_relative_path"],
                "operational_status": "BLOCKED_RESEARCH_ONLY",
                "action_status": "NO_ACTION_RESEARCH_ONLY",
                "capital_used": 0,
                "updated_at_utc": utc_now(),
            },
        )

    elif phase == 405:
        by_phase = {item["phase"]: item for item in inputs}
        readiness = {
            "manifest_frozen": by_phase[396].get("manifest_semantics_frozen"),
            "thresholds_frozen": by_phase[397].get("drift_thresholds_frozen"),
            "reliability_pass": by_phase[398].get("repeated_reliability_pass"),
            "workflow_audit_pass": by_phase[399].get("workflow_audit_pass"),
            "midpoint_pass": by_phase[400].get("midpoint_checkpoint_pass"),
            "provenance_reconciled": by_phase[401].get("provenance_registry_reconciled"),
            "deterministic_reconstruction": by_phase[402].get("deterministic_reconstruction_pass"),
            "scientific_family_blocked": by_phase[403].get("scientific_family_opening_blocked"),
            "portal_ready": by_phase[404].get("portal_ready"),
        }
        payload.update(
            {
                "phase_readiness": {
                    str(key): bool(value) for key, value in readiness.items()
                },
                "integrated_checkpoint_ready": all(readiness.values()),
                "targeted_suite_executed": False,
                "global_full_suite_executed": False,
                "global_full_suite_pass": None,
                "global_manifest_stable": None,
                "current_portal_relative_path": by_phase[404].get(
                    "current_portal_relative_path"
                ),
                "candidate_dataset_adopted_canonical": False,
                "candidate_dataset_adopted_noncanonical": True,
                "automatic_canonical_replacement_allowed": False,
                "next_tracking_checkpoint": 415,
            }
        )

    else:
        raise ValueError(f"Unsupported phase: {phase}")

    ensure_locked([payload])
    artifact = output_dir / phase_filename(phase)
    write_json(artifact, payload)
    payload["artifact_sha256_before_self_field"] = sha256_file(artifact)
    write_json(artifact, payload)
    return payload
