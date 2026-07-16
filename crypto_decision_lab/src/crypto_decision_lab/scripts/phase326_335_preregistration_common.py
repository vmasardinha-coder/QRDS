from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from crypto_decision_lab.scripts.phase316_325_negative_evidence_common import (
    LOCKS,
    PROPOSED_NEW_FAMILY_ID,
    PROPOSED_QUESTION_ID,
    REQUIRED_PORTAL_HEADINGS,
    ROOT,
    base_payload,
    canonical_hash,
    fingerprint,
    money_brl,
    parse_junit,
    read_json,
    render_simple_portal,
    require_portal_headings,
    validate_phase,
    write_json,
    write_summary,
    write_text,
)

BASELINE_PHASE325_HEAD = "221ed45d6e3e8676f3ff343588a6c613a512b755"
QUESTION = (
    "Can contemporaneous cross-exchange disagreement and derivatives-data "
    "quality identify periods when a directional research model should "
    "abstain, without predicting buy or sell direction?"
)
TARGET_ID = "ABSTAIN_RELIABILITY_FAILURE_H8_V1"
MAX_HYPOTHESIS_BUDGET = 12


def review_record(
    gate_id: str,
    label: str,
    passed: bool,
    evidence: Any,
    failure_code: str,
) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
        "failure_code": None if passed else failure_code,
        "waiver_allowed": False,
    }


def all_pass(records: Iterable[dict[str, Any]]) -> bool:
    values = list(records)
    return bool(values) and all(bool(item.get("passed")) for item in values)


__all__ = [
    "BASELINE_PHASE325_HEAD",
    "LOCKS",
    "MAX_HYPOTHESIS_BUDGET",
    "PROPOSED_NEW_FAMILY_ID",
    "PROPOSED_QUESTION_ID",
    "QUESTION",
    "REQUIRED_PORTAL_HEADINGS",
    "ROOT",
    "TARGET_ID",
    "all_pass",
    "base_payload",
    "canonical_hash",
    "fingerprint",
    "money_brl",
    "parse_junit",
    "read_json",
    "render_simple_portal",
    "require_portal_headings",
    "review_record",
    "validate_phase",
    "write_json",
    "write_summary",
    "write_text",
]
