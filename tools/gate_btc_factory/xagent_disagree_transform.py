#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

MIN_AVAILABLE = 3
RANGE_MIN = -1.0
RANGE_MAX = 1.0


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _finite_signal(obs: dict[str, Any]) -> float | None:
    value = obs.get("signal")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("NON_NUMERIC_SIGNAL")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("NON_FINITE_SIGNAL")
    if value < RANGE_MIN or value > RANGE_MAX:
        raise ValueError("SIGNAL_RANGE_VIOLATION")
    return value


def transform(observations: list[dict[str, Any]]) -> dict[str, Any]:
    producer_ids: list[str] = []
    evidence_classes: list[str] = []
    available: list[tuple[str, float]] = []
    unavailable: list[str] = []

    for obs in observations:
        pid = str(obs.get("producer_id", ""))
        evidence = str(obs.get("evidence_class", ""))
        if not pid or not evidence:
            raise ValueError("MISSING_PRODUCER_ID_OR_EVIDENCE_CLASS")
        if pid in producer_ids:
            raise ValueError("DUPLICATE_PRODUCER_ID")
        producer_ids.append(pid)
        evidence_classes.append(evidence)
        signal = _finite_signal(obs)
        if signal is None:
            unavailable.append(pid)
        else:
            available.append((pid, signal))

    # Independence is represented prospectively by distinct preregistered evidence classes.
    # The transform does not infer or manufacture independence from numeric values.
    if len(set(evidence_classes)) != len(evidence_classes):
        raise ValueError("DUPLICATE_EVIDENCE_CLASS_FAIL_CLOSED")

    available_count = len(available)
    unavailable_count = len(unavailable)
    total_count = len(observations)
    availability_fraction = available_count / total_count if total_count else 0.0

    if available_count < MIN_AVAILABLE:
        return {
            "schema": "gate_btc_2.xagent_disagreement_observation.v1",
            "generated_at_utc": now(),
            "family_id": "F-XAGENT-DISAGREE",
            "status": "ABSTAIN_INSUFFICIENT_INDEPENDENT_SIGNALS",
            "available_count": available_count,
            "unavailable_count": unavailable_count,
            "availability_fraction": availability_fraction,
            "available_producers": [p for p, _ in available],
            "unavailable_producers": unavailable,
            "features": None,
            "economic_direction": None,
            "thresholds": None,
            "lookbacks": None,
            "exposure_mapping": None,
            "economic_outcomes_read": False,
            "economic_claim": False,
            "promotion_authority": False,
            "scientific_credit": 0,
            "survivor_credit": 0,
            "engine_feed": False,
            "orders": 0,
            "real_capital": 0,
            "no_retune": True,
            "no_backfill": True,
            "canonical_580_untouched": True,
            "h1_h31_untouched": True,
        }

    values = [v for _, v in available]
    mean = sum(values) / available_count
    variance = sum((x - mean) ** 2 for x in values) / available_count
    std = math.sqrt(variance)
    pairs = list(combinations(values, 2))
    pairwise = sum(abs(a - b) / 2.0 for a, b in pairs) / len(pairs) if pairs else 0.0
    n_positive = sum(v > 0 for v in values)
    n_negative = sum(v < 0 for v in values)
    sign_split = min(n_positive, n_negative) / available_count

    out = {
        "schema": "gate_btc_2.xagent_disagreement_observation.v1",
        "generated_at_utc": now(),
        "family_id": "F-XAGENT-DISAGREE",
        "status": "PROSPECTIVE_FEATURE_VECTOR_AVAILABLE",
        "available_count": available_count,
        "unavailable_count": unavailable_count,
        "availability_fraction": availability_fraction,
        "available_producers": [p for p, _ in available],
        "unavailable_producers": unavailable,
        "component_signals": {p: v for p, v in available},
        "features": {
            "available_count": available_count,
            "unavailable_count": unavailable_count,
            "availability_fraction": availability_fraction,
            "consensus_mean": mean,
            "consensus_abs": abs(mean),
            "disagreement_std": std,
            "pairwise_disagreement": pairwise,
            "sign_split_fraction": sign_split,
        },
        "economic_direction": None,
        "thresholds": None,
        "lookbacks": None,
        "exposure_mapping": None,
        "economic_outcomes_read": False,
        "economic_claim": False,
        "promotion_authority": False,
        "scientific_credit": 0,
        "survivor_credit": 0,
        "engine_feed": False,
        "orders": 0,
        "real_capital": 0,
        "no_retune": True,
        "no_backfill": True,
        "canonical_580_untouched": True,
        "h1_h31_untouched": True,
    }
    canonical = json.dumps(out, sort_keys=True, separators=(",", ":")).encode()
    out["record_sha256"] = hashlib.sha256(canonical).hexdigest()
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    observations = [json.loads(Path(p).read_text(encoding="utf-8")) for p in args.inputs]
    result = transform(observations)
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "available_count": result["available_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
