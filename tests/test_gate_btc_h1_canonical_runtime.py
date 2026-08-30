from pathlib import Path
import importlib.util

MOD=Path(__file__).parents[1]/"tools/gate_btc_factory/h1_canonical_runtime.py"
spec=importlib.util.spec_from_file_location("h1rt",MOD)
h1=importlib.util.module_from_spec(spec); spec.loader.exec_module(h1)
ANCHOR={"canonical_evidence":{"qualified":8,"last_candidate_date":"2026-08-28"}}


def test_anchor_starts_at_8_without_summing_other_ledger():
    o=h1.build(ANCHOR,None,"2026-08-28","qualified","STRUCTURAL_PASS","1")
    assert o["qualified"]==8
    assert o["remaining"]==12
    assert o["post_anchor_events"]==[]


def test_next_unique_pass_increments_once():
    o=h1.build(ANCHOR,None,"2026-08-31","qualified","STRUCTURAL_PASS","2")
    assert o["qualified"]==9 and o["remaining"]==11
    o2=h1.build(ANCHOR,o,"2026-08-31","qualified","STRUCTURAL_PASS","3")
    assert o2["qualified"]==9


def test_gap_never_increments():
    o=h1.build(ANCHOR,None,"2026-08-31","gap","SOURCE_FAILURE","2")
    assert o["qualified"]==8
    assert o["post_anchor_events"][0]["reason"]=="SOURCE_FAILURE"


def test_existing_below_anchor_cannot_regress():
    o=h1.build(ANCHOR,{"qualified":6},"2026-08-31","gap","OTHER","2")
    assert o["qualified"]==8


def test_20_freezes_collection_but_keeps_economics_locked_until_integrity_green():
    existing={"qualified":19,"post_anchor_events":[]}
    o=h1.build(ANCHOR,existing,"2026-09-01","qualified","STRUCTURAL_PASS","4")
    assert o["qualified"]==20
    assert o["economics_locked"] is True
    assert o["economics_unlock_requires_integrity_green"] is True
    assert o["collector_should_continue"] is False
    assert o["checkpoint_trigger_reached"] is True
