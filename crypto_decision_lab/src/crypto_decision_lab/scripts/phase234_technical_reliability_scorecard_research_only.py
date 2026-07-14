from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase226_235_technical_reliability_common import (
    base_payload,
    load_json,
    write_json,
    write_markdown,
)


def build_technical_reliability_scorecard(
    artifact_paths: list[Path],
) -> dict[str, Any]:
    artifacts = [load_json(path) for path in artifact_paths]
    expected = list(range(226, 234))
    phases = [int(item["phase"]) for item in artifacts]
    controls = {
        f"phase_{item['phase']}": bool(item["passed"])
        for item in artifacts
    }
    score = round(
        100
        * sum(1 for value in controls.values() if value)
        / len(expected)
    )
    passed = bool(
        phases == expected
        and all(controls.values())
        and score == 100
    )
    classification = (
        "TECHNICAL_EXECUTION_RISK_CONTROLLED_RESEARCH_ONLY"
        if passed
        else "TECHNICAL_EXECUTION_RISK_NEEDS_REVIEW"
    )
    payload = base_payload(
        234,
        "TECHNICAL_RELIABILITY_SCORECARD_PASS_RESEARCH_ONLY"
        if passed
        else "TECHNICAL_RELIABILITY_SCORECARD_NEEDS_REVIEW",
    )
    payload.update(
        {
            "source_phases": phases,
            "controls": controls,
            "score": score,
            "classification": classification,
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
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--documentation", required=True)
    args = parser.parse_args()
    payload = build_technical_reliability_scorecard(
        [Path(path) for path in args.phase_artifact]
    )
    write_json(args.artifact, payload)
    write_markdown(
        args.documentation,
        "Phase 234 Technical Reliability Scorecard",
        payload,
        [
            f"- Score: `{payload['score']}/100`",
            f"- Classification: `{payload['classification']}`",
            "- Technical execution controls are separated from data trust and edge.",
        ],
    )
    print(payload["status"])
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
