import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/gate_btc_factory"))

from xagent_disagree_transform import transform


def obs(pid, evidence, signal):
    return {"producer_id": pid, "evidence_class": evidence, "signal": signal}


def test_three_independent_signals_emit_frozen_features_only():
    d = transform([
        obs("A", "E1", 0.2),
        obs("B", "E2", -0.1),
        obs("C", "E3", 0.5),
    ])
    assert d["status"] == "PROSPECTIVE_FEATURE_VECTOR_AVAILABLE"
    assert d["available_count"] == 3
    assert d["unavailable_count"] == 0
    assert d["availability_fraction"] == 1.0
    f = d["features"]
    assert f["consensus_mean"] == pytest.approx(0.2)
    assert f["consensus_abs"] == pytest.approx(0.2)
    expected_std = math.sqrt(((0.2-0.2)**2 + (-0.1-0.2)**2 + (0.5-0.2)**2) / 3)
    assert f["disagreement_std"] == pytest.approx(expected_std)
    expected_pairwise = (abs(0.2-(-0.1))/2 + abs(0.2-0.5)/2 + abs(-0.1-0.5)/2) / 3
    assert f["pairwise_disagreement"] == pytest.approx(expected_pairwise)
    assert f["sign_split_fraction"] == pytest.approx(1/3)
    assert d["economic_direction"] is None
    assert d["thresholds"] is None
    assert d["lookbacks"] is None
    assert d["exposure_mapping"] is None
    assert d["economic_outcomes_read"] is False
    assert d["economic_claim"] is False
    assert d["scientific_credit"] == 0
    assert d["engine_feed"] is False
    assert d["orders"] == 0
    assert d["real_capital"] == 0


def test_missing_signal_is_excluded_not_zero_filled_and_abstains_below_three():
    d = transform([
        obs("A", "E1", 0.3),
        obs("B", "E2", None),
        obs("C", "E3", -0.2),
    ])
    assert d["status"] == "ABSTAIN_INSUFFICIENT_INDEPENDENT_SIGNALS"
    assert d["available_count"] == 2
    assert d["unavailable_count"] == 1
    assert d["features"] is None
    assert d["unavailable_producers"] == ["B"]


def test_range_violation_fails_closed():
    with pytest.raises(ValueError, match="SIGNAL_RANGE_VIOLATION"):
        transform([obs("A", "E1", 1.1), obs("B", "E2", 0.0), obs("C", "E3", -0.1)])


def test_duplicate_producer_fails_closed():
    with pytest.raises(ValueError, match="DUPLICATE_PRODUCER_ID"):
        transform([obs("A", "E1", 0.1), obs("A", "E2", 0.2), obs("C", "E3", 0.3)])


def test_duplicate_evidence_class_fails_closed():
    with pytest.raises(ValueError, match="DUPLICATE_EVIDENCE_CLASS_FAIL_CLOSED"):
        transform([obs("A", "E1", 0.1), obs("B", "E1", 0.2), obs("C", "E3", 0.3)])
