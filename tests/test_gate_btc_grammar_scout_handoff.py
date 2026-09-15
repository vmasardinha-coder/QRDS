import json
from tools.gate_btc_factory.grammar_scout_handoff import build_handoff


def proposal():
    return {
        "channel_id": "NEW_CROSS_ASSET_MECHANISM",
        "status": "SCOUTED_NOT_PREREGISTERED",
        "mechanism": "observable ex-ante cross-asset transmission",
        "required_new_data": ["A", "B"],
        "official_free_source_candidates": ["B3"],
        "economics_read": False,
        "may_change_existing_grammar": False,
    }


def scout():
    return {"mode":"IDEATION_ONLY_NO_ECONOMICS", "history_used_for_selection":False, "proposals":[proposal()]}


def test_emits_only_separate_preregistration_request():
    out = build_handoff(scout())
    assert out["mode"] == "OUTCOME_BLIND_HANDOFF_ONLY"
    assert out["request_count"] == 1
    r = out["requests"][0]
    assert r["status"] == "ELIGIBLE_FOR_SEPARATE_PREREGISTRATION_GATE"
    assert r["economics_read"] is False
    assert r["may_allocate_existing_h_id"] is False
    assert r["may_modify_existing_grammar"] is False
    assert r["may_receive_retroactive_credit"] is False
    assert out["safety"]["h1_h31_untouched"] is True


def test_append_only_signature_suppresses_repeat(tmp_path):
    first = build_handoff(scout())
    (tmp_path/"old.json").write_text(json.dumps(first), encoding="utf-8")
    second = build_handoff(scout(), tmp_path)
    assert second["request_count"] == 0


def test_fail_closed_if_outcome_blind_contract_broken():
    bad = scout(); bad["history_used_for_selection"] = True
    try:
        build_handoff(bad)
    except ValueError:
        return
    raise AssertionError("expected fail closed")
