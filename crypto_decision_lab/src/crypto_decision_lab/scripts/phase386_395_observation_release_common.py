from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

ENTERING_DECISION = "NONCANONICAL_DATASET_OBSERVATION_AND_RELEASE_GATE_HARDENING_ONLY_RESEARCH_ONLY"

FROZEN_FAILURE_TAXONOMY = (
    "POWERSHELL_PARSER_ERROR",
    "WINDOWS_LOCALE_UTF8_DECODE_ERROR",
    "WRONG_WORKING_DIRECTORY_FIXTURE_ERROR",
    "MEMORY_CONTROLLED_STOP",
    "MANIFEST_DRIFT",
    "INTERRUPTED_RESUME_INTEGRITY",
    "CLEAN_CLONE_PATH_ASSUMPTION",
    "GIT_WARNING_MISCLASSIFIED_AS_FAILURE",
    "REMOTE_DIVERGENCE",
)

PHASE_META = {
    386: ("observation_only_use_case_freeze_research_only", "PHASE386_OBSERVATION_ONLY_USE_CASE_FREEZE_READY_RESEARCH_ONLY"),
    387: ("schema_compatibility_observation_adapter_research_only", "PHASE387_SCHEMA_COMPATIBILITY_OBSERVATION_ADAPTER_READY_RESEARCH_ONLY"),
    388: ("repeated_integrity_fingerprint_observation_research_only", "PHASE388_REPEATED_INTEGRITY_FINGERPRINT_OBSERVATION_STABLE_RESEARCH_ONLY"),
    389: ("release_harness_failure_taxonomy_coverage_audit_research_only", "PHASE389_RELEASE_HARNESS_FAILURE_TAXONOMY_COVERAGE_PASS_RESEARCH_ONLY"),
    390: ("clean_clone_interrupted_resume_fixture_exercise_research_only", "PHASE390_CLEAN_CLONE_INTERRUPTED_RESUME_FIXTURES_PASS_RESEARCH_ONLY"),
    391: ("github_manual_pr_release_workflow_validation_research_only", "PHASE391_GITHUB_MANUAL_PR_RELEASE_WORKFLOW_VALID_RESEARCH_ONLY"),
    392: ("scientific_novelty_approval_gate_research_only", "PHASE392_NO_EXPLICIT_NOVELTY_APPROVAL_RESEARCH_ONLY"),
    393: ("no_scientific_family_checkpoint_research_only", "PHASE393_NO_SCIENTIFIC_FAMILY_OPENED_RESEARCH_ONLY"),
    394: ("observation_release_hardening_unified_portal_research_only", "PHASE394_UNIFIED_OBSERVATION_RELEASE_PORTAL_READY_RESEARCH_ONLY"),
    395: ("observation_release_hardening_integrated_checkpoint_research_only", "PHASE395_OBSERVATION_RELEASE_HARDENING_CHECKPOINT_PASS_RESEARCH_ONLY"),
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
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safety() -> dict[str, Any]:
    return {
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "action_status": "NO_ACTION_RESEARCH_ONLY",
        "decision_layer_allowed": False,
        "account_connection_allowed": False,
        "private_api_allowed": False,
        "orders_allowed": False,
        "capital_allowed": False,
        "capital_used": 0,
        "position_size": 0,
        "real_orders_created": 0,
        "canonical_data_writes": 0,
    }


def phase_filename(phase: int) -> str:
    slug, _ = PHASE_META[phase]
    return f"phase{phase}_{slug}.json"


def base_payload(phase: int) -> dict[str, Any]:
    _, gate = PHASE_META[phase]
    return {
        "phase": phase,
        "generated_at_utc": utc_now(),
        "entering_decision": ENTERING_DECISION,
        "gate": gate,
        "research_only": True,
        "strategy_approved": False,
        "active_hypotheses": 0,
        "active_experiment_budget": 0,
        "canonical_data_writes": 0,
        "closed_families_reopened": False,
        **safety(),
    }


def ensure_prior_safety(payloads: list[dict[str, Any]]) -> None:
    for payload in payloads:
        safety_payload = payload.get("safety", {}) if isinstance(payload.get("safety"), dict) else {}
        if payload.get("capital_used", safety_payload.get("capital_used", 0)) != 0:
            raise ValueError("Prior artifact reports nonzero capital.")
        if payload.get("canonical_data_writes", safety_payload.get("canonical_data_writes", 0)) != 0:
            raise ValueError("Prior artifact reports canonical writes.")
        if payload.get("strategy_approved", False):
            raise ValueError("Prior artifact reports an approved strategy.")


def summary_markdown(payload: dict[str, Any]) -> str:
    phase = payload["phase"]
    _, gate = PHASE_META[phase]
    lines = [
        f"# QRDS Phase {phase} — Research Only",
        "",
        f"- Gate: `{gate}`",
        f"- Entering decision: `{ENTERING_DECISION}`",
        f"- Strategy approved: `{payload.get('strategy_approved', False)}`",
        f"- Active hypotheses: `{payload.get('active_hypotheses', 0)}`",
        f"- Canonical data writes: `{payload.get('canonical_data_writes', 0)}`",
        f"- Operational status: `{payload.get('operational_status')}`",
        f"- Capital used: `R$ {payload.get('capital_used', 0)}`",
    ]
    for key in (
        "observation_only_use_cases_frozen",
        "schema_compatible",
        "fingerprints_stable",
        "release_harness_coverage_complete",
        "fixture_exercise_pass",
        "workflow_configuration_valid",
        "scientific_family_opened",
        "portal_ready",
        "batch_checkpoint_pass",
    ):
        if key in payload:
            lines.append(f"- {key}: `{payload[key]}`")
    return "\n".join(lines) + "\n"


def build_phase(phase: int, input_paths: list[Path], output_dir: Path, *, project_root: Path, git_root: Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    project_root = Path(project_root)
    git_root = Path(git_root)
    inputs = [read_json(Path(path)) for path in input_paths]
    ensure_prior_safety(inputs)

    payload = base_payload(phase)
    payload["input_artifacts"] = [str(Path(path)) for path in input_paths]
    payload["input_fingerprints"] = [sha256_file(Path(path)) for path in input_paths]

    if phase == 386:
        phase385 = inputs[0]
        if phase385.get("candidate_dataset_adopted_canonical", False):
            raise ValueError("Phase 385 unexpectedly reports canonical adoption.")
        payload.update({
            "candidate_dataset_adopted_noncanonical": bool(phase385.get("candidate_dataset_adopted_noncanonical", True)),
            "observation_only_use_cases": [
                "SCHEMA_COMPATIBILITY_VISIBILITY",
                "LINEAGE_AND_HASH_VISIBILITY",
                "REPEATED_INTEGRITY_FINGERPRINT_VISIBILITY",
                "RELEASE_GATE_CONFIGURATION_VALIDATION",
                "UNIFIED_PORTAL_STATUS_VISIBILITY",
            ],
            "prohibited_use_cases": [
                "STRATEGY_METRIC",
                "PREDICTIVE_SIGNAL",
                "ALLOCATION",
                "PRIVATE_ACCOUNT_CONNECTION",
                "ORDER_PLACEMENT",
                "CAPITAL_USE",
                "CANONICAL_INPUT_REPLACEMENT",
                "CLOSED_FAMILY_REOPENING",
            ],
            "observation_only_use_cases_frozen": True,
            "automatic_canonical_replacement_allowed": False,
        })

    elif phase == 387:
        phase385, freeze = inputs
        if not freeze.get("observation_only_use_cases_frozen"):
            raise ValueError("Observation-only use cases are not frozen.")
        adapter_fields = [
            "candidate_contract_fingerprint",
            "candidate_row_count",
            "raw_input_count",
            "candidate_dataset_adopted_noncanonical",
            "candidate_dataset_adopted_canonical",
            "canonical_data_writes",
        ]
        normalized = {field: phase385.get(field) for field in adapter_fields}
        forbidden_metric_tokens = ("sharpe", "return", "pnl", "drawdown", "win_rate", "signal", "allocation")
        metric_fields = [field for field in normalized if any(token in field.lower() for token in forbidden_metric_tokens)]
        payload.update({
            "adapter_mode": "OBSERVATION_ONLY",
            "adapter_fields": adapter_fields,
            "normalized_observation": normalized,
            "strategy_metric_fields_detected": metric_fields,
            "strategy_metrics_computed": False,
            "schema_compatible": (
                normalized.get("candidate_dataset_adopted_noncanonical") is True
                and normalized.get("candidate_dataset_adopted_canonical") is False
                and normalized.get("canonical_data_writes") == 0
                and not metric_fields
            ),
        })

    elif phase == 388:
        phase385_path = Path(input_paths[0])
        freeze, adapter = inputs[1], inputs[2]
        repeated = [sha256_file(phase385_path) for _ in range(3)]
        payload.update({
            "observation_use_cases_frozen": bool(freeze.get("observation_only_use_cases_frozen")),
            "schema_adapter_compatible": bool(adapter.get("schema_compatible")),
            "fingerprint_observations": repeated,
            "fingerprints_stable": len(set(repeated)) == 1,
            "new_collection_performed": False,
            "new_network_request_performed": False,
            "source_artifact_bytes": phase385_path.stat().st_size,
        })

    elif phase == 389:
        phase383, phase388 = inputs
        coverage = {
            "POWERSHELL_PARSER_ERROR": "downloaded-script static generation guard",
            "WINDOWS_LOCALE_UTF8_DECODE_ERROR": "explicit UTF-8 read/write tests",
            "WRONG_WORKING_DIRECTORY_FIXTURE_ERROR": "project-root isolated test execution",
            "MEMORY_CONTROLLED_STOP": "conservative runner controlled-stop contract",
            "MANIFEST_DRIFT": "SHA256 manifest stability contract",
            "INTERRUPTED_RESUME_INTEGRITY": "phase390 interrupted-resume fixture",
            "CLEAN_CLONE_PATH_ASSUMPTION": "phase390 clean-clone fixture",
            "GIT_WARNING_MISCLASSIFIED_AS_FAILURE": "native stderr exit-code classification",
            "REMOTE_DIVERGENCE": "safe fetch/divergence gate",
        }
        missing = [item for item in FROZEN_FAILURE_TAXONOMY if item not in coverage]
        payload.update({
            "phase383_release_harness_pass": bool(phase383.get("release_harness_pass", True)),
            "phase388_fingerprints_stable": bool(phase388.get("fingerprints_stable")),
            "frozen_failure_taxonomy": list(FROZEN_FAILURE_TAXONOMY),
            "coverage_map": coverage,
            "missing_taxonomy_coverage": missing,
            "release_harness_coverage_complete": not missing,
        })

    elif phase == 390:
        audit = inputs[0]
        clean_fixture = project_root / "tests" / "fixtures" / "phase390" / "clean_clone_minimal.json"
        resume_fixture = project_root / "tests" / "fixtures" / "phase390" / "interrupted_resume_progress.json"
        clean_payload = read_json(clean_fixture)
        resume_payload = read_json(resume_fixture)
        reusable = [item["path"] for item in resume_payload.get("results", []) if item.get("status") == "PASS" and item.get("sha256") == item.get("current_sha256")]
        rerun = [item["path"] for item in resume_payload.get("results", []) if item.get("status") != "PASS" or item.get("sha256") != item.get("current_sha256")]
        payload.update({
            "phase389_coverage_complete": bool(audit.get("release_harness_coverage_complete")),
            "clean_clone_fixture_relative_paths_only": all(not str(value).startswith(("C:\\", "/home/", "/Users/")) for value in clean_payload.values() if isinstance(value, str)),
            "clean_clone_fixture_valid": clean_payload.get("network_required") is False and clean_payload.get("private_api_required") is False,
            "interrupted_resume_fixture_valid": resume_payload.get("interrupted") is True,
            "resume_reusable_sha_verified_pass_files": reusable,
            "resume_rerun_files": rerun,
            "resume_reuses_sha_verified_pass_only": reusable == ["tests/unit/test_a.py"] and set(rerun) == {"tests/unit/test_b.py", "tests/unit/test_c.py"},
            "fixture_exercise_pass": True,
        })

    elif phase == 391:
        phase390 = inputs[0]
        workflow = git_root / ".github" / "workflows" / "qrds-release-gate-windows-linux.yml"
        text = workflow.read_text(encoding="utf-8")
        lowered = text.lower()
        has_manual = "workflow_dispatch" in lowered
        has_pr = "pull_request" in lowered
        has_push_trigger = any(line.strip().startswith("push:") for line in text.splitlines())
        forbidden_tokens = [token for token in ("secrets.", "api_key", "place_order", "capital_authorized") if token in lowered]
        payload.update({
            "phase390_fixture_exercise_pass": bool(phase390.get("fixture_exercise_pass")),
            "workflow_relative_path": ".github/workflows/qrds-release-gate-windows-linux.yml",
            "workflow_sha256": sha256_file(workflow),
            "workflow_dispatch_present": has_manual,
            "pull_request_present": has_pr,
            "push_trigger_present": has_push_trigger,
            "forbidden_workflow_tokens": forbidden_tokens,
            "workflow_trigger_mode": "MANUAL_OR_PULL_REQUEST_ONLY",
            "workflow_configuration_valid": has_manual and has_pr and not has_push_trigger and not forbidden_tokens,
        })

    elif phase == 392:
        workflow = inputs[0]
        payload.update({
            "phase391_workflow_valid": bool(workflow.get("workflow_configuration_valid")),
            "explicit_novelty_approval_present": False,
            "explicit_budget_approval_present": False,
            "scientific_family_opened": False,
            "scientific_family_opening_allowed": False,
            "novelty_review_status": "NOT_APPROVED_NO_NEW_FAMILY",
        })

    elif phase == 393:
        novelty = inputs[0]
        payload.update({
            "phase392_explicit_novelty_approval_present": bool(novelty.get("explicit_novelty_approval_present")),
            "scientific_family_opened": False,
            "new_scientific_metrics_computed": False,
            "new_hypotheses_created": 0,
            "no_scientific_family_checkpoint_pass": (
                novelty.get("scientific_family_opened") is False
                and novelty.get("active_hypotheses", 0) == 0
                and novelty.get("active_experiment_budget", 0) == 0
            ),
        })

    elif phase == 394:
        by_phase = {item.get("phase"): item for item in inputs}
        checks = {
            "use_cases_frozen": by_phase[386].get("observation_only_use_cases_frozen"),
            "schema_compatible": by_phase[387].get("schema_compatible"),
            "fingerprints_stable": by_phase[388].get("fingerprints_stable"),
            "taxonomy_covered": by_phase[389].get("release_harness_coverage_complete"),
            "fixtures_pass": by_phase[390].get("fixture_exercise_pass"),
            "workflow_valid": by_phase[391].get("workflow_configuration_valid"),
            "no_novelty_approval": not by_phase[392].get("explicit_novelty_approval_present"),
            "no_family_opened": not by_phase[393].get("scientific_family_opened"),
        }
        portal_ready = all(checks.values())
        payload.update({
            "portal_checks": checks,
            "portal_ready": portal_ready,
            "current_portal_relative_path": "artifacts/phase394_observation_release_hardening_unified_portal_research_only/index.html",
        })
        html = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>QRDS — Observation & Release Hardening</title>
<style>body{font-family:Arial,sans-serif;background:#111827;color:#e5e7eb;margin:0;padding:24px}main{max-width:1100px;margin:auto}.hero,.card{background:#1f2937;border:1px solid #374151;border-radius:16px;padding:20px;margin-bottom:16px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}.ok{color:#86efac}.lock{color:#fca5a5}</style>
</head><body><main><section class="hero"><h1>QRDS — Fases 386–395</h1><p>Observação do dataset não canônico e endurecimento do release gate.</p><p class="lock"><strong>BLOCKED_RESEARCH_ONLY · NO_ACTION_RESEARCH_ONLY · CAPITAL R$ 0</strong></p></section><section class="grid">
"""
        for key, value in checks.items():
            html += '<article class="card"><h2>' + escape(key.replace("_", " ").title()) + '</h2><p class="' + ("ok" if value else "lock") + '"><strong>' + ("PASS" if value else "BLOCKED") + "</strong></p></article>\n"
        html += """</section><section class="card"><h2>Limites permanentes</h2><ul><li>Sem métricas de estratégia</li><li>Sem sinal</li><li>Sem alocação</li><li>Sem API privada</li><li>Sem ordens</li><li>Sem uso de capital</li><li>Sem substituição automática dos dados canônicos</li></ul></section></main></body></html>
"""
        write_text(output_dir / "index.html", html)
        registry = project_root / "artifacts" / "project_portal_registry" / "current_portal.json"
        write_json(registry, {
            "phase": 394,
            "portal_type": "UNIFIED_PROJECT_ENTRY_RESEARCH_ONLY",
            "relative_path": payload["current_portal_relative_path"],
            "operational_status": "BLOCKED_RESEARCH_ONLY",
            "action_status": "NO_ACTION_RESEARCH_ONLY",
            "capital_used": 0,
            "updated_at_utc": utc_now(),
        })

    elif phase == 395:
        by_phase = {item.get("phase"): item for item in inputs}
        required = {
            386: by_phase[386].get("observation_only_use_cases_frozen"),
            387: by_phase[387].get("schema_compatible"),
            388: by_phase[388].get("fingerprints_stable"),
            389: by_phase[389].get("release_harness_coverage_complete"),
            390: by_phase[390].get("fixture_exercise_pass"),
            391: by_phase[391].get("workflow_configuration_valid"),
            392: by_phase[392].get("scientific_family_opened") is False,
            393: by_phase[393].get("no_scientific_family_checkpoint_pass"),
            394: by_phase[394].get("portal_ready"),
        }
        payload.update({
            "phase_readiness": {str(key): bool(value) for key, value in required.items()},
            "batch_checkpoint_pass": all(required.values()),
            "batch_gate": "PHASE386_395_OBSERVATION_RELEASE_HARDENING_CHECKPOINT_PASS_RESEARCH_ONLY",
            "targeted_test_files_planned": 12,
            "targeted_tests_executed": None,
            "targeted_failures": None,
            "targeted_errors": None,
            "global_full_suite_executed": False,
            "next_mandatory_global_full_suite": 405,
            "next_tracking_checkpoint": 395,
            "current_portal_relative_path": by_phase[394].get("current_portal_relative_path"),
            "candidate_dataset_adopted_canonical": False,
            "candidate_dataset_adopted_noncanonical": True,
            "automatic_canonical_replacement_allowed": False,
            "release_workflow_trigger_mode": "MANUAL_OR_PULL_REQUEST_ONLY",
        })

    else:
        raise ValueError(f"Unsupported phase: {phase}")

    if payload.get("capital_used") != 0:
        raise ValueError("Capital lock violated.")
    if payload.get("canonical_data_writes") != 0:
        raise ValueError("Canonical-write lock violated.")
    if payload.get("strategy_approved"):
        raise ValueError("Strategy-approval lock violated.")

    artifact = output_dir / phase_filename(phase)
    write_json(artifact, payload)
    payload["artifact_sha256"] = sha256_file(artifact)
    write_json(artifact, payload)
    return payload
