from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("evidence_factory", ROOT / "tools/gate_btc_2_evidence_factory.py")
assert SPEC and SPEC.loader
EF = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EF)


def h(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def candidate(required=None):
    return {
        "schema": EF.SCHEMA_CANDIDATE,
        "candidate_id": "H-TEST-001",
        "candidate_version": 1,
        "hypothesis_sha256": h("hypothesis"),
        "config_sha256": h("config"),
        "code_sha256": h("code"),
        "cutoff_utc": "2026-08-27T00:00:00Z",
        "d0_utc": "2026-08-28T00:00:00Z",
        "source_identity": {"venue": "TEST", "instrument": "BTC"},
        "strategy_factory_artifact_sha256": h("factory-artifact"),
        "required_evidence": required or list(EF.EVIDENCE_ORDER),
        "safety": dict(EF.SAFETY),
    }


def passed(name: str):
    return {
        "evidence_type": name,
        "status": "PASS",
        "artifact": f"artifact/{name}.json",
        "artifact_sha256": h(name),
        "authority": "canonical-test-authority",
        "retuned": False,
        "backfilled_as_prospective": False,
        "silent_source_substitution": False,
    }


def test_a0_checklist_is_deterministic_and_binds_candidate():
    c = candidate()
    first = EF.build_checklist(c)
    second = EF.build_checklist(c)
    assert first == second
    assert first["candidate_binding_sha256"] == EF.canonical_hash(c)
    assert [x["evidence_type"] for x in first["requirements"]] == list(EF.EVIDENCE_ORDER)
    assert first["safety"] == EF.SAFETY


def test_a0_rejects_safety_drift_and_missing_frozen_hash():
    c = candidate()
    c["safety"]["NO_RETUNE"] = False
    with pytest.raises(RuntimeError, match="safety boundary drift"):
        EF.build_checklist(c)
    c = candidate()
    c["hypothesis_sha256"] = ""
    with pytest.raises(RuntimeError, match="hypothesis_sha256 invalid"):
        EF.build_checklist(c)


def test_a1_missing_pit_is_collect_more_not_pass():
    result = EF.assess(candidate(), [])
    assert result["decision"] == "COLLECT_MORE"
    assert result["next_state"] == "PIT_REQUIRED"


def test_a1_negative_evidence_closes_frozen_hypothesis_without_retune():
    record = passed("PIT")
    record["status"] = "FAIL"
    result = EF.assess(candidate(["PIT", "SURVIVORSHIP"]), [record])
    assert result["decision"] == "FAIL"
    assert result["next_state"] == "HYPOTHESIS_REFUTED"
    assert result["safety"]["NO_RETUNE"] is True


def test_a1_forbids_backfill_and_silent_source_substitution():
    record = passed("PROSPECTIVE")
    record["backfilled_as_prospective"] = True
    with pytest.raises(RuntimeError, match="backfilled prospective evidence forbidden"):
        EF.assess(candidate(["PROSPECTIVE"]), [record])
    record = passed("PROSPECTIVE")
    record["silent_source_substitution"] = True
    with pytest.raises(RuntimeError, match="silent source substitution forbidden"):
        EF.assess(candidate(["PROSPECTIVE"]), [record])


def test_a2_adapter_inventory_references_existing_authorities():
    inventory = EF.adapter_inventory(ROOT)
    assert inventory["PIT_SURVIVORSHIP_STRESS"]["present"] is True
    assert inventory["SOURCE_ADMISSION"]["present"] is True
    assert inventory["COLLECTOR_HEALTH"]["present"] is True
    assert inventory["COLLECTOR_HEALTH"]["registry_present"] is True
    assert all(row["sha256"] for row in inventory.values())


def test_a3_valid_transition_is_hash_linked_and_terminal_is_immutable():
    csha = EF.canonical_hash(candidate())
    first = EF.transition(csha, "RESEARCH_CANDIDATE", "FROZEN_HYPOTHESIS", "freeze")
    second = EF.transition(csha, "FROZEN_HYPOTHESIS", "PIT_REQUIRED", "pit required", first["transition_sha256"])
    assert second["prior_transition_sha256"] == first["transition_sha256"]
    assert len(second["transition_sha256"]) == 64
    with pytest.raises(RuntimeError, match="terminal state is immutable"):
        EF.transition(csha, "HYPOTHESIS_REFUTED", "RESEARCH_CANDIDATE", "forbidden")


def test_a3_invalid_transition_fails_closed():
    with pytest.raises(RuntimeError, match="invalid transition"):
        EF.transition(EF.canonical_hash(candidate()), "FROZEN_HYPOTHESIS", "ECONOMICS_READY", "skip gates")


def test_a4_missing_stage9_forward_health_stays_collect_more():
    result = EF.collector_health_requirement(
        candidate(["PROSPECTIVE"]),
        collector_id="GATE_BTC_2_STAGE9_MICROSTRUCTURE",
        required_data=["funding", "open_interest", "perp_volume", "spot_volume"],
        source="frozen authorized public source identities",
        frequency="forward-only authorized capture",
        required_n=1,
        target_gate="PROSPECTIVE_EVIDENCE",
        earliest_decision_date="AFTER_FIRST_VALID_FORWARD_CAPTURE",
        health_payload=None,
    )
    assert result["decision"] == "COLLECT_MORE"
    assert result["collector_owned_by_evidence_factory"] is False
    assert result["prospective_credit_from_backfill"] == 0
    assert result["current_N"] is None


def test_a4_requires_health_and_counter_not_just_workflow_existence():
    health = {
        "schema": "qrds.factory.collector_health.v1",
        "safety": {"RESEARCH_ONLY": True, "SHADOW_ONLY": True, "NOT_APPROVED": True, "ORDERS": 0, "REAL_CAPITAL": 0, "ENGINE_FEED": False},
        "collectors": [{"collector_id": "TEST", "anomaly_class": None, "canonical_counter": 2}],
    }
    result = EF.collector_health_requirement(
        candidate(["PROSPECTIVE"]), "TEST", ["x"], "source", "daily", 3, "PROSPECTIVE_EVIDENCE", "2026-09-01", health
    )
    assert result["decision"] == "COLLECT_MORE"
    health["collectors"][0]["canonical_counter"] = 3
    assert EF.collector_health_requirement(
        candidate(["PROSPECTIVE"]), "TEST", ["x"], "source", "daily", 3, "PROSPECTIVE_EVIDENCE", "2026-09-01", health
    )["decision"] == "PASS"


def test_a5_full_evidence_ends_at_human_review_with_zero_capital():
    c = candidate()
    assessment = EF.assess(c, [passed(name) for name in EF.EVIDENCE_ORDER])
    assert assessment["decision"] == "PASS"
    assert assessment["next_state"] == "HUMAN_PROMOTION_REVIEW"
    projection = EF.executive_projection(c, assessment)
    assert projection["items"]["11"]["status"] == "HUMAN_PROMOTION_REVIEW"
    assert projection["automatic_promotion"] is False
    assert projection["engine_feed"] is False
    assert projection["orders"] == 0
    assert projection["real_capital_brl"] == 0
    assert set(projection["items"]) == {"1B", "6", "10", "11", "12", "13"}
