from __future__ import annotations

import json
from pathlib import Path
from typing import Any

READY_GATE = "PHASE64_AGENT_PATCH_DIFF_GUARD_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

FORBIDDEN_DIFF_PATTERNS = [
    "operational_status: ACTIVE",
    '"operational_status": "ACTIVE"',
    "edge_validated: True",
    '"edge_validated": true',
    "edge_operationally_validated: True",
    '"edge_operationally_validated": true',
    "shadow_decision_allowed: True",
    '"shadow_decision_allowed": true',
    "decision_layer_allowed: True",
    '"decision_layer_allowed": true',
    "trading_signal_generated: True",
    '"trading_signal_generated": true',
    "recommendation_generated: True",
    '"recommendation_generated": true',
    "allocation_generated: True",
    '"allocation_generated": true',
    "operational_decision_allowed: True",
    '"operational_decision_allowed": true',
    "safe_apply_allowed: True",
    '"safe_apply_allowed": true',
    "promotion_allowed: True",
    '"promotion_allowed": true',
    "canonical_data_writes: 1",
    '"canonical_data_writes": 1',
    "buy now",
    "sell now",
    "execute order",
    "increase allocation",
    "reduce allocation",
    "trading signal",
    "portfolio recommendation",
]

WATCHED_PATH_HINTS = [
    "policy",
    "gate",
    "decision",
    "allocation",
    "execution",
    "order",
    "canonical",
    "safety",
    "broker",
    "exchange",
]

SAMPLE_SAFE_DIFF = """
diff --git a/tests/unit/test_example.py b/tests/unit/test_example.py
+def test_path_fix():
+    assert True
"""

SAMPLE_UNSAFE_DIFF = """
diff --git a/src/policy.py b/src/policy.py
- shadow_decision_allowed: False
+ shadow_decision_allowed: True
+ buy now
"""

def scan_patch_diff(diff_text: str, changed_files: list[str] | None = None) -> dict[str, Any]:
    changed_files = changed_files or []
    lower = diff_text.lower()

    forbidden_found = [
        pattern for pattern in FORBIDDEN_DIFF_PATTERNS
        if pattern.lower() in lower
    ]

    watched_files = [
        path for path in changed_files
        if any(hint in path.lower() for hint in WATCHED_PATH_HINTS)
    ]

    requires_human_review = True
    safe_for_research_review = len(forbidden_found) == 0

    return {
        "safe_for_research_review": safe_for_research_review,
        "forbidden_patterns_found": forbidden_found,
        "changed_files": changed_files,
        "watched_files": watched_files,
        "watched_file_count": len(watched_files),
        "requires_human_review": requires_human_review,
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

def build_phase64(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase64_agent_patch_diff_guard_research_only"
    out.mkdir(parents=True, exist_ok=True)

    safe_scan = scan_patch_diff(SAMPLE_SAFE_DIFF, ["tests/unit/test_example.py"])
    unsafe_scan = scan_patch_diff(SAMPLE_UNSAFE_DIFF, ["src/policy.py"])

    result = {
        "gate": READY_GATE,
        "ready": True,
        "forbidden_diff_patterns": FORBIDDEN_DIFF_PATTERNS,
        "watched_path_hints": WATCHED_PATH_HINTS,
        "sample_safe_scan": safe_scan,
        "sample_unsafe_scan": unsafe_scan,
        **LOCKS,
    }

    (out / "phase64_agent_patch_diff_guard.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase64_sample_safe_diff.txt").write_text(SAMPLE_SAFE_DIFF, encoding="utf-8")
    (out / "phase64_sample_unsafe_diff.txt").write_text(SAMPLE_UNSAFE_DIFF, encoding="utf-8")
    (out / "index.html").write_text(
        f"""
<html>
<body>
<h1>QRDS Phase 64 • Agent Patch Diff Guard</h1>
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
    result = build_phase64()
    print("QRDS Phase 64 • Agent Patch Diff Guard Research-Only")
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
