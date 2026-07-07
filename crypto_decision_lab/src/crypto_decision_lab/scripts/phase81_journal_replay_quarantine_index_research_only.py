from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase80_journal_replay_batch_quarantine_research_only import (
    SAMPLE_BAD_BATCH,
    build_batch_quarantine,
)

READY_GATE = "PHASE81_JOURNAL_REPLAY_QUARANTINE_INDEX_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

REQUIRED_ENTRY_FLAGS = {
    "replay_execution_allowed": False,
    "loader_execution_allowed": False,
    "edge_validated": False,
    "shadow_decision_allowed": False,
    "decision_layer_allowed": False,
    "safe_apply_allowed": False,
    "promotion_allowed": False,
    "canonical_data_writes": 0,
    "operational_status": "BLOCKED_RESEARCH_ONLY",
}

def validate_quarantine_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    if "batch_id" not in bundle:
        errors.append("missing:batch_id")
    if "quarantine_required" not in bundle:
        errors.append("missing:quarantine_required")
    if bundle.get("human_review_required") is not True:
        errors.append("human_review_required_must_be_true")

    for key, expected in REQUIRED_ENTRY_FLAGS.items():
        if bundle.get(key) != expected:
            errors.append(f"safety_flag_mismatch:{key}")

    return {
        "bundle_valid_for_research_index": len(errors) == 0,
        "errors": errors,
        "batch_id": bundle.get("batch_id"),
        "quarantine_required": bundle.get("quarantine_required"),
        "invalid_entry_count": bundle.get("invalid_entry_count", 0),
        "human_review_required": True,
        "replay_execution_allowed": False,
        "loader_execution_allowed": False,
        "edge_validated": False,
        "shadow_decision_allowed": False,
        "decision_layer_allowed": False,
        "safe_apply_allowed": False,
        "promotion_allowed": False,
        "canonical_data_writes": 0,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
    }

def build_quarantine_index(quarantine_dir: str | Path) -> dict[str, Any]:
    base = Path(quarantine_dir)
    base.mkdir(parents=True, exist_ok=True)

    bundles = []
    for path in sorted(base.glob("*_quarantine_bundle.json")):
        try:
            bundle = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            bundle = {
                "batch_id": path.stem,
                "quarantine_required": True,
                "human_review_required": True,
                "read_error": str(exc),
                "replay_execution_allowed": False,
                "loader_execution_allowed": False,
                "edge_validated": False,
                "shadow_decision_allowed": False,
                "decision_layer_allowed": False,
                "safe_apply_allowed": False,
                "promotion_allowed": False,
                "canonical_data_writes": 0,
                "operational_status": "BLOCKED_RESEARCH_ONLY",
            }
        bundle["_path"] = str(path)
        bundles.append(bundle)

    entries = []
    invalid_entries = []
    for bundle in bundles:
        validation = validate_quarantine_bundle(bundle)
        entry = {
            "batch_id": bundle.get("batch_id"),
            "path": bundle.get("_path"),
            "quarantine_required": bundle.get("quarantine_required"),
            "invalid_entry_count": bundle.get("invalid_entry_count", 0),
            "human_review_required": bundle.get("human_review_required"),
            "validation": validation,
        }
        entries.append(entry)
        if validation["bundle_valid_for_research_index"] is not True:
            invalid_entries.append(entry)

    quarantine_required_count = len([e for e in entries if e["quarantine_required"] is True])

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "quarantine_index_descriptive_only": True,
        "bundle_count": len(entries),
        "quarantine_required_count": quarantine_required_count,
        "invalid_index_entry_count": len(invalid_entries),
        "entries": entries,
        "invalid_index_entries": invalid_entries,
        "index_valid_for_research_only": len(invalid_entries) == 0,
        "human_review_required": True,
        "replay_execution_allowed": False,
        "loader_execution_allowed": False,
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
        "operational_status": "BLOCKED_RESEARCH_ONLY",
    }

def render_quarantine_index_html(index: dict[str, Any]) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{entry['batch_id']}</td>"
        f"<td>{entry['quarantine_required']}</td>"
        f"<td>{entry['invalid_entry_count']}</td>"
        f"<td>{entry['human_review_required']}</td>"
        f"<td>{entry['validation']['bundle_valid_for_research_index']}</td>"
        "</tr>"
        for entry in index["entries"]
    ) or "<tr><td colspan='5'>No quarantine bundles found.</td></tr>"

    return f"""
<html>
<head>
  <meta charset="utf-8">
  <title>QRDS Journal Replay Quarantine Index</title>
  <style>
    body{{font-family:system-ui;background:#07111f;color:#e7edf8;padding:32px}}
    table{{border-collapse:collapse;width:100%;background:#101f35}}
    th,td{{border:1px solid #28415f;padding:10px;text-align:left}}
    .badge{{display:inline-block;padding:6px 10px;border:1px solid #28415f;border-radius:999px;margin:4px}}
  </style>
</head>
<body>
  <h1>QRDS Journal Replay Quarantine Index</h1>
  <p>{READY_GATE}</p>
  <p class="badge">Operational: BLOCKED_RESEARCH_ONLY</p>
  <p class="badge">Edge: False</p>
  <p class="badge">Shadow decision allowed: False</p>
  <p class="badge">Decision layer allowed: False</p>
  <p class="badge">Promotion allowed: False</p>
  <p class="badge">safe_apply_allowed: False</p>
  <p class="badge">canonical_data_writes: 0</p>
  <p class="badge">replay_execution_allowed: False</p>

  <h2>Summary</h2>
  <p>bundle_count: {index["bundle_count"]}</p>
  <p>quarantine_required_count: {index["quarantine_required_count"]}</p>
  <p>invalid_index_entry_count: {index["invalid_index_entry_count"]}</p>
  <p>index_valid_for_research_only: {index["index_valid_for_research_only"]}</p>

  <h2>Bundles</h2>
  <table>
    <thead>
      <tr><th>Batch ID</th><th>Quarantine Required</th><th>Invalid Entries</th><th>Human Review</th><th>Index Valid</th></tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>

  <h2>Boundary</h2>
  <p>This index is descriptive research only. It does not unlock replay execution, edge validation,
  signals, recommendations, allocations, shadow decisions, operational decisions, promotion,
  safe-apply or canonical writes.</p>
</body>
</html>
"""

def write_quarantine_index(quarantine_dir: str | Path) -> dict[str, Any]:
    base = Path(quarantine_dir)
    index = build_quarantine_index(base)
    (base / "quarantine_index.json").write_text(
        json.dumps(index, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (base / "quarantine_index.html").write_text(
        render_quarantine_index_html(index),
        encoding="utf-8",
    )
    return index

def _project() -> Path:
    cwd = Path.cwd()
    return cwd if cwd.name == "crypto_decision_lab" else cwd / "crypto_decision_lab"

def build_phase81(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase81_journal_replay_quarantine_index_research_only"
    out.mkdir(parents=True, exist_ok=True)

    sample_quarantine = build_batch_quarantine(SAMPLE_BAD_BATCH)
    (out / "sample-bad-batch-80_quarantine_bundle.json").write_text(
        json.dumps(sample_quarantine, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    index = write_quarantine_index(out)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_quarantine_index": index,
        **LOCKS,
    }

    (out / "phase81_journal_replay_quarantine_index.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "index.html").write_text(render_quarantine_index_html(index), encoding="utf-8")

    project_out = project / "docs" / "reports" / "journal_replay"
    project_out.mkdir(parents=True, exist_ok=True)
    write_quarantine_index(project_out)
    (project_out / "phase81_journal_replay_quarantine_index.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (project_out / "phase81_journal_replay_quarantine_index.html").write_text(
        render_quarantine_index_html(index),
        encoding="utf-8",
    )

    return result

def main() -> int:
    result = build_phase81()
    print("QRDS Phase 81 • Journal Replay Quarantine Index Research-Only")
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
