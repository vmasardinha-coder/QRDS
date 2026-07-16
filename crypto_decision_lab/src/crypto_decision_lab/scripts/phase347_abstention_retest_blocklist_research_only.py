from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase346_355_closure_navigation_common import (
    EXPECTED_TEMPLATE_COUNT,
    FAMILY_ID,
    ROOT,
    base_payload,
    canonical_json,
    fingerprint,
    phase_summary,
    read_json,
    validate_phase,
    write_json,
    write_summary,
)


def build(phase346_path: Path, phase336_path: Path, output_dir: Path) -> dict[str, Any]:
    p346 = read_json(phase346_path)
    p336 = read_json(phase336_path)
    validate_phase(p346, 346)
    validate_phase(p336, 336)
    templates = list(p336.get("active_templates", []))
    if len(templates) != EXPECTED_TEMPLATE_COUNT:
        raise RuntimeError(f"Expected {EXPECTED_TEMPLATE_COUNT} sealed templates, found {len(templates)}.")

    blocked: list[dict[str, Any]] = []
    seen: set[str] = set()
    for template in templates:
        template_id = str(template.get("template_id", "")).strip()
        if not template_id or template_id in seen:
            raise RuntimeError("Template IDs must be non-empty and unique.")
        seen.add(template_id)
        semantic_payload = {key: value for key, value in template.items() if key not in {"description", "label"}}
        blocked.append(
            {
                "template_id": template_id,
                "exact_retest_blocked": True,
                "semantic_signature": fingerprint(semantic_payload),
                "semantic_retest_blocked": True,
                "parameter_rescue_blocked": True,
                "canonical_definition": canonical_json(semantic_payload),
            }
        )

    payload = base_payload(347, "ABSTENTION_EXACT_AND_SEMANTIC_RETEST_BLOCKLIST_READY_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE347_ABSTENTION_RETEST_BLOCKLIST_READY_RESEARCH_ONLY",
            "family_id": FAMILY_ID,
            "blocked_templates": blocked,
            "blocked_template_count": len(blocked),
            "exact_retests_blocked": True,
            "semantic_retests_blocked": True,
            "parameter_rescue_allowed": False,
            "silent_registry_reopening_allowed": False,
            "new_experiment_budget": 0,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase347_abstention_retest_blocklist.json", payload)
    write_summary(
        phase_summary(347, "abstention_retest_blocklist"),
        title="Phase 347 — Abstention Retest Blocklist",
        gate=payload["gate"],
        bullets=[
            f"Exact templates blocked: `{len(blocked)}`",
            "Semantic retests blocked: `True`",
            "Parameter rescue blocked: `True`",
            "New experiment budget: `0`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase346-artifact", type=Path, default=ROOT / "artifacts/phase346_abstention_negative_evidence_registration_research_only/phase346_abstention_negative_evidence_registration.json")
    parser.add_argument("--phase336-artifact", type=Path, default=ROOT / "artifacts/phase336_finite_registry_opening_research_only/phase336_finite_registry_opening.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/phase347_abstention_retest_blocklist_research_only")
    args = parser.parse_args()
    payload = build(args.phase346_artifact, args.phase336_artifact, args.output_dir)
    print(payload["gate"])
    print("Blocked templates:", payload["blocked_template_count"])
    print("Semantic retests blocked:", payload["semantic_retests_blocked"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
