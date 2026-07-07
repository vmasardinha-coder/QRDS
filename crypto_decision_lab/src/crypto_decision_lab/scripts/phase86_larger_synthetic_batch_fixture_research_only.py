from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase79_journal_replay_batch_loader_research_only import (
    SAMPLE_BATCH,
    validate_batch_payload,
)
from crypto_decision_lab.scripts.phase83_journal_replay_batch_report_research_only import (
    build_batch_report,
    write_batch_report,
)
from crypto_decision_lab.scripts.phase84_journal_replay_batch_report_index_research_only import (
    write_batch_report_index,
)

READY_GATE = "PHASE86_LARGER_SYNTHETIC_BATCH_FIXTURE_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def _tag_entry(entry: dict[str, Any], idx: int) -> dict[str, Any]:
    tagged = copy.deepcopy(entry)

    for key in ("entry_id", "id", "journal_id", "observation_id"):
        if key in tagged:
            tagged[key] = f"{tagged[key]}-synthetic-{idx:03d}"

    tagged["synthetic_fixture_row"] = True
    tagged["synthetic_fixture_seq"] = idx
    tagged["research_only_ack"] = True

    return tagged

def build_larger_synthetic_batch(multiplier: int = 6) -> dict[str, Any]:
    if multiplier < 2:
        raise ValueError("multiplier must be >= 2")

    base = copy.deepcopy(SAMPLE_BATCH)
    entries = base.get("entries", [])

    synthetic_entries: list[dict[str, Any]] = []
    seq = 1

    for round_idx in range(multiplier):
        for entry in entries:
            tagged = _tag_entry(entry, seq)

            if isinstance(tagged.get("notes"), str):
                tagged["notes"] = f"{tagged['notes']} | synthetic_fixture_round={round_idx + 1}"
            else:
                tagged["notes"] = f"synthetic_fixture_round={round_idx + 1}"

            synthetic_entries.append(tagged)
            seq += 1

    base["batch_id"] = f"larger-synthetic-batch-phase86-x{multiplier}"
    base["created_by"] = "qrds_phase86_larger_synthetic_batch_fixture_research_only"
    base["research_only_ack"] = True
    base["synthetic_fixture"] = True
    base["synthetic_fixture_multiplier"] = multiplier
    base["synthetic_fixture_original_entry_count"] = len(entries)
    base["synthetic_fixture_entry_count"] = len(synthetic_entries)
    base["entries"] = synthetic_entries

    return base

def build_larger_synthetic_batch_package(output_dir: str | Path, multiplier: int = 6) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    batch = build_larger_synthetic_batch(multiplier=multiplier)
    validation = validate_batch_payload(batch)
    report = build_batch_report(batch)

    (out / "larger_synthetic_batch_phase86.json").write_text(
        json.dumps(batch, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    write_batch_report(out, batch)
    index = write_batch_report_index(out)

    package = {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "larger_synthetic_batch_fixture_descriptive_only": True,
        "batch_id": batch["batch_id"],
        "multiplier": multiplier,
        "entry_count": len(batch["entries"]),
        "batch_validation": validation,
        "batch_report_status": report.get("report_status"),
        "batch_report_index_status": index.get("index_valid_for_research_only"),
        "human_review_required": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        "focused_tests_required": True,
        **LOCKS,
    }

    (out / "phase86_larger_synthetic_batch_fixture.json").write_text(
        json.dumps(package, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    (out / "phase86_larger_synthetic_batch_fixture.html").write_text(
        render_larger_synthetic_batch_fixture_html(package),
        encoding="utf-8",
    )

    return package

def render_larger_synthetic_batch_fixture_html(package: dict[str, Any]) -> str:
    return f"""
<html>
<head>
  <meta charset="utf-8">
  <title>QRDS Larger Synthetic Batch Fixture</title>
  <style>
    body{{font-family:system-ui;background:#07111f;color:#e7edf8;padding:32px}}
    .badge{{display:inline-block;padding:6px 10px;border:1px solid #28415f;border-radius:999px;margin:4px}}
  </style>
</head>
<body>
  <h1>QRDS Larger Synthetic Batch Fixture</h1>
  <p>{READY_GATE}</p>
  <p class="badge">Operational: BLOCKED_RESEARCH_ONLY</p>
  <p class="badge">larger_synthetic_batch_fixture_descriptive_only: True</p>
  <p class="badge">Full suite: SKIPPED_LOCAL_ECONOMICAL</p>
  <p class="badge">Edge: False</p>
  <p class="badge">Shadow decision allowed: False</p>
  <p class="badge">Decision layer allowed: False</p>
  <p class="badge">Promotion allowed: False</p>
  <p class="badge">safe_apply_allowed: False</p>
  <p class="badge">canonical_data_writes: 0</p>

  <h2>Fixture</h2>
  <p>batch_id: {package["batch_id"]}</p>
  <p>multiplier: {package["multiplier"]}</p>
  <p>entry_count: {package["entry_count"]}</p>
  <p>batch_report_status: {package["batch_report_status"]}</p>
  <p>batch_report_index_status: {package["batch_report_index_status"]}</p>

  <h2>Boundary</h2>
  <p>This larger synthetic batch fixture is descriptive research only. It does not validate edge,
  generate signals, recommendations, allocations, shadow decisions, operational decisions,
  promotion, safe-apply or canonical writes.</p>
</body>
</html>
"""

def build_phase86(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = Path.cwd()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase86_larger_synthetic_batch_fixture_research_only"
    package = build_larger_synthetic_batch_package(out)
    return {
        "gate": READY_GATE,
        "ready": package["batch_validation"].get("batch_valid_for_replay_loader") is True,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "larger_synthetic_batch_package": package,
        **LOCKS,
    }

def main() -> int:
    result = build_phase86()
    package = result["larger_synthetic_batch_package"]

    print("QRDS Phase 86 • Larger Synthetic Batch Fixture Research-Only")
    print(result["gate"])
    print("Batch validation:", package["batch_validation"].get("batch_valid_for_replay_loader"))
    print("Entry count:", package["entry_count"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")
    print("Full suite: SKIPPED_LOCAL_ECONOMICAL")

    return 0 if result["ready"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
