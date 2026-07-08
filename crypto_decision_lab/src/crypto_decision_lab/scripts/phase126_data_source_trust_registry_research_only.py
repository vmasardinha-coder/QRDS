from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE126_DATA_SOURCE_TRUST_REGISTRY_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

DATA_SOURCES = [
    {
        "source_id": "public_exchange_market_data",
        "source_type": "market_data",
        "allowed_for_research": True,
        "allowed_for_decision": False,
        "trust_tier": "candidate_research_only",
        "required_checks": ["timestamp_present", "symbol_present", "price_present", "volume_present"],
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "source_id": "offline_fixture_data",
        "source_type": "fixture",
        "allowed_for_research": True,
        "allowed_for_decision": False,
        "trust_tier": "test_fixture_only",
        "required_checks": ["manifest_present", "deterministic_payload", "no_live_orders"],
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "source_id": "derived_replay_evidence",
        "source_type": "derived_evidence",
        "allowed_for_research": True,
        "allowed_for_decision": False,
        "trust_tier": "derived_research_only",
        "required_checks": ["source_trace_present", "replay_gate_present", "no_signal_export"],
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "source_id": "manual_review_notes",
        "source_type": "human_review",
        "allowed_for_research": True,
        "allowed_for_decision": False,
        "trust_tier": "annotation_only",
        "required_checks": ["reviewer_present", "timestamp_present", "approval_effect_none"],
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
]

FORBIDDEN_DATA_EFFECTS = [
    "decision_authority",
    "edge_validation",
    "trading_signal_generation",
    "allocation_generation",
    "recommendation_generation",
    "safe_apply",
    "promotion",
    "canonical_write",
]

def build_data_source_trust_registry(project_root: str | Path | None = None) -> dict[str, Any]:
    allowed_sources = [source for source in DATA_SOURCES if source["allowed_for_research"] is True]
    decision_sources = [source for source in DATA_SOURCES if source["allowed_for_decision"] is True]
    bad_effects = [
        source for source in DATA_SOURCES
        if source["operational_effect"] != "NONE_RESEARCH_ONLY"
    ]

    registry_pass = (
        len(DATA_SOURCES) == 4
        and len(allowed_sources) == 4
        and len(decision_sources) == 0
        and len(bad_effects) == 0
        and len(FORBIDDEN_DATA_EFFECTS) == 8
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "registry_name": "data_source_trust_registry_research_only",
        "sources": DATA_SOURCES,
        "source_count": len(DATA_SOURCES),
        "allowed_research_source_count": len(allowed_sources),
        "decision_source_count": len(decision_sources),
        "forbidden_data_effects": FORBIDDEN_DATA_EFFECTS,
        "registry_pass": registry_pass,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "data_trust_status": "CANDIDATE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase126(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase126_data_source_trust_registry_research_only"
    out.mkdir(parents=True, exist_ok=True)

    registry = build_data_source_trust_registry()
    (out / "phase126_data_source_trust_registry.json").write_text(
        json.dumps(registry, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "gate": READY_GATE,
        "ready": registry["registry_pass"],
        "registry": registry,
        **LOCKS,
    }

def main() -> int:
    result = build_phase126()
    registry = result["registry"]

    print(result["gate"])
    print("Registry pass:", registry["registry_pass"])
    print("Source count:", registry["source_count"])
    print("Decision source count:", registry["decision_source_count"])
    print("Data trust status:", registry["data_trust_status"])
    print("Approval effect:", registry["approval_effect"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if registry["registry_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
