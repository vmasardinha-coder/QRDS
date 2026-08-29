from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location(
        "factory_transition_runtime_test",
        ROOT / "tools/gate_btc_factory/plan_factory_transitions.py",
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_closed_runtime_frontier_advances_exactly_one_generation():
    m = load_module()
    action = m.build_next_generation_from_runtime({
        "generation": "H2720-H2729",
        "status": "CLOSED_NO_H2720_H2729_SURVIVOR",
        "survivors": [],
        "next_generation_start": 2730,
    })
    assert action is not None
    assert action["action"] == "CREATE_NEXT_GENERATION_ISSUE"
    assert action["track"] == "B3_H40_PLUS"
    assert action["marker"] == "B3 H2730-H2739"
    assert "H2720-H2729 closed" in action["body"]


def test_runtime_frontier_with_survivor_never_auto_advances():
    m = load_module()
    assert m.build_next_generation_from_runtime({
        "generation": "H2720-H2729",
        "status": "CLOSED_WITH_SURVIVOR",
        "survivors": ["H2724"],
        "next_generation_start": 2730,
    }) is None


def test_runtime_frontier_mismatch_fails_closed():
    m = load_module()
    assert m.build_next_generation_from_runtime({
        "generation": "H2720-H2729",
        "status": "CLOSED_NO_H2720_H2729_SURVIVOR",
        "survivors": [],
        "next_generation_start": 2740,
    }) is None


def test_already_active_survivor_is_not_reactivated():
    m = load_module()
    tracks = {
        "B3_H31": {
            "status": "APPROVED_FOR_SEPARATE_PROSPECTIVE_SOURCE_BINDING",
        }
    }
    registry = {
        "activations": {
            "B3_H31": {"state": "ACTIVE_PROSPECTIVE_SHADOW"},
        }
    }
    assert m.approved_activations(tracks, registry) == []


def test_unactivated_approved_survivor_still_gets_safe_activation():
    m = load_module()
    tracks = {
        "B3_H31": {
            "status": "APPROVED_FOR_SEPARATE_PROSPECTIVE_SOURCE_BINDING",
        }
    }
    actions = m.approved_activations(tracks, {"activations": {}})
    assert len(actions) == 1
    assert actions[0]["activation_state"] == "ACTIVE_PROSPECTIVE_SHADOW"
    assert actions[0]["orders"] == 0
    assert actions[0]["real_capital"] == 0
    assert actions[0]["engine_feed"] is False
