from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.gate_btc_factory import invalidated_source_qualification_search as mod


def test_existing_gate_is_strict_and_hash_bound(tmp_path: Path):
    runtime = tmp_path / "runtime"
    data = runtime / "factory_autonomy/invalidated_requalification/source_qualified/EVALUATION_DATA.csv"
    data.parent.mkdir(parents=True)
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
        "evaluation_namespace": "RQ_TEST",
        "dataset_sha256": hashlib.sha256(data.read_bytes()).hexdigest(),
        "dataset_relative_path": "runtime/factory_autonomy/invalidated_requalification/source_qualified/EVALUATION_DATA.csv",
        "windows": {
            "discovery": {"start": "2025-01-02", "end": "2025-05-30"},
            "replication": {"start": "2025-06-02", "end": "2025-12-12"},
        },
    }
    p = runtime / "factory_autonomy/invalidated_requalification/SOURCE_GATE.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(gate), encoding="utf-8")
    out = mod.validate_existing_gate(p, runtime)
    assert out["valid"] is True
    gate["dataset_sha256"] = "0" * 64
    p.write_text(json.dumps(gate), encoding="utf-8")
    assert mod.validate_existing_gate(p, runtime)["reason"] == "DATASET_HASH_MISMATCH"


def test_search_stays_fail_closed_without_strict_gate(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(mod, "_sample_response", lambda session, url: {
        "url": url, "reachable": True, "win_identity_hint": True, "csv_schema_hint": True
    })
    monkeypatch.setattr(mod, "_github_candidates", lambda session, token: [{
        "status": "SCHEMA_IDENTITY_CANDIDATE_STILL_PIT_UNQUALIFIED",
        "independent_of_invalidated_source": True,
    }])
    root = {
        "root_cause_classification": "SOURCE_DATA_GAP",
        "affected_scope": {"family_count": 768, "family_ids": ["H1962"]},
    }
    gate = tmp_path / "SOURCE_GATE.json"
    out = mod.search(root, gate, tmp_path, token="x")
    assert out["status"] == "ACTIVE_SEARCHING_QUALIFICATION"
    assert out["source_gate"]["valid"] is False
    assert out["definitive_data_gap_allowed"] is False
    assert out["qualification_policy"]["no_candidate_promoted_by_reachability_alone"] is True
    s = out["safety"]
    assert s["research_only"] and s["shadow_only"] and s["not_approved"]
    assert s["engine_feed"] is False and s["orders"] == 0 and s["real_capital"] == 0
    assert s["no_retune"] and s["no_backfill"] and s["no_counter_reset"] and s["fail_closed"]


def test_identity_hint_rejects_generic_win_words():
    prose = "How to win at localization. date time open price are configuration labels."
    assert mod._win_identity_hint(prose, "web/src/locales/en.ts") is False
    assert mod._intraday_schema_hint(prose) is False


def test_identity_and_schema_hints_accept_explicit_win_market_data():
    sample = "timestamp,open,high,low,close,volume\n2026-08-28T10:00:00-03:00,1,2,0,1,10\n"
    assert mod._win_identity_hint(sample, "data/WINFUT_5min.csv") is True
    assert mod._intraday_schema_hint(sample) is True
