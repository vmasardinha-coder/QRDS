from __future__ import annotations

import json
import itertools
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


def test_v3_preregistration_is_finite_distinct_and_not_executable_yet() -> None:
    manifest = json.loads((ROOT / "research" / "b3_h_autonomous_science_v3_family_manifest.json").read_text(encoding="utf-8"))
    source = json.loads((ROOT / "research" / "b3_h_autonomous_science_v3_source_contract.json").read_text(encoding="utf-8"))

    rows = list(itertools.product(
        manifest["features"],
        manifest["directions"],
        manifest["decision_windows_minutes"],
        manifest["abs_z_thresholds"],
    ))
    assert len(rows) == 160
    assert len(set(rows)) == 160
    assert manifest["first_family_number"] == 2730
    assert manifest["last_family_number"] == 2889
    assert manifest["generation_count"] == 16
    assert manifest["data_dimension"] == "TICK_MICROSTRUCTURE"
    assert manifest["economics_start_allowed"] is False
    assert source["primary_source"]["provider"] == "B3"
    assert source["primary_source"]["role"] == "PRIMARY_SCIENTIFIC_SOURCE"
    assert source["economics_allowed_before_qualification_pass"] is False
    assert source["secondary_sources"][0]["provider"] == "MetaTrader5"
    assert source["secondary_sources"][0]["use"] == "CROSS_VALIDATION_ONLY"
    assert source["secondary_sources"][0]["primary_source"] is False

    v2_features = {row[0] for row in expanded_universe()}
    assert not (set(manifest["features"]) & v2_features)

    # Preregistration alone must never authorize the current evaluator to run H2730.
    with pytest.raises(RuntimeError, match="AUTONOMOUS_SCIENCE_GRAMMAR_EXHAUSTED"):
        build_generation(2730)
