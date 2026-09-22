import json
from pathlib import Path


CONTRACT = Path("artifacts/gate_btc_2/EXPERIMENTAL_PROSPECTIVE_SHADOW_CONTRACT_20260922.json")


def load_contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_shadow_is_zero_credit_and_non_promotional():
    c = load_contract()
    assert c["historical_credit"] == 0
    assert c["retroactive_credit"] == 0
    assert c["promotion_authority"] is False
    assert c["allowed_transitions"]["to_survivor"].startswith("FORBIDDEN")
    assert c["allowed_transitions"]["to_execution"] == "FORBIDDEN"


def test_shadow_preserves_research_safety():
    c = load_contract()
    assert c["research_only"] is True
    assert c["shadow_only"] is True
    assert c["engine_feed"] is False
    assert c["orders"] == 0
    assert c["real_capital_brl"] == 0
    assert c["no_backfill"] is True
    assert c["no_retune"] is True


def test_admission_requires_forward_causality_and_frozen_rule():
    a = load_contract()["required_admission"]
    assert a["mechanism_frozen_before_d0"] is True
    assert a["direction_or_position_mapping_frozen_before_d0"] is True
    assert a["source_identity_valid"] is True
    assert a["timestamp_availability_valid_prospectively"] is True
    assert a["causal_execution_rule_defined"] is True
    assert a["same_hypothesis_clean_terminal_rejection_absent"] is True
    assert a["no_post_result_parameter_changes"] is True
    assert a["d0_first_observation_after_merged_activation"] is True


def test_clean_terminal_rejection_is_not_rescued():
    c = load_contract()
    assert "VALID_SCIENTIFIC_REJECTION_SAME_HYPOTHESIS" in c["ineligible_origin_classes"]
    assert "POST_RESULT_RETUNE" in c["ineligible_origin_classes"]
    assert "POST_RESULT_SIGN_FLIP" in c["ineligible_origin_classes"]


def test_missing_and_unavailable_evidence_never_gain_credit():
    o = load_contract()["observation_semantics"]
    assert o["duplicate_observation_credit"] == 0
    assert o["late_reconstruction_credit"] == 0
    assert o["missing_observation_policy"] == "RECORD_GAP_NO_CREDIT"
    assert o["unavailable_evidence_policy"] == "EXPLICIT_UNAVAILABLE_NEVER_NEUTRALIZED"


def test_contract_activates_no_families_yet():
    assert load_contract()["item_2_status"] == "CONTRACT_FROZEN_NO_FAMILIES_ACTIVATED"
