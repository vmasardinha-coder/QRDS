from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase135_evidence_quality_batch_checkpoint_research_only import (
    build_checkpoint as build_evidence_quality_checkpoint,
)

READY_GATE = "PHASE136_EDGE_CANDIDATE_REGISTRY_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

EDGE_CANDIDATES = [
    {
        "candidate_id": "volatility_reversion_candidate",
        "market_scope": "BTC_PERP_RESEARCH_ONLY",
        "hypothesis": "Volatility expansion followed by mean reversion may be observable in replay data.",
        "candidate_status": "UNVALIDATED_RESEARCH_ONLY",
        "allowed_for_trading": False,
        "allowed_for_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "candidate_id": "range_breakout_candidate",
        "market_scope": "BTC_PERP_RESEARCH_ONLY",
        "hypothesis": "Range compression followed by breakout may be observable in replay data.",
        "candidate_status": "UNVALIDATED_RESEARCH_ONLY",
        "allowed_for_trading": False,
        "allowed_for_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "candidate_id": "liquidity_gap_candidate",
        "market_scope": "BTC_PERP_RESEARCH_ONLY",
        "hypothesis": "Liquidity gaps may correlate with abnormal short-horizon movement in replay data.",
        "candidate_status": "UNVALIDATED_RESEARCH_ONLY",
        "allowed_for_trading": False,
        "allowed_for_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
]

def build_edge_candidate_registry(project_root: str | Path | None = None) -> dict[str, Any]:
    evidence_quality = build_evidence_quality_checkpoint(project_root)

    invalid_candidates = [
        c for c in EDGE_CANDIDATES
        if c["allowed_for_trading"] is not False
        or c["allowed_for_decision"] is not False
        or c["candidate_status"] != "UNVALIDATED_RESEARCH_ONLY"
        or c["operational_effect"] != "NONE_RESEARCH_ONLY"
    ]

    registry_pass = (
        evidence_quality["checkpoint_pass"] is True
        and len(EDGE_CANDIDATES) == 3
        and len(invalid_candidates) == 0
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "registry_name": "edge_candidate_registry_research_only",
        "source_evidence_quality_gate": evidence_quality["gate"],
        "source_evidence_quality_pass": evidence_quality["checkpoint_pass"],
        "source_quality_score": evidence_quality["quality_score"],
        "source_threshold_label": evidence_quality["threshold_label"],
        "edge_candidates": EDGE_CANDIDATES,
        "candidate_count": len(EDGE_CANDIDATES),
        "invalid_candidate_count": len(invalid_candidates),
        "registry_pass": registry_pass,
        "edge_candidate_status": "CANDIDATE_REGISTRY_UNVALIDATED_RESEARCH_ONLY",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase136(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase136_edge_candidate_registry_research_only"
    out.mkdir(parents=True, exist_ok=True)

    registry = build_edge_candidate_registry()
    (out / "phase136_edge_candidate_registry.json").write_text(
        json.dumps(registry, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": registry["registry_pass"], "registry": registry, **LOCKS}

def main() -> int:
    result = build_phase136()
    registry = result["registry"]

    print(result["gate"])
    print("Registry pass:", registry["registry_pass"])
    print("Candidate count:", registry["candidate_count"])
    print("Invalid candidate count:", registry["invalid_candidate_count"])
    print("Edge candidate status:", registry["edge_candidate_status"])
    print("Source quality score:", registry["source_quality_score"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge validated: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if registry["registry_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
