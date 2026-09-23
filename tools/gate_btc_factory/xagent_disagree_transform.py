#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import statistics
from pathlib import Path
from typing import Any

FAMILY_ID = "F-XAGENT-DISAGREE"
BOUND_PRODUCERS = (
    "S-XSPOT-FLOW-01",
    "S-XTERM-CARRY-01",
    "S-XBREADTH-01",
)
MIN_AVAILABLE = 3


def stable_hash(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(payload).hexdigest()


def availability_ms(obs: dict[str, Any]) -> int:
    for key in ("available_after_ms", "capture_time_ms", "close_time_ms"):
        value = obs.get(key)
        if value is not None:
            return int(value)
    raise RuntimeError(f"MISSING_AVAILABILITY_TIMESTAMP:{obs.get('producer_id')}")


def _validated_component(obs: dict[str, Any]) -> tuple[bool, str | None, float | None, int | None]:
    producer = str(obs.get("producer_id"))
    if producer not in BOUND_PRODUCERS:
        return False, "UNBOUND_PRODUCER", None, None
    signal = obs.get("signal")
    if signal is None:
        return False, "SIGNAL_UNAVAILABLE", None, None
    try:
        x = float(signal)
    except (TypeError, ValueError):
        raise RuntimeError(f"NON_NUMERIC_SIGNAL:{producer}")
    if not math.isfinite(x) or x < -1.0 or x > 1.0:
        raise RuntimeError(f"SIGNAL_RANGE_VIOLATION:{producer}:{x}")
    if obs.get("economic_outcomes_read") is not False:
        raise RuntimeError(f"ECONOMICS_READ_VIOLATION:{producer}")
    if obs.get("engine_feed") is not False or int(obs.get("orders", 0)) != 0 or int(obs.get("real_capital", 0)) != 0:
        raise RuntimeError(f"SAFETY_VIOLATION:{producer}")
    if obs.get("no_backfill") is not True or obs.get("no_retune") is not True:
        raise RuntimeError(f"FROZEN_LOCK_VIOLATION:{producer}")
    return True, None, x, availability_ms(obs)


def aggregate(observations: list[dict[str, Any]]) -> dict[str, Any]:
    by_id: dict[str, dict[str, Any]] = {}
    for obs in observations:
        pid = str(obs.get("producer_id"))
        if pid in by_id:
            raise RuntimeError(f"DUPLICATE_PRODUCER:{pid}")
        by_id[pid] = obs

    available: list[dict[str, Any]] = []
    unavailable: list[dict[str, Any]] = []
    evidence_classes: set[str] = set()
    for pid in BOUND_PRODUCERS:
        obs = by_id.get(pid)
        if obs is None:
            unavailable.append({"producer_id": pid, "reason": "OBSERVATION_MISSING"})
            continue
        ok, reason, signal, avail_ms = _validated_component(obs)
        if not ok:
            unavailable.append({"producer_id": pid, "reason": reason})
            continue
        evidence = str(obs.get("evidence_class") or "")
        if not evidence:
            raise RuntimeError(f"MISSING_EVIDENCE_CLASS:{pid}")
        if evidence in evidence_classes:
            raise RuntimeError(f"DUPLICATE_EVIDENCE_CLASS:{evidence}")
        evidence_classes.add(evidence)
        available.append({
            "producer_id": pid,
            "evidence_class": evidence,
            "signal": signal,
            "available_after_ms": avail_ms,
            "record_sha256": obs.get("record_sha256"),
        })

    values = [float(c["signal"]) for c in available]
    available_count = len(values)
    unavailable_count = len(BOUND_PRODUCERS) - available_count
    feature_available_after_ms = max((int(c["available_after_ms"]) for c in available), default=None)
    for c in available:
        if int(c["available_after_ms"]) > int(feature_available_after_ms):
            raise RuntimeError("NON_CAUSAL_COMPONENT_TIMESTAMP")

    eligible = available_count >= MIN_AVAILABLE
    features = None
    if eligible:
        mean = statistics.fmean(values)
        pair_values = [abs(a - b) / 2.0 for a, b in itertools.combinations(values, 2)]
        n_pos = sum(x > 0 for x in values)
        n_neg = sum(x < 0 for x in values)
        features = {
            "available_count": available_count,
            "unavailable_count": unavailable_count,
            "availability_fraction": available_count / len(BOUND_PRODUCERS),
            "consensus_mean": mean,
            "consensus_abs": abs(mean),
            "disagreement_std": statistics.pstdev(values),
            "pairwise_disagreement": statistics.fmean(pair_values),
            "sign_split_fraction": min(n_pos, n_neg) / available_count,
        }

    rec = {
        "schema": "gate_btc_2.xagent_disagree_feature_state.v1",
        "family_id": FAMILY_ID,
        "status": "FEATURE_STATE_AVAILABLE" if eligible else "ABSTAIN_INSUFFICIENT_INDEPENDENT_SIGNALS",
        "binding_mode": "LATEST_PROSPECTIVE_OBSERVATIONS_AS_OF_FEATURE_AVAILABILITY",
        "bound_producers": list(BOUND_PRODUCERS),
        "minimum_available_signals": MIN_AVAILABLE,
        "available_components": available,
        "unavailable_components": unavailable,
        "feature_available_after_ms": feature_available_after_ms,
        "common_causal_timestamp_rule": "ALL_COMPONENT_AVAILABLE_AFTER_MS_LE_FEATURE_AVAILABLE_AFTER_MS_EQUALS_MAX_COMPONENT_AVAILABILITY",
        "historical_reconstruction": False,
        "backfill_used": False,
        "missing_to_zero_used": False,
        "new_normalization_used": False,
        "features": features,
        "threshold_applied": False,
        "economic_direction_assigned": False,
        "exposure_mapping_applied": False,
        "economic_outcomes_read": False,
        "scientific_credit": 0,
        "survivor_credit": 0,
        "promotion_authority": False,
        "engine_feed": False,
        "orders": 0,
        "real_capital": 0,
        "no_backfill": True,
        "no_retune": True,
        "h1_h31_untouched": True,
        "canonical_580_untouched": True,
    }
    rec["record_sha256"] = stable_hash(rec)
    return rec


def self_test() -> None:
    base = {
        "economic_outcomes_read": False,
        "engine_feed": False,
        "orders": 0,
        "real_capital": 0,
        "no_backfill": True,
        "no_retune": True,
    }
    obs = [
        dict(base, producer_id="S-XSPOT-FLOW-01", evidence_class="A", signal=1.0, available_after_ms=10, record_sha256="a"),
        dict(base, producer_id="S-XTERM-CARRY-01", evidence_class="B", signal=-1.0, available_after_ms=20, record_sha256="b"),
        dict(base, producer_id="S-XBREADTH-01", evidence_class="C", signal=0.0, available_after_ms=30, record_sha256="c"),
    ]
    d = aggregate(obs)
    assert d["status"] == "FEATURE_STATE_AVAILABLE"
    assert d["feature_available_after_ms"] == 30
    f = d["features"]
    assert f["consensus_mean"] == 0.0
    assert abs(f["disagreement_std"] - math.sqrt(2.0/3.0)) < 1e-12
    assert abs(f["pairwise_disagreement"] - (2.0/3.0)) < 1e-12
    assert abs(f["sign_split_fraction"] - (1.0/3.0)) < 1e-12
    assert d["threshold_applied"] is False
    assert d["economic_outcomes_read"] is False

    missing = aggregate(obs[:2])
    assert missing["status"] == "ABSTAIN_INSUFFICIENT_INDEPENDENT_SIGNALS"
    assert missing["features"] is None
    assert missing["missing_to_zero_used"] is False
    print("XAGENT_DISAGREE_TRANSFORM_SELF_TEST=PASS")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spot")
    ap.add_argument("--term")
    ap.add_argument("--breadth")
    ap.add_argument("--output")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        self_test()
        return 0
    if not all((a.spot, a.term, a.breadth, a.output)):
        ap.error("--spot --term --breadth --output required")
    observations = [json.loads(Path(p).read_text(encoding="utf-8")) for p in (a.spot, a.term, a.breadth)]
    d = aggregate(observations)
    Path(a.output).write_text(json.dumps(d, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": d["status"], "feature_available_after_ms": d["feature_available_after_ms"], "features": d["features"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
