from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "gate_btc_factory"))

from autonomous_family_generator import build_generation, expanded_universe, universe


def ident(f: dict) -> tuple:
    return (
        f["feature"],
        f["direction"],
        f["decision_window_minutes"],
        f["abs_z_threshold"],
        f["standardization_lookback_sessions"],
    )


def test_v1_is_immutable_prefix_and_v2_is_decade_aligned() -> None:
    assert len(universe()) == 256
    rows = expanded_universe()
    assert len(rows) == 2560
    assert len(rows) % 10 == 0
    assert len(set(rows)) == len(rows)
    assert all(x[4] == 20 for x in rows[:256])


def test_h420_crosses_v1_v2_boundary_without_gap_or_clone() -> None:
    d = build_generation(420)
    assert d["generation"] == "H420-H429"
    assert d["protocol"].endswith("protocol_v2.md")
    assert [x["family_id"] for x in d["families"]] == [f"H{i}" for i in range(420, 430)]
    assert [x["standardization_lookback_sessions"] for x in d["families"]] == [20] * 6 + [10] * 4
    assert len({ident(x) for x in d["families"]}) == 10


def test_h430_continues_v2_deterministically() -> None:
    a = build_generation(430)
    b = build_generation(430)
    assert a == b
    assert all(x["standardization_lookback_sessions"] == 10 for x in a["families"])
    prior = build_generation(420)
    assert not ({ident(x) for x in a["families"]} & {ident(x) for x in prior["families"]})


def test_full_v2_universe_ends_on_decade_boundary() -> None:
    last = build_generation(2720)
    assert last["generation"] == "H2720-H2729"
    assert len(last["families"]) == 10
    with pytest.raises(RuntimeError, match="AUTONOMOUS_SCIENCE_GRAMMAR_EXHAUSTED"):
        build_generation(2730)


def test_safety_boundary_unchanged() -> None:
    for start in (170, 420, 430, 2720):
        d = build_generation(start)
        assert d["frozen_before_economics"] is True
        assert d["h1_economics_read"] is False
        assert d["research_only"] is True
        assert d["shadow_only"] is True
        assert d["not_approved"] is True
        assert d["orders"] == 0
        assert d["real_capital"] == 0
        assert d["engine_feed"] is False
