from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from tools import gate_btc_momentum_m3_persistence as m3


def _source_payload(cutoff: str, n: int = 40, *, duplicate: bool = False, missing_r30: set[str] | None = None):
    missing_r30 = missing_r30 or set()
    rows = []
    for i in range(n):
        asset = f"A{i:03d}"
        row = {"asset": asset, "r30": float(n - i) / 100.0, "m1": 9999.0 - i, "rank_m1": i + 1}
        if asset in missing_r30:
            row.pop("r30")
        rows.append(row)
    if duplicate:
        rows.append(dict(rows[0]))
    payload = {
        "schema": "gate-btc-momentum-m1m2-prospective-snapshot-v1",
        "cutoff": cutoff,
        "classification": "PROSPECTIVE_SHADOW",
        "m1": {"rows": rows, "summary": {}},
        "m2": {"rows": [], "summary": {}},
        "safety": {
            "research_only": True,
            "shadow_only": True,
            "not_approved": True,
            "engine_feed": False,
            "orders": 0,
            "real_capital": 0,
        },
    }
    payload["snapshot_sha256"] = m3.canonical_sha(payload)
    return payload


def _write_source(root: Path, cutoff: str, **kwargs):
    payload = _source_payload(cutoff, **kwargs)
    (root / f"{cutoff}.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _three(root: Path, cutoff: str = "2026-09-10", **kwargs):
    d = date.fromisoformat(cutoff)
    for lag in (0, 7, 14):
        _write_source(root, (d - timedelta(days=lag)).isoformat(), **kwargs)


def test_deterministic_same_inputs_same_bytes(tmp_path: Path):
    _three(tmp_path)
    a = m3.compute(tmp_path, "2026-09-10")
    b = m3.compute(tmp_path, "2026-09-10")
    assert a == b
    assert a["snapshot_sha256"] == m3.canonical_sha(a)
    assert a["common_universe_n"] == 40
    assert a["selection_preview"] == [f"A{i:03d}" for i in range(10)]


def test_exact_t_minus_7_t_minus_14_required_no_nearest_substitution(tmp_path: Path):
    d = date.fromisoformat("2026-09-10")
    _write_source(tmp_path, d.isoformat())
    _write_source(tmp_path, (d - timedelta(days=6)).isoformat())
    _write_source(tmp_path, (d - timedelta(days=14)).isoformat())
    with pytest.raises(SystemExit, match="required canonical source snapshot missing"):
        m3.compute(tmp_path, "2026-09-10")


def test_future_snapshot_presence_cannot_change_output(tmp_path: Path):
    _three(tmp_path)
    before = m3.compute(tmp_path, "2026-09-10")
    _write_source(tmp_path, "2026-09-11")
    after = m3.compute(tmp_path, "2026-09-10")
    assert before == after
    assert "2026-09-11" not in after["source_cutoffs"]


def test_pre_freeze_and_same_day_freeze_are_rejected(tmp_path: Path):
    with pytest.raises(SystemExit, match="strictly after"):
        m3.compute(tmp_path, "2026-09-09")
    with pytest.raises(SystemExit, match="strictly after"):
        m3.compute(tmp_path, "2026-09-08")


def test_source_snapshot_hash_mismatch_fails_closed(tmp_path: Path):
    _three(tmp_path)
    path = tmp_path / "2026-09-03.json"
    payload = json.loads(path.read_text())
    payload["m1"]["rows"][0]["r30"] = 123.0
    path.write_text(json.dumps(payload))
    with pytest.raises(SystemExit, match="source snapshot hash mismatch"):
        m3.compute(tmp_path, "2026-09-10")


def test_duplicate_asset_fails_closed(tmp_path: Path):
    d = date.fromisoformat("2026-09-10")
    _write_source(tmp_path, d.isoformat())
    _write_source(tmp_path, (d - timedelta(days=7)).isoformat(), duplicate=True)
    _write_source(tmp_path, (d - timedelta(days=14)).isoformat())
    with pytest.raises(SystemExit, match="duplicate asset"):
        m3.compute(tmp_path, "2026-09-10")


def test_common_universe_below_30_fails_closed(tmp_path: Path):
    d = date.fromisoformat("2026-09-10")
    _write_source(tmp_path, d.isoformat(), n=40)
    _write_source(tmp_path, (d - timedelta(days=7)).isoformat(), n=40)
    _write_source(tmp_path, (d - timedelta(days=14)).isoformat(), n=29)
    with pytest.raises(SystemExit, match="common universe below frozen minimum"):
        m3.compute(tmp_path, "2026-09-10")


def test_m1_scores_do_not_affect_m3_only_r30_does(tmp_path: Path):
    _three(tmp_path)
    baseline = m3.compute(tmp_path, "2026-09-10")
    path = tmp_path / "2026-09-10.json"
    payload = json.loads(path.read_text())
    for row in payload["m1"]["rows"]:
        row["m1"] = -float(row["m1"])
        row["rank_m1"] = 999
    payload["snapshot_sha256"] = m3.canonical_sha(payload)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    changed = m3.compute(tmp_path, "2026-09-10")
    assert [r["asset"] for r in baseline["rows"]] == [r["asset"] for r in changed["rows"]]
    assert [r["m3"] for r in baseline["rows"]] == [r["m3"] for r in changed["rows"]]


def test_output_is_signal_only_and_safety_zero(tmp_path: Path):
    _three(tmp_path)
    payload = m3.compute(tmp_path, "2026-09-10")
    assert payload["economics_activated"] is False
    assert payload["retrospective_credit"] == 0
    assert payload["safety"] == {
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "promotion_eligible": False,
        "orders": 0,
        "real_capital": 0,
        "backfill": False,
        "late_seal": False,
        "counter_reset": False,
        "retune": False,
    }


def test_independent_ledger_duplicate_is_idempotent_but_mutation_rejected(tmp_path: Path):
    source = tmp_path / "source"
    ledger = tmp_path / "m3"
    output = tmp_path / "out.json"
    source.mkdir()
    _three(source)
    payload = m3.compute(source, "2026-09-10")
    m3.persist(payload, ledger, output)
    m3.persist(payload, ledger, output)
    target = ledger / "2026-09-10.json"
    mutated = json.loads(target.read_text())
    mutated["rows"][0]["m3"] += 0.01
    mutated["snapshot_sha256"] = m3.canonical_sha(mutated)
    target.write_text(json.dumps(mutated, indent=2, sort_keys=True) + "\n")
    with pytest.raises(SystemExit, match="different canonical payload"):
        m3.persist(payload, ledger, output)
