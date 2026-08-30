from __future__ import annotations

import importlib.util
import json
from pathlib import Path

MOD = Path(__file__).parents[1] / "tools/gate_btc_factory/invalidated_family_requalification_runner.py"
spec = importlib.util.spec_from_file_location("rq", MOD)
rq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rq)


def policy():
    return {"trigger": {"historical_result_status": "HISTORICAL_RESULT_INVALIDATED_BY_MECHANICAL_DEFECT"}}


def root(ids):
    return {
        "root_cause_classification": "SOURCE_DATA_GAP",
        "root_cause_unresolved": False,
        "historical_integrity_status": "HISTORICAL_RESULT_INVALIDATED_BY_MECHANICAL_DEFECT",
        "affected_scope": {"family_ids": ids, "family_count": len(ids)},
    }


def contract(fid):
    return {
        "family_id": fid,
        "feature": "OPEN_RETURN",
        "decision_window_minutes": 20,
        "direction": "CONTINUATION",
        "abs_z_threshold": 1.5,
        "holding_horizons_minutes": [15, 30, 60],
        "standardization_lookback_sessions": 20,
        "causal_standardization": "ROLLING_20_PRIOR_SESSIONS_MEDIAN_MAD",
    }


def write_results(d: Path, ids):
    d.mkdir(parents=True)
    payload = {
        "generation": f"{ids[0]}-{ids[-1]}",
        "families": [{"family_id": fid, "contract": contract(fid)} for fid in ids],
    }
    (d / f"gate_btc_b3_h{ids[0][1:]}_h{ids[-1][1:]}_result.json").write_text(json.dumps(payload), encoding="utf-8")


def test_all_affected_families_are_queued(tmp_path):
    ids = ["H1962", "H1963", "H1964"]
    results = tmp_path / "results"
    write_results(results, ids)
    q = rq.build_queue(root(ids), policy(), results)
    assert q["affected_family_count"] == 3
    assert q["queued_family_count"] == 3
    assert [x["original_family_id"] for x in q["families"]] == ids
    assert all(x["status"] == "WAITING_SOURCE_QUALIFICATION" for x in q["families"])
    assert q["safety"]["no_backfill"] is True
    assert q["safety"]["orders"] == 0


def test_missing_frozen_contract_fails_closed(tmp_path):
    ids = ["H1962", "H1963"]
    results = tmp_path / "results"
    write_results(results, ["H1962"])
    try:
        rq.build_queue(root(ids), policy(), results)
    except RuntimeError as e:
        assert "MISSING_FROZEN_CONTRACTS" in str(e)
    else:
        raise AssertionError("missing contract must fail closed")


def test_source_gate_requires_unseen_pit_auditable_and_hash(tmp_path):
    data = tmp_path / "x.csv"
    data.write_text("timestamp,open,high,low,close,volume\n", encoding="utf-8")
    gate = {
        "qualified": True,
        "free_or_official_auditable": True,
        "publication_semantics_proven": True,
        "revision_semantics_proven": True,
        "identity_qa_pass": True,
        "schema_qa_pass": True,
        "point_in_time_valid": True,
        "independent_unseen_evaluation_data": True,
        "no_historical_backfill_credit": True,
        "economics_pre_read": False,
        "evaluation_namespace": "RQ1",
        "windows": {
            "discovery": {"start": "2025-01-01", "end": "2025-06-30"},
            "replication": {"start": "2025-07-01", "end": "2025-12-31"},
        },
        "dataset_sha256": rq.sha256(data),
    }
    ok, reason = rq.validate_source_gate(gate, data)
    assert ok is True and reason == "SOURCE_GATE_GREEN"
    gate["independent_unseen_evaluation_data"] = False
    ok, reason = rq.validate_source_gate(gate, data)
    assert ok is False and "independent_unseen" in reason


def test_prereg_keeps_exact_original_grammar_and_new_identity():
    c = contract("H1962")
    gate = {
        "evaluation_namespace": "REQUAL_2026A",
        "source_gate_id": "sg1",
        "dataset_sha256": "abc",
        "windows": {"discovery": {"start": "2025-01-01", "end": "2025-06-30"}, "replication": {"start": "2025-07-01", "end": "2025-12-31"}},
    }
    p = rq.prereg_for("H1962", c, gate)
    assert p["namespace"] == "REQUAL_2026A::H1962"
    assert p["original_family_id"] == "H1962"
    assert p["grammar_contract"] == c
    assert p["historical_family_mutated"] is False
    assert p["historical_observations_credited"] == 0
    assert p["safety"]["no_retune"] is True


def test_existing_terminal_results_are_idempotent(tmp_path):
    ids = ["H1962"]
    results = tmp_path / "results"
    write_results(results, ids)
    existing = {
        "families": [{
            "original_family_id": "H1962",
            "new_namespace": "RQ::H1962",
            "status": "SCIENTIFIC_REJECTION",
            "attempts": 1,
            "result_path": "x",
            "prospective_candidate_path": None,
        }]
    }
    q = rq.build_queue(root(ids), policy(), results, existing)
    assert q["families"][0]["status"] == "SCIENTIFIC_REJECTION"
    assert q["families"][0]["attempts"] == 1
