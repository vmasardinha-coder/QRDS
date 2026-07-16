from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase316_325_negative_evidence_common import (
    CLOSED_FAMILY_ID, ROOT, base_payload, canonical_hash, fingerprint, hypothesis_signature,
    read_json, validate_phase, write_json, write_summary,
)


def build(phase303_path: Path, phase304_path: Path, phase311_path: Path, phase315_path: Path, output_dir: Path) -> dict[str, Any]:
    p303, p304, p311, p315 = map(read_json, (phase303_path, phase304_path, phase311_path, phase315_path))
    for phase, payload in ((303,p303),(304,p304),(311,p311),(315,p315)):
        validate_phase(payload, phase)
    if p315.get("current_family_decision") != "CLOSE_CURRENT_FAMILY_RESEARCH_ONLY":
        raise RuntimeError("Phase 315 did not close the current family.")
    hypotheses = list(p303.get("hypotheses", []))
    if len(hypotheses) != int(p303.get("experiment_budget", -1)) or len(hypotheses) != 24:
        raise RuntimeError("Closed family registry is incomplete or budget differs from 24.")
    signatures = [hypothesis_signature(item) for item in hypotheses]
    family_signature = canonical_hash([item["signature_sha256"] for item in signatures])
    payload = base_payload(316, "NEGATIVE_EVIDENCE_REGISTERED_RESEARCH_ONLY")
    payload.update({
        "gate": "PHASE316_NEGATIVE_EVIDENCE_REGISTRY_READY_RESEARCH_ONLY",
        "closed_family_id": CLOSED_FAMILY_ID,
        "closed_family_signature_sha256": family_signature,
        "hypothesis_count": len(hypotheses),
        "hypothesis_signature_count": len(signatures),
        "modal_hypothesis_id": p304.get("modal_hypothesis_id"),
        "mean_result_per_10000_brl": p304.get("outer_metrics_10bps",{}).get("mean_per_10000_brl"),
        "lower_95_per_10000_brl": p304.get("outer_metrics_10bps",{}).get("lower_95_per_10000_brl"),
        "failed_gate_ids": list(p311.get("failed_gate_ids", [])),
        "failed_gate_count": int(p311.get("failed_gate_count", 0)),
        "current_family_decision": p315.get("current_family_decision"),
        "negative_result_registered": True,
        "retest_unchanged_family_allowed": False,
        "experiment_budget_reopened": False,
        "new_hypotheses_registered": 0,
        "strategy_approved": False,
        "forward_shadow_eligible": False,
    })
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir/"phase316_negative_evidence_registry.json", payload)
    write_json(output_dir/"closed_family_signatures.json", {"family": CLOSED_FAMILY_ID, "family_signature_sha256": family_signature, "hypotheses": signatures})
    write_summary(ROOT/"docs/reports/negative_evidence/phase316_negative_evidence_registry_summary.md", title="Phase 316 — Negative Evidence Registry", gate=payload["gate"], bullets=[
        f"Closed family: `{CLOSED_FAMILY_ID}`", f"Registered negative hypotheses: `{len(hypotheses)}`",
        f"Failed eligibility gates: `{payload['failed_gate_count']}`", "Unchanged retest allowed: `False`",
        "Experiment budget reopened: `False`", "Capital used: `R$ 0`",
    ])
    return payload


def main() -> int:
    a=argparse.ArgumentParser(); art=ROOT/"artifacts"
    a.add_argument("--phase303-artifact",type=Path,default=art/"phase303_finite_hypothesis_registry_v2_research_only/phase303_finite_hypothesis_registry_v2.json")
    a.add_argument("--phase304-artifact",type=Path,default=art/"phase304_nested_walk_forward_v2_research_only/phase304_nested_walk_forward_v2.json")
    a.add_argument("--phase311-artifact",type=Path,default=art/"phase311_candidate_eligibility_contract_v2_research_only/phase311_candidate_eligibility_contract_v2.json")
    a.add_argument("--phase315-artifact",type=Path,default=art/"phase315_stability_family_checkpoint_research_only/phase315_stability_family_checkpoint.json")
    a.add_argument("--output-dir",type=Path,default=art/"phase316_negative_evidence_registry_research_only")
    x=a.parse_args(); p=build(x.phase303_artifact,x.phase304_artifact,x.phase311_artifact,x.phase315_artifact,x.output_dir)
    print(p["gate"]); print("Negative result registered:",p["negative_result_registered"]); print("Unchanged retest allowed:",p["retest_unchanged_family_allowed"]); print("Strategy approved:",p["strategy_approved"]); return 0
if __name__=="__main__": raise SystemExit(main())
