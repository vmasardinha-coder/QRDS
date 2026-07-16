from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase346_355_closure_navigation_common import (
    FAMILY_ID,
    ROOT,
    base_payload,
    fingerprint,
    phase_summary,
    read_json,
    validate_phase,
    write_json,
    write_summary,
)


def build(paths: list[Path], output_dir: Path) -> dict[str, Any]:
    items = [read_json(path) for path in paths]
    for phase, item in zip(range(346, 350), items):
        validate_phase(item, phase)
    p346, p347, p348, p349 = items
    if p346.get("negative_evidence_registered") is not True:
        raise RuntimeError("Negative evidence was not registered.")
    if p347.get("blocked_template_count") != 12 or p347.get("semantic_retests_blocked") is not True:
        raise RuntimeError("Retest blocklist is incomplete.")
    if p348.get("parameter_rescue_recommended") is not False:
        raise RuntimeError("Failure-cause audit recommended parameter rescue.")
    if p349.get("data_remediation_can_retroactively_rescue_family") is not False:
        raise RuntimeError("Data-limitation audit weakened closure integrity.")

    closure_basis = {
        "phase346": p346.get("artifact_fingerprint"),
        "phase347": p347.get("artifact_fingerprint"),
        "phase348": p348.get("artifact_fingerprint"),
        "phase349": p349.get("artifact_fingerprint"),
    }
    payload = base_payload(350, "ABSTENTION_CLOSURE_INTEGRITY_SEALED_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE350_ABSTENTION_CLOSURE_INTEGRITY_SEAL_READY_RESEARCH_ONLY",
            "family_id": FAMILY_ID,
            "closure_basis": closure_basis,
            "closure_fingerprint": fingerprint(closure_basis),
            "closure_sealed": True,
            "closure_reopen_allowed": False,
            "parameter_rescue_experiments_allowed": 0,
            "active_hypotheses": 0,
            "active_experiment_budget": 0,
            "historical_backfill_credit": 0,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase350_abstention_closure_integrity_seal.json", payload)
    write_summary(
        phase_summary(350, "abstention_closure_integrity_seal"),
        title="Phase 350 — Abstention Closure-integrity Seal",
        gate=payload["gate"],
        bullets=[
            f"Closure fingerprint: `{payload['closure_fingerprint']}`",
            "Closure sealed: `True`",
            "Closure reopen allowed: `False`",
            "Parameter-rescue experiments allowed: `0`",
            "Active experiment budget: `0`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    defaults = [
        ROOT / "artifacts/phase346_abstention_negative_evidence_registration_research_only/phase346_abstention_negative_evidence_registration.json",
        ROOT / "artifacts/phase347_abstention_retest_blocklist_research_only/phase347_abstention_retest_blocklist.json",
        ROOT / "artifacts/phase348_abstention_failure_cause_audit_research_only/phase348_abstention_failure_cause_audit.json",
        ROOT / "artifacts/phase349_abstention_data_limitation_audit_research_only/phase349_abstention_data_limitation_audit.json",
    ]
    for phase, default in zip(range(346, 350), defaults):
        parser.add_argument(f"--phase{phase}-artifact", type=Path, default=default)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/phase350_abstention_closure_integrity_seal_research_only")
    args = parser.parse_args()
    paths = [getattr(args, f"phase{phase}_artifact") for phase in range(346, 350)]
    payload = build(paths, args.output_dir)
    print(payload["gate"])
    print("Closure sealed:", payload["closure_sealed"])
    print("Active experiment budget:", payload["active_experiment_budget"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
