from __future__ import annotations

import json
from pathlib import Path
from typing import Any

READY_GATE = "PHASE65_LOCAL_SAFETY_PREFLIGHT_GUARD_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

REQUIRED_PREFLIGHT_FLAGS = {
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

FORBIDDEN_PREFLIGHT_TERMS = [
    "buy now",
    "sell now",
    "execute order",
    "place order",
    "increase allocation",
    "reduce allocation",
    "portfolio recommendation",
    "trade signal",
    "shadow_decision_allowed: True",
    "decision_layer_allowed: True",
    "edge_validated: True",
    "safe_apply_allowed: True",
    "promotion_allowed: True",
    "canonical_data_writes: 1",
]

WATCHED_PATH_HINTS = [
    "policy",
    "decision",
    "execution",
    "allocation",
    "recommendation",
    "signal",
    "broker",
    "exchange",
    "canonical",
    "safety",
]

SAMPLE_SAFE_PREFLIGHT_INPUT = {
    "changed_files": ["tests/unit/test_example.py"],
    "focused_tests_status": "PASS",
    "full_suite_status": "PASS",
    "detected_flags": REQUIRED_PREFLIGHT_FLAGS,
    "notes": "Safe technical validation only.",
}

def run_preflight_check(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if payload.get("focused_tests_status") != "PASS":
        errors.append("focused_tests_not_pass")

    if payload.get("full_suite_status") != "PASS":
        errors.append("full_suite_not_pass")

    flags = payload.get("detected_flags", {})
    for key, expected in REQUIRED_PREFLIGHT_FLAGS.items():
        if flags.get(key) != expected:
            errors.append(f"safety_flag_mismatch:{key}")

    text = json.dumps(payload, sort_keys=True, ensure_ascii=False).lower()
    forbidden_found = [
        term for term in FORBIDDEN_PREFLIGHT_TERMS
        if term.lower() in text
    ]
    for term in forbidden_found:
        errors.append(f"forbidden_term:{term}")

    changed_files = payload.get("changed_files", [])
    watched_files = [
        path for path in changed_files
        if any(hint in str(path).lower() for hint in WATCHED_PATH_HINTS)
    ]
    if watched_files:
        warnings.append("watched_paths_require_human_review")

    return {
        "preflight_passed_for_research_only": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "watched_files": watched_files,
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

def _project() -> Path:
    cwd = Path.cwd()
    return cwd if cwd.name == "crypto_decision_lab" else cwd / "crypto_decision_lab"

def build_phase65(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase65_local_safety_preflight_guard_research_only"
    out.mkdir(parents=True, exist_ok=True)

    sample_result = run_preflight_check(SAMPLE_SAFE_PREFLIGHT_INPUT)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "required_preflight_flags": REQUIRED_PREFLIGHT_FLAGS,
        "forbidden_preflight_terms": FORBIDDEN_PREFLIGHT_TERMS,
        "watched_path_hints": WATCHED_PATH_HINTS,
        "sample_preflight_result": sample_result,
        **LOCKS,
    }

    (out / "phase65_local_safety_preflight_guard.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase65_sample_preflight_input.json").write_text(
        json.dumps(SAMPLE_SAFE_PREFLIGHT_INPUT, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "index.html").write_text(
        f"""
<html>
<body>
<h1>QRDS Phase 65 • Local Safety Preflight Guard</h1>
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
    result = build_phase65()
    print("QRDS Phase 65 • Local Safety Preflight Guard Research-Only")
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
