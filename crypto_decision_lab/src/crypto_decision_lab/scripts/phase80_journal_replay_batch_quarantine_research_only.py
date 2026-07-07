from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase79_journal_replay_batch_loader_research_only import (
    SAMPLE_BATCH,
    validate_batch_payload,
)

READY_GATE = "PHASE80_JOURNAL_REPLAY_BATCH_QUARANTINE_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

SAMPLE_BAD_BATCH = {
    "batch_id": "sample-bad-batch-80",
    "created_by": "qrds_phase80_fixture",
    "research_only_ack": False,
    "entries": [
        {
            "journal_id": "bad-001",
            "asset": "BTC",
            "would_have_action": "buy",
            "paper_size_notional": 1000.0,
            "entry_reference_price": 100000.0,
            "exit_reference_price": 101000.0,
            "research_only_ack": False,
        }
    ],
}

def build_batch_quarantine(payload: dict[str, Any]) -> dict[str, Any]:
    validation = validate_batch_payload(payload)
    entry_validations = validation.get("entry_validations", [])

    invalid_entries = []
    entries = payload.get("entries") if isinstance(payload.get("entries"), list) else []
    for item in entry_validations:
        if item.get("valid_for_replay_dry_run") is not True:
            index = item.get("index")
            raw_entry = entries[index] if isinstance(index, int) and index < len(entries) else None
            invalid_entries.append({
                "index": index,
                "errors": item.get("errors", []),
                "raw_entry": raw_entry,
            })

    quarantine_required = (
        validation.get("batch_valid_for_replay_loader") is not True
        or int(validation.get("invalid_entry_count", 0)) > 0
    )

    return {
        "batch_id": payload.get("batch_id"),
        "quarantine_required": quarantine_required,
        "quarantine_reason": "batch_or_entry_validation_failed" if quarantine_required else "not_required",
        "batch_validation_errors": validation.get("errors", []),
        "invalid_entry_count": validation.get("invalid_entry_count", 0),
        "invalid_entries": invalid_entries,
        "human_review_required": True,
        "batch_loader_descriptive_only": True,
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

def write_quarantine_bundle(output_dir: str | Path, payload: dict[str, Any]) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    quarantine = build_batch_quarantine(payload)
    batch_id = str(payload.get("batch_id") or "unknown_batch").replace("/", "_")
    path = out / f"{batch_id}_quarantine_bundle.json"
    path.write_text(json.dumps(quarantine, indent=2, sort_keys=True), encoding="utf-8")
    return quarantine

def _project() -> Path:
    cwd = Path.cwd()
    return cwd if cwd.name == "crypto_decision_lab" else cwd / "crypto_decision_lab"

def build_phase80(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase80_journal_replay_batch_quarantine_research_only"
    out.mkdir(parents=True, exist_ok=True)

    safe_quarantine = build_batch_quarantine(SAMPLE_BATCH)
    bad_quarantine = write_quarantine_bundle(out, SAMPLE_BAD_BATCH)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_safe_batch_quarantine": safe_quarantine,
        "sample_bad_batch_quarantine": bad_quarantine,
        **LOCKS,
    }

    (out / "phase80_journal_replay_batch_quarantine.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase80_sample_bad_batch.json").write_text(
        json.dumps(SAMPLE_BAD_BATCH, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    html = f"""
<html>
<body>
<h1>QRDS Phase 80 • Journal Replay Batch Quarantine</h1>
<p>{READY_GATE}</p>
<p>Operational: BLOCKED_RESEARCH_ONLY</p>
<p>Edge: False</p>
<p>Shadow decision allowed: False</p>
<p>Decision layer allowed: False</p>
<p>Promotion allowed: False</p>
<p>safe_apply_allowed: False</p>
<p>canonical_data_writes: 0</p>
<p>batch_loader_descriptive_only: True</p>
<p>bad_batch_id: {bad_quarantine["batch_id"]}</p>
<p>quarantine_required: {bad_quarantine["quarantine_required"]}</p>
<p>invalid_entry_count: {bad_quarantine["invalid_entry_count"]}</p>
<p>human_review_required: True</p>
</body>
</html>
"""
    (out / "index.html").write_text(html, encoding="utf-8")

    project_out = project / "docs" / "reports" / "journal_replay"
    project_out.mkdir(parents=True, exist_ok=True)
    (project_out / "phase80_journal_replay_batch_quarantine.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (project_out / "phase80_journal_replay_batch_quarantine.html").write_text(html, encoding="utf-8")

    return result

def main() -> int:
    result = build_phase80()
    print("QRDS Phase 80 • Journal Replay Batch Quarantine Research-Only")
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
