from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .phase199_205_research_batch_common import LOCKS, load_json, require_phase, utc_now, write_json, write_text


def build_phase204(checkpoint_path: Path, reproducibility_path: Path, causality_path: Path, output_dir: Path, documentation_path: Path | None = None) -> dict[str, Any]:
    checkpoint = load_json(checkpoint_path)
    reproducibility = load_json(reproducibility_path)
    causality = load_json(causality_path)
    require_phase(checkpoint, 200)
    require_phase(reproducibility, 202)
    require_phase(causality, 203)

    avg_provenance = 0.0
    dimensions = {
        "data_evidence_chain": 20 if checkpoint.get("data_trust_checkpoint_ready") else 0,
        "data_findings_transparency": 10 if "findings" in checkpoint else 0,
        "replay_reproducibility": 30 if reproducibility.get("reproducible") else 0,
        "causality_and_time_order": 30 if causality.get("causality_audit_passed") else 0,
        "safety_locks": 10 if checkpoint.get("locks", {}).get("operational_status") == "BLOCKED_RESEARCH_ONLY" else 0,
    }
    score = sum(dimensions.values())
    if score >= 90:
        band = "STRONG_RESEARCH_EVIDENCE_NO_APPROVAL"
    elif score >= 70:
        band = "MODERATE_RESEARCH_EVIDENCE_NO_APPROVAL"
    else:
        band = "INSUFFICIENT_RESEARCH_EVIDENCE"

    payload = {
        "schema": "qrds.phase204.shadow_replay_scorecard.v1",
        "phase": 204,
        "phase_status": "PASS_RESEARCH_ONLY",
        "scorecard_status": "SHADOW_REPLAY_EVIDENCE_SCORECARD_READY_RESEARCH_ONLY",
        "generated_at": utc_now(),
        "dimensions": dimensions,
        "evidence_score": score,
        "evidence_band": band,
        "data_finding_total": checkpoint.get("finding_total", 0),
        "reproducibility_passed": reproducibility.get("reproducible") is True,
        "causality_passed": causality.get("causality_audit_passed") is True,
        "scorecard_ready": True,
        "predictive_validity_established": False,
        "data_trust_validated": False,
        "promotion_allowed": False,
        "valid_for_decision": False,
        "operational_use_allowed": False,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "next_stage": "PHASE_205_FULL_INTEGRATION_TRACKING_CHECKPOINT_RESEARCH_ONLY",
        "locks": LOCKS,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase204_shadow_replay_evidence_scorecard.json", payload)
    if documentation_path:
        rows = [f"| {name} | {value} |" for name, value in dimensions.items()]
        write_text(documentation_path, "\n".join([
            "# Phase 204 - Shadow Replay Evidence Scorecard",
            "",
            "**Status:** `PASS_RESEARCH_ONLY`",
            "",
            f"- Evidence score: `{score}/100`",
            f"- Evidence band: `{band}`",
            f"- Data findings retained: `{payload['data_finding_total']}`",
            "",
            "| Dimension | Points |",
            "|---|---:|",
            *rows,
            "",
            "The scorecard summarizes evidence. It cannot approve decisions or trading.",
            "",
            "```text",
            "predictive_validity_established: False",
            "data_trust_validated: False",
            "promotion_allowed: False",
            "operational_status: BLOCKED_RESEARCH_ONLY",
            "```",
        ]))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint-path", type=Path, required=True)
    parser.add_argument("--reproducibility-path", type=Path, required=True)
    parser.add_argument("--causality-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--documentation-path", type=Path, required=True)
    args = parser.parse_args()
    payload = build_phase204(args.checkpoint_path, args.reproducibility_path, args.causality_path, args.output_dir, args.documentation_path)
    print("PHASE204_EVIDENCE_SCORECARD: PASS")
    print("Evidence score:", payload["evidence_score"])
    print("Evidence band:", payload["evidence_band"])
    print("Promotion allowed:", payload["promotion_allowed"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
