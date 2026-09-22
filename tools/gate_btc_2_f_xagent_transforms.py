#!/usr/bin/env python3
from __future__ import annotations

import math
import statistics

VALID_RISK_STATES = {"ALLOW", "VETO", "ABSTAIN_UNAVAILABLE"}


def disagreement_features(signals: list[float | None]) -> dict:
    available = []
    unavailable = 0
    for value in signals:
        if value is None:
            unavailable += 1
            continue
        x = float(value)
        if not math.isfinite(x) or x < -1.0 or x > 1.0:
            raise ValueError("signal must be finite and within [-1,1]")
        available.append(x)
    total = len(signals)
    if len(available) < 3:
        return {
            "eligible": False,
            "disposition": "ABSTAIN / INSUFFICIENT_INDEPENDENT_SIGNALS",
            "available_count": len(available),
            "unavailable_count": unavailable,
            "availability_fraction": len(available) / total if total else 0.0,
        }
    mean = statistics.fmean(available)
    pairs = [abs(a-b)/2.0 for i,a in enumerate(available) for b in available[i+1:]]
    pos = sum(x > 0 for x in available)
    neg = sum(x < 0 for x in available)
    return {
        "eligible": True,
        "disposition": "DISAGREEMENT_FEATURES_READY",
        "available_count": len(available),
        "unavailable_count": unavailable,
        "availability_fraction": len(available) / total if total else 0.0,
        "consensus_mean": mean,
        "consensus_abs": abs(mean),
        "disagreement_std": statistics.pstdev(available),
        "pairwise_disagreement": statistics.fmean(pairs),
        "sign_split_fraction": min(pos, neg) / len(available),
    }


def risk_veto_decision(states: list[str]) -> dict:
    if not states:
        raise ValueError("at least one risk assessor is required")
    bad = [s for s in states if s not in VALID_RISK_STATES]
    if bad:
        raise ValueError(f"invalid risk state: {bad[0]}")
    counts = {state: states.count(state) for state in sorted(VALID_RISK_STATES)}
    if counts["VETO"]:
        decision = "VETO"
    elif counts["ABSTAIN_UNAVAILABLE"]:
        decision = "ABSTAIN"
    else:
        decision = "ALLOW"
    n = len(states)
    return {
        "eligible": True,
        "aggregate_decision": decision,
        "assessor_count": n,
        "allow_count": counts["ALLOW"],
        "veto_count": counts["VETO"],
        "unavailable_count": counts["ABSTAIN_UNAVAILABLE"],
        "allow_fraction": counts["ALLOW"] / n,
        "veto_fraction": counts["VETO"] / n,
        "unavailable_fraction": counts["ABSTAIN_UNAVAILABLE"] / n,
    }
