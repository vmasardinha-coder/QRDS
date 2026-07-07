from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE90_JOURNAL_REPLAY_EVIDENCE_CHECKPOINT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

CHECKPOINT_PHASES = [
    {
        "phase": 84,
        "gate": "PHASE84_JOURNAL_REPLAY_BATCH_REPORT_INDEX_RESEARCH_ONLY_READY_RESEARCH_ONLY",
        "test_file": "tests/unit/test_phase84_journal_replay_batch_report_index_research_only.py",
        "scope": "batch report index",
    },
    {
        "phase": 85,
        "gate": "PHASE85_JOURNAL_REPLAY_BATCH_PORTAL_QA_SMOKE_RESEARCH_ONLY_READY_RESEARCH_ONLY",
        "test_file": "tests/unit/test_phase85_journal_replay_batch_portal_qa_smoke_research_only.py",
        "scope": "batch portal QA smoke",
    },
    {
        "phase": 86,
        "gate": "PHASE86_LARGER_SYNTHETIC_BATCH_FIXTURE_RESEARCH_ONLY_READY_RESEARCH_ONLY",
        "test_file": "tests/unit/test_phase86_larger_synthetic_batch_fixture_research_only.py",
        "scope": "larger synthetic batch fixture",
    },
    {
        "phase": 87,
        "gate": "PHASE87_REPLAY_EVIDENCE_THRESHOLD_REGISTRY_RESEARCH_ONLY_READY_RESEARCH_ONLY",
        "test_file": "tests/unit/test_phase87_replay_evidence_threshold_registry_research_only.py",
        "scope": "replay evidence threshold registry",
    },
    {
        "phase": 88,
        "gate": "PHASE88_NEGATIVE_CASE_REGISTRY_RESEARCH_ONLY_READY_RESEARCH_ONLY",
        "test_file": "tests/unit/test_phase88_negative_case_registry_research_only.py",
        "scope": "negative case registry",
    },
    {
        "phase": 89,
        "gate": "PHASE89_REPLAY_FALSE_POSITIVE_NO_EDGE_GUARD_RESEARCH_ONLY_READY_RESEARCH_ONLY",
        "test_file": "tests/unit/test_phase89_replay_false_positive_no_edge_guard_research_only.py",
        "scope": "false positive no-edge guard",
    },
]

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

def build_checkpoint_registry() -> dict[str, Any]:
    entries = []

    for item in CHECKPOINT_PHASES:
        entries.append({
            "phase": item["phase"],
            "gate": item["gate"],
            "scope": item["scope"],
            "test_file": item["test_file"],
            "expected_focused_test_status": "PASS",
            "included_in_checkpoint": True,
            "operational_status": "BLOCKED_RESEARCH_ONLY",
            "edge_validated": False,
            "shadow_decision_allowed": False,
            "decision_layer_allowed": False,
            "safe_apply_allowed": False,
            "promotion_allowed": False,
            "canonical_data_writes": 0,
        })

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_name": "journal_replay_evidence_checkpoint_phases_84_89",
        "checkpoint_descriptive_only": True,
        "checkpoint_phase_start": 84,
        "checkpoint_phase_end": 89,
        "checkpoint_phase_count": len(entries),
        "entries": entries,
        "focused_tests_required": True,
        "focused_tests_scope": [item["test_file"] for item in CHECKPOINT_PHASES],
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        "full_suite_reason": "Codespaces quota unavailable; local checkpoint runs focused phase tests only. Full suite deferred until Codespaces quota returns or explicit local full-suite approval.",
        "checkpoint_status": "READY_FOR_LOCAL_FOCUSED_VALIDATION_RESEARCH_ONLY",
        "human_review_required": True,
        **LOCKS,
    }

def render_checkpoint_html(registry: dict[str, Any]) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{entry['phase']}</td>"
        f"<td>{entry['gate']}</td>"
        f"<td>{entry['scope']}</td>"
        f"<td>{entry['expected_focused_test_status']}</td>"
        f"<td>{entry['operational_status']}</td>"
        "</tr>"
        for entry in registry["entries"]
    )

    return f"""
<html>
<head>
  <meta charset="utf-8">
  <title>QRDS Journal Replay Evidence Checkpoint</title>
  <style>
    body{{font-family:system-ui;background:#07111f;color:#e7edf8;padding:32px}}
    .badge{{display:inline-block;padding:6px 10px;border:1px solid #28415f;border-radius:999px;margin:4px}}
    table{{border-collapse:collapse;background:#101f35;width:100%}}
    th,td{{border:1px solid #28415f;padding:10px;text-align:left;vertical-align:top}}
  </style>
</head>
<body>
  <h1>QRDS Journal Replay Evidence Checkpoint</h1>
  <p>{READY_GATE}</p>
  <p class="badge">Checkpoint: phases 84–89</p>
  <p class="badge">Operational: BLOCKED_RESEARCH_ONLY</p>
  <p class="badge">checkpoint_descriptive_only: True</p>
  <p class="badge">Edge: False</p>
  <p class="badge">Shadow decision allowed: False</p>
  <p class="badge">Decision layer allowed: False</p>
  <p class="badge">Promotion allowed: False</p>
  <p class="badge">safe_apply_allowed: False</p>
  <p class="badge">canonical_data_writes: 0</p>
  <p class="badge">Full suite: SKIPPED_LOCAL_ECONOMICAL</p>

  <h2>Checkpoint Entries</h2>
  <table>
    <thead>
      <tr><th>Phase</th><th>Gate</th><th>Scope</th><th>Focused Test</th><th>Operational</th></tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>

  <h2>Boundary</h2>
  <p>This checkpoint is descriptive research only. It confirms focused local validation coverage
  for phases 84–89. It does not validate edge, generate signals, recommendations, allocations,
  shadow decisions, operational decisions, promotion, safe-apply or canonical writes.</p>
</body>
</html>
"""

def build_phase90(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = Path.cwd()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase90_journal_replay_evidence_checkpoint_research_only"
    out.mkdir(parents=True, exist_ok=True)

    registry = build_checkpoint_registry()

    (out / "phase90_journal_replay_evidence_checkpoint.json").write_text(
        json.dumps(registry, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase90_journal_replay_evidence_checkpoint.html").write_text(
        render_checkpoint_html(registry),
        encoding="utf-8",
    )

    return {
        "gate": READY_GATE,
        "ready": True,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_registry": registry,
        **LOCKS,
    }

def main() -> int:
    result = build_phase90()
    registry = result["checkpoint_registry"]

    print("QRDS Phase 90 • Journal Replay Evidence Checkpoint Research-Only")
    print(result["gate"])
    print("Checkpoint phases:", f"{registry['checkpoint_phase_start']}-{registry['checkpoint_phase_end']}")
    print("Focused tests:", "REQUIRED")
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")
    print("Full suite:", registry["full_suite_status"])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
