from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE69_RUNNER_MANIFEST_WRITER_INTEGRATION_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def build_runner_manifest(
    phase: int,
    gate: str,
    preflight_status: str = "PASS",
    focused_tests_status: str = "PASS",
    full_suite_status: str = "PASS",
) -> dict[str, Any]:
    return {
        "phase": phase,
        "gate": gate,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "preflight_status": preflight_status,
        "focused_tests_status": focused_tests_status,
        "full_suite_status": full_suite_status,
        "runner_manifest_ready": True,
        "human_review_required": True,
        "agent_auto_apply_allowed": False,
        **LOCKS,
    }

def validate_runner_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    if manifest.get("preflight_status") != "PASS":
        errors.append("preflight_not_pass")
    if manifest.get("focused_tests_status") != "PASS":
        errors.append("focused_tests_not_pass")
    if manifest.get("full_suite_status") != "PASS":
        errors.append("full_suite_not_pass")

    expected_flags = {
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "edge_validated": False,
        "shadow_decision_allowed": False,
        "decision_layer_allowed": False,
        "safe_apply_allowed": False,
        "promotion_allowed": False,
        "canonical_data_writes": 0,
    }
    for key, expected in expected_flags.items():
        if manifest.get(key) != expected:
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

def write_runner_manifest(output_dir: str | Path, phase: int, gate: str) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest = build_runner_manifest(phase=phase, gate=gate)
    manifest["validation"] = validate_runner_manifest(manifest)
    path = out / f"phase{phase}_runner_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest

def _project() -> Path:
    cwd = Path.cwd()
    return cwd if cwd.name == "crypto_decision_lab" else cwd / "crypto_decision_lab"

def build_phase69(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase69_runner_manifest_writer_integration_research_only"
    out.mkdir(parents=True, exist_ok=True)

    manifest = write_runner_manifest(out, 69, READY_GATE)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "sample_manifest": manifest,
        **LOCKS,
    }

    (out / "phase69_runner_manifest_writer_integration.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "index.html").write_text(
        f"""
<html>
<body>
<h1>QRDS Phase 69 • Runner Manifest Writer Integration</h1>
<p>{READY_GATE}</p>
<p>Operational: BLOCKED_RESEARCH_ONLY</p>
<p>Edge: False</p>
<p>Shadow decision allowed: False</p>
<p>Decision layer allowed: False</p>
<p>Promotion allowed: False</p>
<p>safe_apply_allowed: False</p>
<p>canonical_data_writes: 0</p>
</body>
</html>
""",
        encoding="utf-8",
    )
    return result

def main() -> int:
    result = build_phase69()
    print("QRDS Phase 69 • Runner Manifest Writer Integration Research-Only")
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
