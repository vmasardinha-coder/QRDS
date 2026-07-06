from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE68_RUNNER_VALIDATION_MANIFEST_RESEARCH_ONLY_READY_RESEARCH_ONLY"

LOCKS = {
    "app_mode": "INTERACTIVE_RESEARCH_ONLY",
    "policy_lock": "ACTIVE",
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "edge_validated": False,
    "edge_operationally_validated": False,
    "shadow_decision_allowed": False,
    "decision_layer_allowed": False,
    "trading_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "operational_decision_allowed": False,
    "safe_apply_allowed": False,
    "promotion_allowed": False,
    "canonical_data_writes": 0,
}

REQUIRED_MANIFEST_FIELDS = [
    "phase",
    "gate",
    "preflight_status",
    "focused_tests_status",
    "full_suite_status",
    "operational_status",
    "edge_validated",
    "shadow_decision_allowed",
    "decision_layer_allowed",
    "promotion_allowed",
    "safe_apply_allowed",
    "canonical_data_writes",
]

SAMPLE_MANIFEST = {
    "phase": 68,
    "gate": READY_GATE,
    "preflight_status": "PASS",
    "focused_tests_status": "PASS",
    "full_suite_status": "PASS",
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "edge_validated": False,
    "shadow_decision_allowed": False,
    "decision_layer_allowed": False,
    "promotion_allowed": False,
    "safe_apply_allowed": False,
    "canonical_data_writes": 0,
}

def validate_runner_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    for field in REQUIRED_MANIFEST_FIELDS:
        if field not in manifest:
            errors.append(f"missing:{field}")

    if manifest.get("preflight_status") != "PASS":
        errors.append("preflight_not_pass")

    if manifest.get("focused_tests_status") != "PASS":
        errors.append("focused_tests_not_pass")

    if manifest.get("full_suite_status") != "PASS":
        errors.append("full_suite_not_pass")

    expected = {
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "edge_validated": False,
        "shadow_decision_allowed": False,
        "decision_layer_allowed": False,
        "promotion_allowed": False,
        "safe_apply_allowed": False,
        "canonical_data_writes": 0,
    }

    for key, value in expected.items():
        if manifest.get(key) != value:
            errors.append(f"safety_flag_mismatch:{key}")

    return {
        "manifest_valid_for_research_only": len(errors) == 0,
        "errors": errors,
        "human_review_required": True,
        "agent_auto_apply_allowed": False,
        "safe_apply_allowed": False,
        "promotion_allowed": False,
        "edge_validated": False,
        "shadow_decision_allowed": False,
        "decision_layer_allowed": False,
        "canonical_data_writes": 0,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
    }

def build_validation_manifest(phase: int = 68, gate: str = READY_GATE) -> dict[str, Any]:
    manifest = dict(SAMPLE_MANIFEST)
    manifest["phase"] = phase
    manifest["gate"] = gate
    manifest["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["validation"] = validate_runner_manifest(manifest)
    return manifest

def _project() -> Path:
    cwd = Path.cwd()
    return cwd if cwd.name == "crypto_decision_lab" else cwd / "crypto_decision_lab"

def build_phase68(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase68_runner_validation_manifest_research_only"
    out.mkdir(parents=True, exist_ok=True)

    manifest = build_validation_manifest()

    result = {
        "gate": READY_GATE,
        "ready": True,
        "required_manifest_fields": REQUIRED_MANIFEST_FIELDS,
        "sample_manifest": manifest,
        **LOCKS,
    }

    (out / "phase68_runner_validation_manifest.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase68_sample_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "index.html").write_text(
        f"""
<html>
<body>
<h1>QRDS Phase 68 • Runner Validation Manifest</h1>
<p>{READY_GATE}</p>
<p>Operational: BLOCKED_RESEARCH_ONLY</p>
<p>Edge: False</p>
<p>Shadow decision allowed: False</p>
<p>Decision layer allowed: False</p>
<p>Promotion allowed: False</p>
<p>safe_apply_allowed: False</p>
<p>canonical_data_writes: 0</p>
<p>preflight_status: PASS</p>
</body>
</html>
""",
        encoding="utf-8",
    )
    return result

def main() -> int:
    result = build_phase68()
    print("QRDS Phase 68 • Runner Validation Manifest Research-Only")
    print(result["gate"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("Promotion allowed: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
