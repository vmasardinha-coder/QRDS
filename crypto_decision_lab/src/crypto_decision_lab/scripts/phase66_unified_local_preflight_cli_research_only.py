from __future__ import annotations

import json
from pathlib import Path
from typing import Any

READY_GATE = "PHASE66_UNIFIED_LOCAL_PREFLIGHT_CLI_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

FORBIDDEN_TERMS = [
    "buy now",
    "sell now",
    "execute order",
    "increase allocation",
    "reduce allocation",
    "trade signal",
    "portfolio recommendation",
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

SAMPLE_PREFLIGHT_PAYLOAD = {
    "changed_files": ["tests/unit/test_example.py"],
    "focused_tests_status": "PASS",
    "full_suite_status": "PASS",
    "detected_flags": {
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
    },
    "notes": "research-only preflight sample",
}

def unified_preflight(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if payload.get("focused_tests_status") != "PASS":
        errors.append("focused_tests_not_pass")
    if payload.get("full_suite_status") != "PASS":
        errors.append("full_suite_not_pass")

    flags = payload.get("detected_flags", {})
    for key, expected in LOCKS.items():
        if key in ["app_mode", "policy_lock"]:
            continue
        if flags.get(key) != expected:
            errors.append(f"safety_flag_mismatch:{key}")

    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).lower()
    for term in FORBIDDEN_TERMS:
        if term.lower() in blob:
            errors.append(f"forbidden_term:{term}")

    watched_files = [
        str(path) for path in payload.get("changed_files", [])
        if any(hint in str(path).lower() for hint in WATCHED_PATH_HINTS)
    ]
    if watched_files:
        warnings.append("watched_paths_require_human_review")

    return {
        "preflight_passed": len(errors) == 0,
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

def build_phase66(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase66_unified_local_preflight_cli_research_only"
    out.mkdir(parents=True, exist_ok=True)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "sample_payload": SAMPLE_PREFLIGHT_PAYLOAD,
        "sample_preflight": unified_preflight(SAMPLE_PREFLIGHT_PAYLOAD),
        "forbidden_terms": FORBIDDEN_TERMS,
        "watched_path_hints": WATCHED_PATH_HINTS,
        **LOCKS,
    }

    (out / "phase66_unified_local_preflight_cli.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase66_sample_preflight_payload.json").write_text(
        json.dumps(SAMPLE_PREFLIGHT_PAYLOAD, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "index.html").write_text(
        f"""
<html>
<body>
<h1>QRDS Phase 66 • Unified Local Preflight CLI</h1>
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
    result = build_phase66()
    print("QRDS Phase 66 • Unified Local Preflight CLI Research-Only")
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
