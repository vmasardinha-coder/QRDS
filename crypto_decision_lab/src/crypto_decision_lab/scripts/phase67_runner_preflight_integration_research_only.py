from __future__ import annotations

import json
from pathlib import Path
from typing import Any

READY_GATE = "PHASE67_RUNNER_PREFLIGHT_INTEGRATION_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

RUNNER_REQUIREMENTS = [
    "runner_executes_preflight_before_verify",
    "runner_executes_verify",
    "runner_records_validation_log",
    "runner_keeps_research_only_locks",
    "runner_does_not_auto_apply_agent_changes",
    "runner_does_not_write_canonical_data",
]

SAMPLE_RUNNER_LOG = """
[QRDS][Runner] Root: /workspaces/QRDS
[QRDS][Runner] Phase: 67
[QRDS][Runner] Mode: run-and-verify
[QRDS][Runner] Running local preflight...
[QRDS][Runner] Running verify: qrds_phase67_verify.sh
PHASE67_RUNNER_PREFLIGHT_INTEGRATION_RESEARCH_ONLY_READY_RESEARCH_ONLY
Operational: BLOCKED_RESEARCH_ONLY
Edge: False
Shadow decision allowed: False
Decision layer allowed: False
Promotion allowed: False
safe_apply_allowed: False
canonical_data_writes: 0
Focused tests: PASS
Full suite: PASS
"""

def evaluate_runner_log(text: str, expected_gate: str = READY_GATE) -> dict[str, Any]:
    required_lines = [
        expected_gate,
        "Operational: BLOCKED_RESEARCH_ONLY",
        "Edge: False",
        "Shadow decision allowed: False",
        "Decision layer allowed: False",
        "Promotion allowed: False",
        "safe_apply_allowed: False",
        "canonical_data_writes: 0",
        "Focused tests: PASS",
        "Full suite: PASS",
    ]
    missing = [line for line in required_lines if line not in text]
    preflight_detected = "[qrds][runner] running local preflight" in text.lower()

    forbidden = [
        "Operational: ACTIVE",
        "Edge: True",
        "Shadow decision allowed: True",
        "Decision layer allowed: True",
        "Promotion allowed: True",
        "safe_apply_allowed: True",
        "canonical_data_writes: 1",
    ]
    forbidden_found = [line for line in forbidden if line in text]

    return {
        "runner_log_valid_for_research_only": not missing and not forbidden_found and preflight_detected,
        "missing_required_lines": missing,
        "forbidden_lines_found": forbidden_found,
        "preflight_detected": preflight_detected,
        "promotion_allowed": False,
        "edge_validated": False,
        "shadow_decision_allowed": False,
        "decision_layer_allowed": False,
        "safe_apply_allowed": False,
        "canonical_data_writes": 0,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
    }

def _project() -> Path:
    cwd = Path.cwd()
    return cwd if cwd.name == "crypto_decision_lab" else cwd / "crypto_decision_lab"

def build_phase67(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase67_runner_preflight_integration_research_only"
    out.mkdir(parents=True, exist_ok=True)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "runner_requirements": RUNNER_REQUIREMENTS,
        "sample_runner_log_evaluation": evaluate_runner_log(SAMPLE_RUNNER_LOG),
        **LOCKS,
    }

    (out / "phase67_runner_preflight_integration.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase67_sample_runner_log.txt").write_text(SAMPLE_RUNNER_LOG, encoding="utf-8")
    (out / "index.html").write_text(
        f"""
<html>
<body>
<h1>QRDS Phase 67 • Runner Preflight Integration</h1>
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
    result = build_phase67()
    print("QRDS Phase 67 • Runner Preflight Integration Research-Only")
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
