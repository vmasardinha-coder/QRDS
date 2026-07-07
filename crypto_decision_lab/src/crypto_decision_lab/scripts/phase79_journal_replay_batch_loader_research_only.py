from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase72_journal_replay_dry_run_engine_research_only import (
    SAMPLE_REPLAY_ENTRIES,
    replay_batch_dry_run,
    validate_replay_entry,
)
from crypto_decision_lab.scripts.phase76_journal_replay_evidence_scorecard_v2_research_only import (
    build_scorecard_from_entries,
)

READY_GATE = "PHASE79_JOURNAL_REPLAY_BATCH_LOADER_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

REQUIRED_BATCH_FIELDS = {
    "batch_id",
    "created_by",
    "research_only_ack",
    "entries",
}

SAMPLE_BATCH = {
    "batch_id": "sample-batch-79",
    "created_by": "qrds_phase79_fixture",
    "research_only_ack": True,
    "entries": SAMPLE_REPLAY_ENTRIES,
}

def validate_batch_payload(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    missing = sorted(REQUIRED_BATCH_FIELDS - set(payload))
    for field in missing:
        errors.append(f"missing_batch_field:{field}")

    if payload.get("research_only_ack") is not True:
        errors.append("batch_research_only_ack_must_be_true")

    entries = payload.get("entries")
    if not isinstance(entries, list):
        errors.append("entries_must_be_list")
        entries = []

    entry_validations = []
    invalid_entry_count = 0
    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            validation = {
                "index": idx,
                "valid_for_replay_dry_run": False,
                "errors": ["entry_must_be_object"],
            }
        else:
            validation = validate_replay_entry(entry)
            validation["index"] = idx
        if validation.get("valid_for_replay_dry_run") is not True:
            invalid_entry_count += 1
        entry_validations.append(validation)

    return {
        "batch_valid_for_replay_loader": len(errors) == 0,
        "errors": errors,
        "entry_validations": entry_validations,
        "entry_count": len(entries),
        "invalid_entry_count": invalid_entry_count,
        "loader_execution_allowed": False,
        "canonical_data_writes": 0,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
    }

def load_batch_from_path(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("batch_payload_must_be_object")
    return payload

def run_batch_loader(payload: dict[str, Any]) -> dict[str, Any]:
    validation = validate_batch_payload(payload)
    entries = payload.get("entries") if isinstance(payload.get("entries"), list) else []

    replay = replay_batch_dry_run(entries) if entries else replay_batch_dry_run([])
    scorecard = build_scorecard_from_entries(entries) if entries else build_scorecard_from_entries([])

    return {
        "batch_id": payload.get("batch_id"),
        "batch_loader_descriptive_only": True,
        "batch_validation": validation,
        "replay": replay,
        "scorecard": scorecard,
        "loader_execution_allowed": False,
        "replay_execution_allowed": False,
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

def _project() -> Path:
    cwd = Path.cwd()
    return cwd if cwd.name == "crypto_decision_lab" else cwd / "crypto_decision_lab"

def build_phase79(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase79_journal_replay_batch_loader_research_only"
    out.mkdir(parents=True, exist_ok=True)

    batch_path = out / "phase79_sample_batch.json"
    batch_path.write_text(json.dumps(SAMPLE_BATCH, indent=2, sort_keys=True), encoding="utf-8")

    loaded = load_batch_from_path(batch_path)
    loader_result = run_batch_loader(loaded)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_batch_loader_result": loader_result,
        **LOCKS,
    }

    (out / "phase79_journal_replay_batch_loader.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    html = f"""
<html>
<body>
<h1>QRDS Phase 79 • Journal Replay Batch Loader</h1>
<p>{READY_GATE}</p>
<p>Operational: BLOCKED_RESEARCH_ONLY</p>
<p>Edge: False</p>
<p>Shadow decision allowed: False</p>
<p>Decision layer allowed: False</p>
<p>Promotion allowed: False</p>
<p>safe_apply_allowed: False</p>
<p>canonical_data_writes: 0</p>
<p>batch_loader_descriptive_only: True</p>
<p>batch_id: {loader_result["batch_id"]}</p>
<p>entry_count: {loader_result["batch_validation"]["entry_count"]}</p>
<p>invalid_entry_count: {loader_result["batch_validation"]["invalid_entry_count"]}</p>
<p>evidence_status: {loader_result["scorecard"]["evidence_status"]}</p>
</body>
</html>
"""
    (out / "index.html").write_text(html, encoding="utf-8")

    project_out = project / "docs" / "reports" / "journal_replay"
    project_out.mkdir(parents=True, exist_ok=True)
    (project_out / "phase79_journal_replay_batch_loader.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (project_out / "phase79_journal_replay_batch_loader.html").write_text(html, encoding="utf-8")

    return result

def main() -> int:
    result = build_phase79()
    print("QRDS Phase 79 • Journal Replay Batch Loader Research-Only")
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
