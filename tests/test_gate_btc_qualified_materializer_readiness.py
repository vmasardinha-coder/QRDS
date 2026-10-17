from tools.gate_btc_factory.qualified_materializer_readiness import build
def test_existing_007_evidence_reconciles_qualified_families_without_credit():
 i={"families":[
 {"family_id":"XAGRAMMAR_62943307741A","qualified_sources":["B3","CVM"]},
 {"family_id":"XAGRAMMAR_728DC88D691B","qualified_sources":["B3","BCB"]}]}
 e={"families":{
 "XAGRAMMAR_62943307741A":{"status":"SOURCE_BLOCKED_NO_VERSIONED_PIT_VALUES","row_count":0,"blocker":"NO_VERSIONED_VALUES"},
 "XAGRAMMAR_728DC88D691B":{"status":"FEATURES_MATERIALIZED_OUTCOME_BLIND","row_count":122}}}
 o=build(i,e)
 assert o["ready_count"]==1 and o["blocked_count"]==1 and o["terminal_source_blocked_count"]==1
 a={x["family_id"]:x for x in o["families"]}
 assert a["XAGRAMMAR_728DC88D691B"]["materialized_feature_rows"]==122
 assert a["XAGRAMMAR_728DC88D691B"]["collection_started"] is False
 assert a["XAGRAMMAR_62943307741A"]["implementation_status"]=="TERMINAL_SOURCE_BLOCKED_PIT_VALUES"
 assert all(x["scientific_credit"]==0 for x in o["families"])


import copy
import hashlib
import json
from pathlib import Path
import pytest
from tools.gate_btc_factory.qualified_materializer_readiness import FOCUS_ID, build


def prereg_capture():
    prereg = json.loads(Path("artifacts/gate_btc_2/GRAMMAR_007_FOCUS_PROSPECTIVE_PREREG_20261006.json").read_text())
    capture = {"schema": "qrds.factory.grammar_007.focus_prospective_capture.v1", "family_id": FOCUS_ID,
               "activation_utc": prereg["activation_utc"], "captured_at_utc": "2026-10-12T21:25:08+00:00",
               "status": "NO_NEW_ELIGIBLE_PUBLICATION", "observations": [], "observation_count": 0,
               "collection_started": True, "scientific_credit": 0, "prospective_credit": 0,
               "promotion_authority": False, "outcomes_read": False, "economics_read": False,
               "safety": prereg["safety"].copy()}
    return prereg, seal(capture)


def seal(capture):
    capture = {k: v for k, v in capture.items() if k != "capture_sha256"}
    capture["capture_sha256"] = hashlib.sha256(json.dumps(capture, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return capture


def inputs():
    return ({"families": [{"family_id": FOCUS_ID, "qualified_sources": ["B3", "BCB"]}]},
            {"families": {FOCUS_ID: {"status": "FEATURES_MATERIALIZED_OUTCOME_BLIND", "row_count": 122}}})


def test_existing_verified_empty_collection_is_active_without_credit():
    intake, evidence = inputs()
    prereg, capture = prereg_capture()
    before = copy.deepcopy((intake, evidence, prereg, capture))
    row = build(intake, evidence, prereg, capture)["families"][0]
    assert row["collection_started"] is True
    assert row["prospective_observations_reported"] == 0
    assert row["next_action"] == "WAIT_NEXT_ELIGIBLE_OFFICIAL_PUBLICATION"
    assert row["scientific_credit"] == 0
    assert (intake, evidence, prereg, capture) == before


def test_preregistered_without_receipt_requires_start_not_new_preregistration():
    intake, evidence = inputs()
    prereg, _ = prereg_capture()
    row = build(intake, evidence, prereg)["families"][0]
    assert row["collection_started"] is False
    assert row["next_action"] == "START_PREREGISTERED_PROSPECTIVE_COLLECTION"


def test_capture_without_preregistration_is_rejected():
    intake, evidence = inputs()
    _, capture = prereg_capture()
    with pytest.raises(ValueError, match="requires its preregistration"):
        build(intake, evidence, None, capture)


def test_capture_hash_tamper_is_rejected():
    intake, evidence = inputs()
    prereg, capture = prereg_capture()
    capture["collection_started"] = False
    with pytest.raises(ValueError, match="hash mismatch"):
        build(intake, evidence, prereg, capture)


@pytest.mark.parametrize("key,value", [("family_id", "OTHER"), ("activation_utc", "2026-10-01T00:00:00Z"),
    ("scientific_credit", 1), ("prospective_credit", 1), ("outcomes_read", True),
    ("economics_read", True), ("promotion_authority", True), ("observation_count", 1),
    ("status", "PROSPECTIVE_OBSERVATIONS_CAPTURED"), ("captured_at_utc", "2026-10-05T00:00:00Z")])
def test_even_rehashed_invalid_capture_fails_closed(key, value):
    intake, evidence = inputs()
    prereg, capture = prereg_capture()
    capture[key] = value
    with pytest.raises(ValueError):
        build(intake, evidence, prereg, seal(capture))


def test_receipt_cannot_replace_missing_materializer_evidence():
    intake, _ = inputs()
    prereg, capture = prereg_capture()
    row = build(intake, None, prereg, capture)["families"][0]
    assert row["collection_started"] is False
    assert row["implementation_status"] == "SOURCE_MATERIALIZER_REQUIRED"
    assert row["scientific_credit"] == 0
