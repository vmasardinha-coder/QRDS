from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Any

READY_GATE = "PHASE58_JOURNAL_BATCH_STAGING_VALIDATOR_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

REQUIRED = [
    "journal_id",
    "created_at_utc",
    "asset",
    "venue",
    "hypothesis_id",
    "observed_context",
    "would_have_action",
    "paper_size_notional",
    "entry_reference_price",
    "fees_slippage_assumption",
    "research_only_ack",
]

ALLOWED_ACTIONS = {"watch", "paper_long", "paper_short", "paper_no_action"}

SAMPLE_BATCH = [
    {
        "journal_id": "journal-sample-001",
        "created_at_utc": "2026-07-06T12:00:00+00:00",
        "asset": "BTC",
        "venue": "research_manual",
        "hypothesis_id": "HYP-VOL-001",
        "observed_context": "Manual paper-only observation.",
        "would_have_action": "paper_no_action",
        "paper_size_notional": 0,
        "entry_reference_price": 100000.0,
        "fees_slippage_assumption": "Research-only placeholder.",
        "research_only_ack": True,
    },
    {
        "journal_id": "journal-sample-002",
        "created_at_utc": "2026-07-06T13:00:00+00:00",
        "asset": "ETH",
        "venue": "research_manual",
        "hypothesis_id": "HYP-VOL-001",
        "observed_context": "Second paper-only observation.",
        "would_have_action": "watch",
        "paper_size_notional": 0,
        "entry_reference_price": 3000.0,
        "fees_slippage_assumption": "Research-only placeholder.",
        "research_only_ack": True,
    },
]

def validate_entry(entry: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    for field in REQUIRED:
        if field not in entry:
            errors.append(f"missing:{field}")

    if entry.get("research_only_ack") is not True:
        errors.append("research_only_ack_must_be_true")

    if entry.get("would_have_action") not in ALLOWED_ACTIONS:
        errors.append("action_must_be_paper_only")

    for numeric in ["paper_size_notional", "entry_reference_price"]:
        value = entry.get(numeric)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(f"{numeric}_must_be_number")

    try:
        datetime.fromisoformat(str(entry.get("created_at_utc")).replace("Z", "+00:00"))
    except Exception:
        errors.append("created_at_utc_must_be_datetime")

    return {
        "journal_id": entry.get("journal_id"),
        "valid_for_staging_research_only": len(errors) == 0,
        "errors": errors,
    }

def validate_batch(entries: list[dict[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    duplicate_ids: list[str] = []
    row_results: list[dict[str, Any]] = []

    for entry in entries:
        journal_id = str(entry.get("journal_id", ""))
        if journal_id in seen:
            duplicate_ids.append(journal_id)
        seen.add(journal_id)
        row_results.append(validate_entry(entry))

    invalid_rows = [r for r in row_results if not r["valid_for_staging_research_only"]]
    batch_valid = len(invalid_rows) == 0 and len(duplicate_ids) == 0

    return {
        "batch_valid_for_research_staging": batch_valid,
        "row_count": len(entries),
        "valid_row_count": len(entries) - len(invalid_rows),
        "invalid_row_count": len(invalid_rows),
        "duplicate_ids": duplicate_ids,
        "row_results": row_results,
        "staging_write_allowed": False,
        "canonical_write_allowed": False,
        "canonical_data_writes": 0,
        "shadow_decision_allowed": False,
        "decision_layer_allowed": False,
        "edge_validated": False,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
    }

def _project() -> Path:
    cwd = Path.cwd()
    return cwd if cwd.name == "crypto_decision_lab" else cwd / "crypto_decision_lab"

def build_phase58(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase58_journal_batch_staging_validator_research_only"
    out.mkdir(parents=True, exist_ok=True)

    batch_validation = validate_batch(SAMPLE_BATCH)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "batch_validation": batch_validation,
        **LOCKS,
    }

    (out / "phase58_journal_batch_staging_validator.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase58_sample_batch.json").write_text(
        json.dumps(SAMPLE_BATCH, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "index.html").write_text(
        f"""
<html>
<body>
<h1>QRDS Phase 58</h1>
<p>{READY_GATE}</p>
<p>Operational: BLOCKED_RESEARCH_ONLY</p>
<p>Edge: False</p>
<p>Shadow decision allowed: False</p>
<p>Decision layer allowed: False</p>
<p>canonical_data_writes: 0</p>
</body>
</html>
""",
        encoding="utf-8",
    )
    return result

def main() -> int:
    result = build_phase58()
    print("QRDS Phase 58 • Journal Batch Staging Validator Research-Only")
    print(result["gate"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("Promotion allowed: False")
    print("canonical_data_writes: 0")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
