import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/gate_btc_factory"))

from xagent_disagree_transform import aggregate


BASE = {
    "economic_outcomes_read": False,
    "engine_feed": False,
    "orders": 0,
    "real_capital": 0,
    "no_backfill": True,
    "no_retune": True,
}


def obs(pid, evidence, signal, ts):
    return dict(BASE, producer_id=pid, evidence_class=evidence, signal=signal, available_after_ms=ts, record_sha256=pid)


def trio(values=(1.0, -1.0, 0.0), times=(10, 20, 30)):
    return [
        obs("S-XSPOT-FLOW-01", "SPOT_PARTICIPATION_TAKER_FLOW", values[0], times[0]),
        obs("S-XTERM-CARRY-01", "DERIVATIVES_TERM_STRUCTURE_CARRY", values[1], times[1]),
        obs("S-XBREADTH-01", "SPOT_CROSS_SECTIONAL_BREADTH", values[2], times[2]),
    ]


def test_frozen_feature_formulas_exact():
    d = aggregate(trio())
    f = d["features"]
    assert d["status"] == "FEATURE_STATE_AVAILABLE"
    assert f["available_count"] == 3
    assert f["unavailable_count"] == 0
    assert f["availability_fraction"] == 1.0
    assert f["consensus_mean"] == 0.0
    assert f["consensus_abs"] == 0.0
    assert abs(f["disagreement_std"] - math.sqrt(2 / 3)) < 1e-12
    assert abs(f["pairwise_disagreement"] - 2 / 3) < 1e-12
    assert abs(f["sign_split_fraction"] - 1 / 3) < 1e-12


def test_temporal_binding_is_asof_max_without_reconstruction():
    d = aggregate(trio(values=(0.1, 0.2, 0.3), times=(100, 300, 200)))
    assert d["feature_available_after_ms"] == 300
    assert all(c["available_after_ms"] <= 300 for c in d["available_components"])
    assert d["historical_reconstruction"] is False
    assert d["backfill_used"] is False


def test_missing_third_signal_abstains_without_zero_fill():
    xs = trio()[:2]
    d = aggregate(xs)
    assert d["status"] == "ABSTAIN_INSUFFICIENT_INDEPENDENT_SIGNALS"
    assert d["features"] is None
    assert d["missing_to_zero_used"] is False
    assert d["unavailable_components"] == [{"producer_id": "S-XBREADTH-01", "reason": "OBSERVATION_MISSING"}]


def test_duplicate_evidence_class_fails_closed():
    xs = trio()
    xs[2]["evidence_class"] = xs[0]["evidence_class"]
    try:
        aggregate(xs)
        assert False, "expected duplicate evidence class failure"
    except RuntimeError as exc:
        assert "DUPLICATE_EVIDENCE_CLASS" in str(exc)


def test_range_violation_fails_closed():
    xs = trio(values=(0.1, 1.01, 0.2))
    try:
        aggregate(xs)
        assert False, "expected range failure"
    except RuntimeError as exc:
        assert "SIGNAL_RANGE_VIOLATION" in str(exc)


def test_no_threshold_direction_or_exposure_is_applied():
    d = aggregate(trio(values=(0.2, -0.3, 0.4)))
    assert d["threshold_applied"] is False
    assert d["economic_direction_assigned"] is False
    assert d["exposure_mapping_applied"] is False
    assert d["economic_outcomes_read"] is False
    assert d["scientific_credit"] == 0
    assert d["survivor_credit"] == 0
    assert d["engine_feed"] is False
    assert d["orders"] == 0
    assert d["real_capital"] == 0
