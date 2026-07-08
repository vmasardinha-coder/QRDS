from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase137_edge_candidate_eligibility_filter_research_only import (
    build_edge_candidate_eligibility_filter,
)

READY_GATE = "PHASE138_EDGE_CANDIDATE_EVIDENCE_LINKER_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

REQUIRED_EVIDENCE_LINKS = [
    "data_trust_batch_checkpoint",
    "evidence_quality_batch_checkpoint",
    "eligibility_filter",
]

def build_candidate_evidence_links(candidate_evaluations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    links = []

    for item in candidate_evaluations:
        candidate_id = item["candidate_id"]
        link_set = [
            {
                "link_id": f"{candidate_id}_data_trust",
                "evidence_type": "data_trust_batch_checkpoint",
                "gate": "PHASE130_DATA_TRUST_BATCH_CHECKPOINT_RESEARCH_ONLY_READY_RESEARCH_ONLY",
                "required": True,
                "present": True,
                "approval_effect": "NONE_RESEARCH_ONLY",
            },
            {
                "link_id": f"{candidate_id}_evidence_quality",
                "evidence_type": "evidence_quality_batch_checkpoint",
                "gate": "PHASE135_EVIDENCE_QUALITY_BATCH_CHECKPOINT_RESEARCH_ONLY_READY_RESEARCH_ONLY",
                "required": True,
                "present": True,
                "approval_effect": "NONE_RESEARCH_ONLY",
            },
            {
                "link_id": f"{candidate_id}_eligibility_filter",
                "evidence_type": "eligibility_filter",
                "gate": "PHASE137_EDGE_CANDIDATE_ELIGIBILITY_FILTER_RESEARCH_ONLY_READY_RESEARCH_ONLY",
                "required": True,
                "present": item["eligible_for_research"] is True,
                "approval_effect": "NONE_RESEARCH_ONLY",
            },
        ]

        missing = [link["evidence_type"] for link in link_set if link["required"] and not link["present"]]

        links.append(
            {
                "candidate_id": candidate_id,
                "evidence_links": link_set,
                "required_evidence_types": REQUIRED_EVIDENCE_LINKS,
                "missing_required_evidence": missing,
                "linked_for_research": len(missing) == 0,
                "linked_for_decision": False,
                "linked_for_trading": False,
                "operational_effect": "NONE_RESEARCH_ONLY",
            }
        )

    return links

def build_edge_candidate_evidence_linker(project_root: str | Path | None = None) -> dict[str, Any]:
    filt = build_edge_candidate_eligibility_filter(project_root)
    links = build_candidate_evidence_links(filt["candidate_evaluations"])

    failed_links = [item for item in links if item["linked_for_research"] is not True]
    decision_links = [item for item in links if item["linked_for_decision"] is True]
    trading_links = [item for item in links if item["linked_for_trading"] is True]

    linker_pass = (
        filt["filter_pass"] is True
        and len(links) == 3
        and len(failed_links) == 0
        and len(decision_links) == 0
        and len(trading_links) == 0
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "linker_name": "edge_candidate_evidence_linker_research_only",
        "source_filter_gate": filt["gate"],
        "source_filter_pass": filt["filter_pass"],
        "candidate_evidence_links": links,
        "linked_research_candidate_count": len([item for item in links if item["linked_for_research"] is True]),
        "decision_link_count": len(decision_links),
        "trading_link_count": len(trading_links),
        "failed_link_count": len(failed_links),
        "linker_pass": linker_pass,
        "edge_candidate_status": "EVIDENCE_LINKED_RESEARCH_ONLY_UNVALIDATED",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase138(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase138_edge_candidate_evidence_linker_research_only"
    out.mkdir(parents=True, exist_ok=True)

    result = build_edge_candidate_evidence_linker()
    (out / "phase138_edge_candidate_evidence_linker.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": result["linker_pass"], "linker": result, **LOCKS}

def main() -> int:
    result = build_phase138()
    linker = result["linker"]

    print(result["gate"])
    print("Linker pass:", linker["linker_pass"])
    print("Linked research candidate count:", linker["linked_research_candidate_count"])
    print("Decision link count:", linker["decision_link_count"])
    print("Trading link count:", linker["trading_link_count"])
    print("Failed link count:", linker["failed_link_count"])
    print("Edge candidate status:", linker["edge_candidate_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge validated: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if linker["linker_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
