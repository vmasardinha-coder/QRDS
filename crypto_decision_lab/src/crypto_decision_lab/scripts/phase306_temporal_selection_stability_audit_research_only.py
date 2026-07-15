from __future__ import annotations

import argparse
import math
from collections import Counter
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase306_315_stability_common import (
    ROOT,
    base_payload,
    fingerprint,
    longest_run,
    normalized_entropy,
    read_json,
    validate_phase,
    write_json,
    write_phase_summary,
)


def build(phase304_path: Path, output_dir: Path) -> dict[str, Any]:
    phase304 = read_json(phase304_path)
    validate_phase(phase304, 304)
    history = [str(value) for value in phase304.get("selection_history", [])]
    if len(history) < 3:
        raise RuntimeError("Phase 304 selection history is too short for temporal audit.")

    counts = Counter(history)
    modal_id, modal_count = counts.most_common(1)[0]
    modal_share = modal_count / len(history)
    transitions = sum(left != right for left, right in zip(history, history[1:]))
    transition_rate = transitions / (len(history) - 1)
    split = len(history) // 2
    first_modal = Counter(history[:split]).most_common(1)[0][0]
    second_modal = Counter(history[split:]).most_common(1)[0][0]
    run = longest_run(history, modal_id)
    entropy = normalized_entropy(history)

    temporal_stability_pass = (
        bool(phase304.get("selection_stable"))
        and modal_share >= 0.70
        and first_modal == modal_id
        and second_modal == modal_id
        and transition_rate <= 0.30
        and run >= math.ceil(len(history) / 2)
    )
    reasons: list[str] = []
    if not phase304.get("selection_stable"):
        reasons.append("PHASE304_SELECTION_NOT_STABLE")
    if modal_share < 0.70:
        reasons.append("MODAL_SHARE_BELOW_70_PERCENT")
    if first_modal != second_modal:
        reasons.append("EARLY_AND_LATE_WINDOWS_DISAGREE")
    if transition_rate > 0.30:
        reasons.append("TOO_MANY_SELECTION_TRANSITIONS")
    if run < math.ceil(len(history) / 2):
        reasons.append("NO_LONG_CONTIGUOUS_MODAL_RUN")

    payload = base_payload(306, "TEMPORAL_SELECTION_STABILITY_AUDITED_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE306_TEMPORAL_SELECTION_STABILITY_AUDIT_READY_RESEARCH_ONLY",
            "phase304_artifact": phase304_path.relative_to(ROOT).as_posix(),
            "phase304_fingerprint": phase304.get("artifact_fingerprint"),
            "fold_count": len(history),
            "selection_history": history,
            "selection_counts": dict(sorted(counts.items())),
            "modal_hypothesis_id": modal_id,
            "modal_selection_share": modal_share,
            "transition_count": transitions,
            "transition_rate": transition_rate,
            "first_half_modal_hypothesis_id": first_modal,
            "second_half_modal_hypothesis_id": second_modal,
            "longest_modal_run": run,
            "normalized_selection_entropy": entropy,
            "temporal_stability_pass": temporal_stability_pass,
            "failure_reasons": reasons,
            "candidate_eligible_effect": "NONE_PHASE306_ONLY",
            "strategy_approved": False,
            "forward_shadow_eligible": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase306_temporal_selection_stability_audit.json", payload)
    write_phase_summary(
        ROOT / "docs/reports/stability_v2/phase306_temporal_selection_stability_audit_summary.md",
        title="Phase 306 — Temporal Selection Stability Audit",
        gate=payload["gate"],
        bullets=[
            f"Evaluated folds: `{len(history)}`",
            f"Modal hypothesis: `{modal_id}`",
            f"Modal share: `{modal_share:.2%}`",
            f"Selection transition rate: `{transition_rate:.2%}`",
            f"First-half modal: `{first_modal}`",
            f"Second-half modal: `{second_modal}`",
            f"Temporal stability pass: `{temporal_stability_pass}`",
            f"Failure reasons: `{', '.join(reasons) if reasons else 'NONE'}`",
            "Strategy approved: `False`",
        ],
    )
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase304-artifact",
        type=Path,
        default=ROOT / "artifacts/phase304_nested_walk_forward_v2_research_only/phase304_nested_walk_forward_v2.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "artifacts/phase306_temporal_selection_stability_audit_research_only",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build(args.phase304_artifact, args.output_dir)
    print(payload["gate"])
    print("Folds:", payload["fold_count"])
    print("Modal hypothesis:", payload["modal_hypothesis_id"])
    print("Modal share:", payload["modal_selection_share"])
    print("Temporal stability pass:", payload["temporal_stability_pass"])
    print("Strategy approved:", payload["strategy_approved"])
    print("Operational:", payload["locks"]["operational_status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
