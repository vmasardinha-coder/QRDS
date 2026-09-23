from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping

ALLOWED_STATES = {"ALLOW", "VETO", "ABSTAIN_UNAVAILABLE"}


@dataclass(frozen=True)
class VetoAggregate:
    assessor_count: int
    allow_count: int
    veto_count: int
    unavailable_count: int
    allow_fraction: float
    veto_fraction: float
    unavailable_fraction: float
    aggregate_decision: str

    def as_dict(self) -> dict:
        return {
            "family_id": "F-XAGENT-VETO",
            "assessor_count": self.assessor_count,
            "allow_count": self.allow_count,
            "veto_count": self.veto_count,
            "unavailable_count": self.unavailable_count,
            "allow_fraction": self.allow_fraction,
            "veto_fraction": self.veto_fraction,
            "unavailable_fraction": self.unavailable_fraction,
            "aggregate_decision": self.aggregate_decision,
            "economic_direction": None,
            "position_size_mapping": None,
            "return_horizon": None,
            "economic_claim": False,
            "promotion_authority": False,
            "engine_feed": False,
            "orders": 0,
            "real_capital": 0,
            "no_retune": True,
            "no_backfill": True,
            "runtime_activation": False,
            "assessor_binding_required": True,
        }


def aggregate_assessor_states(states: Iterable[str]) -> VetoAggregate:
    values = list(states)
    if not values:
        raise ValueError("at least one assessor state is required")
    invalid = [value for value in values if value not in ALLOWED_STATES]
    if invalid:
        raise ValueError(f"invalid assessor state(s): {invalid}")

    counts = Counter(values)
    assessor_count = len(values)
    allow_count = counts["ALLOW"]
    veto_count = counts["VETO"]
    unavailable_count = counts["ABSTAIN_UNAVAILABLE"]

    if veto_count:
        aggregate_decision = "VETO"
    elif unavailable_count:
        aggregate_decision = "ABSTAIN"
    else:
        aggregate_decision = "ALLOW"

    return VetoAggregate(
        assessor_count=assessor_count,
        allow_count=allow_count,
        veto_count=veto_count,
        unavailable_count=unavailable_count,
        allow_fraction=allow_count / assessor_count,
        veto_fraction=veto_count / assessor_count,
        unavailable_fraction=unavailable_count / assessor_count,
        aggregate_decision=aggregate_decision,
    )


def aggregate_named_assessors(assessors: Mapping[str, str]) -> dict:
    if not assessors:
        raise ValueError("at least one concrete assessor is required")
    result = aggregate_assessor_states(assessors.values()).as_dict()
    result["assessor_ids"] = sorted(assessors)
    return result
