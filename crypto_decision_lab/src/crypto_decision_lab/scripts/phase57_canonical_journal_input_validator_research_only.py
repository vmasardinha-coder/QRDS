from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime

READY_GATE = "PHASE57_CANONICAL_JOURNAL_INPUT_VALIDATOR_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

SAMPLE_VALID_ENTRY = {
    "journal_id": "journal-sample-001",
    "created_at_utc": "2026-07-06T12:00:00+00:00",
    "asset": "BTC",
    "venue": "research_manual",
    "hypothesis_id": "HYP-VOL-001",
    "observed_context": "Manual observation for paper-only replay.",
    "would_have_action": "paper_no_action",
    "paper_size_notional": 0,
    "entry_reference_price": 100000.0,
    "exit_reference_price": None,
    "fees_slippage_assumption": "Research-only placeholder.",
    "outcome_note": None,
    "research_only_ack": True,
}

def validate_journal_entry(entry: dict) -> dict:
    errors = []
    for field in REQUIRED:
        if field not in entry:
            errors.append(f"missing:{field}")

    if entry.get("research_only_ack") is not True:
        errors.append("research_only_ack_must_be_true")

    if entry.get("would_have_action") not in ALLOWED_ACTIONS:
        errors.append("action_must_be_paper_only")

    if not isinstance(entry.get("paper_size_notional"), (int, float)) or isinstance(entry.get("paper_size_notional"), bool):
        errors.append("paper_size_notional_must_be_number")

    if not isinstance(entry.get("entry_reference_price"), (int, float)) or isinstance(entry.get("entry_reference_price"), bool):
        errors.append("entry_reference_price_must_be_number")

    try:
        datetime.fromisoformat(str(entry.get("created_at_utc")).replace("Z", "+00:00"))
    except Exception:
        errors.append("created_at_utc_must_be_datetime")

    return {
        "valid_for_research_replay": len(errors) == 0,
        "errors": errors,
        "canonical_write_allowed": False,
        "shadow_decision_allowed": False,
        "decision_layer_allowed": False,
        "edge_validated": False,
        "canonical_data_writes": 0,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
    }

def build_phase57(output_dir: str | Path | None = None) -> dict:
    cwd = Path.cwd()
    project = cwd if cwd.name == "crypto_decision_lab" else cwd / "crypto_decision_lab"
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase57_canonical_journal_input_validator_research_only"
    out.mkdir(parents=True, exist_ok=True)

    validation = validate_journal_entry(SAMPLE_VALID_ENTRY)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "schema_required_fields": REQUIRED,
        "allowed_actions": sorted(ALLOWED_ACTIONS),
        "sample_validation": validation,
        **LOCKS,
    }

    (out / "phase57_canonical_journal_input_validator.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase57_sample_valid_journal_entry.json").write_text(
        json.dumps(SAMPLE_VALID_ENTRY, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "index.html").write_text(
        f"<html><body><h1>QRDS Phase 57</h1><p>{READY_GATE}</p><p>BLOCKED_RESEARCH_ONLY</p><p>canonical_data_writes: 0</p></body></html>",
        encoding="utf-8",
    )
    return result

def main() -> int:
    result = build_phase57()
    print("QRDS Phase 57 • Canonical Journal Input Validator Research-Only")
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
