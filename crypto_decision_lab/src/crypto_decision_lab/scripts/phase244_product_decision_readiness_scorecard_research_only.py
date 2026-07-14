from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase236_245_evidence_decision_readiness_common import (
    TECHNICAL_RELIABILITY_ARTIFACT,
    base_payload,
    load_json,
    project_root,
    write_json,
    write_markdown,
)


def build_product_decision_readiness_scorecard(
    artifacts: list[dict[str, Any]],
    technical_reliability: dict[str, Any],
) -> dict[str, Any]:
    phases = [int(item["phase"]) for item in artifacts]
    framework_controls = {
        f"phase_{item['phase']}": bool(item.get("passed"))
        for item in artifacts
    }
    framework_score = round(
        100
        * sum(1 for value in framework_controls.values() if value)
        / len(framework_controls)
    )
    technical_score = int(technical_reliability.get("score", 0))
    operational_score = 0
    evidence_admitted = bool(
        next(
            item
            for item in artifacts
            if int(item["phase"]) == 240
        ).get("evidence_admitted")
    )
    packet = next(
        item
        for item in artifacts
        if int(item["phase"]) == 243
    )["sample_packet"]

    passed = bool(
        phases == list(range(236, 244))
        and framework_score == 100
        and technical_score == 100
        and operational_score == 0
        and evidence_admitted is False
        and packet["action"] == "NO_ACTION_RESEARCH_ONLY"
    )
    classification = (
        "PRODUCT_DECISION_FRAMEWORK_READY_EVIDENCE_NOT_VALIDATED"
        if passed
        else "PRODUCT_DECISION_FRAMEWORK_NEEDS_REVIEW"
    )
    payload = base_payload(
        244,
        (
            "PRODUCT_DECISION_READINESS_SCORECARD_PASS_RESEARCH_ONLY"
            if passed
            else "PRODUCT_DECISION_READINESS_SCORECARD_NEEDS_REVIEW"
        ),
    )
    payload.update(
        {
            "source_phases": phases,
            "framework_controls": framework_controls,
            "framework_score": framework_score,
            "technical_reliability_score": technical_score,
            "operational_readiness_score": operational_score,
            "evidence_admitted": evidence_admitted,
            "sample_action": packet["action"],
            "classification": classification,
            "data_trust_validated": False,
            "predictive_validity_established": False,
            "edge_validated": False,
            "valid_for_decision": False,
            "passed": passed,
        }
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase-artifact",
        action="append",
        required=True,
    )
    parser.add_argument("--technical-artifact")
    parser.add_argument("--project-root")
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--documentation", required=True)
    args = parser.parse_args()

    root = project_root(args.project_root)
    technical_path = (
        Path(args.technical_artifact)
        if args.technical_artifact
        else root / TECHNICAL_RELIABILITY_ARTIFACT
    )
    payload = build_product_decision_readiness_scorecard(
        [load_json(path) for path in args.phase_artifact],
        load_json(technical_path),
    )
    write_json(args.artifact, payload)
    write_markdown(
        args.documentation,
        "Phase 244 Product Decision Readiness Scorecard",
        payload,
        [
            f"- Framework score: `{payload['framework_score']}/100`",
            f"- Technical reliability: "
            f"`{payload['technical_reliability_score']}/100`",
            f"- Operational readiness: "
            f"`{payload['operational_readiness_score']}/100`",
            f"- Classification: `{payload['classification']}`",
            "- The product decision schema is ready, but evidence is "
            "not yet admitted and no action is authorized.",
        ],
    )
    print(payload["status"])
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
