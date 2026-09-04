from __future__ import annotations

import json
from pathlib import Path

from tools.gate_btc_factory import invalidated_discovery_first as mod


def contract(lookback=20):
    return {"standardization_lookback_sessions": lookback}


def fake_sessions(dates):
    return {d: object() for d in dates}


def test_structural_capacity_requires_two_halves():
    dates = [f"2025-01-{i:02d}" for i in range(1, 29)] + [f"2025-02-{i:02d}" for i in range(1, 28)]
    ok, reason = mod.structurally_eligible_for_discovery(fake_sessions(dates), contract())
    assert ok is False and reason == "LESS_THAN_TWO_CALENDAR_HALVES"


def test_structural_capacity_requires_min_trade_capacity_after_lookback():
    dates = [f"2025-01-{i:02d}" for i in range(1, 29)] + [f"2025-07-{i:02d}" for i in range(1, 29)]
    ok, reason = mod.structurally_eligible_for_discovery(fake_sessions(dates), contract(20))
    assert ok is False and reason.startswith("MAX_SIGNAL_CAPACITY_BELOW_MIN_TRADES")


def test_structural_capacity_passes_full_year_like_window():
    import pandas as pd
    dates = [d.strftime("%Y-%m-%d") for d in pd.bdate_range("2025-01-02", "2025-12-30")]
    ok, reason = mod.structurally_eligible_for_discovery(fake_sessions(dates), contract(20))
    assert ok is True and reason == "DISCOVERY_STRUCTURAL_CAPACITY_PASS"


def write_valid_evidence(runtime: Path, fid: str, c: dict, dataset_sha: str, result_status="SCIENTIFIC_REJECTION_DISCOVERY"):
    namespace=f"{mod.DISCOVERY_NAMESPACE}::{fid}"
    stem=namespace.replace("::","__")
    prereg={
        "namespace":namespace,
        "original_family_id":fid,
        "dataset_sha256":dataset_sha,
        "grammar_contract":c,
        "grammar_contract_mode":"EXACT_FROZEN_ORIGINAL",
        "discovery_window":{"start":mod.DISCOVERY_START,"end":mod.DISCOVERY_END},
        "replication_window_reserved":{"start":mod.REPLICATION_START,"end":mod.REPLICATION_END},
        "historical_observations_credited":0,
        "same_historical_window_rerun":False,
    }
    result={
        "namespace":namespace,
        "original_family_id":fid,
        "status":result_status,
        "discovery_window":{"start":mod.DISCOVERY_START,"end":mod.DISCOVERY_END},
        "replication_window_reserved":{"start":mod.REPLICATION_START,"end":mod.REPLICATION_END},
        "historical_observations_credited":0,
        "same_historical_window_rerun":False,
    }
    (runtime/"preregistrations").mkdir(parents=True,exist_ok=True)
    (runtime/"results").mkdir(parents=True,exist_ok=True)
    (runtime/"preregistrations"/f"{stem}.json").write_text(json.dumps(prereg),encoding="utf-8")
    (runtime/"results"/f"{stem}.json").write_text(json.dumps(result),encoding="utf-8")


def test_valid_existing_2025_rejection_is_preserved(tmp_path: Path):
    fid="H1962"; c=contract(160); sha="a"*64
    write_valid_evidence(tmp_path,fid,c,sha)
    row={"original_family_id":fid,"new_namespace":f"{mod.DISCOVERY_NAMESPACE}::{fid}","status":"SCIENTIFIC_REJECTION","attempts":1}
    assert mod.valid_existing_discovery(row,fid,c,tmp_path,sha) is True


def test_contaminated_v1_terminal_is_never_treated_as_valid_2025_discovery(tmp_path: Path):
    fid="H2218"; c=contract(160); sha="b"*64
    row={"original_family_id":fid,"new_namespace":f"RQ_FORWARD_UNSEEN_2025_2026_V1::{fid}","status":"SCIENTIFIC_REJECTION","attempts":2}
    assert mod.valid_existing_discovery(row,fid,c,tmp_path,sha) is False


def test_hash_or_contract_mismatch_forces_re_evaluation(tmp_path: Path):
    fid="H1962"; c=contract(160); sha="c"*64
    write_valid_evidence(tmp_path,fid,c,sha)
    row={"original_family_id":fid,"new_namespace":f"{mod.DISCOVERY_NAMESPACE}::{fid}","status":"SCIENTIFIC_REJECTION","attempts":1}
    assert mod.valid_existing_discovery(row,fid,c,tmp_path,"d"*64) is False
    assert mod.valid_existing_discovery(row,fid,contract(20),tmp_path,sha) is False


def test_waiting_replication_valid_evidence_is_preserved(tmp_path: Path):
    fid="H2000"; c=contract(160); sha="e"*64
    write_valid_evidence(tmp_path,fid,c,sha,"DISCOVERY_SURVIVOR_WAITING_INDEPENDENT_REPLICATION")
    row={"original_family_id":fid,"new_namespace":f"{mod.DISCOVERY_NAMESPACE}::{fid}","status":"WAITING_INDEPENDENT_REPLICATION_2026","attempts":1}
    assert mod.valid_existing_discovery(row,fid,c,tmp_path,sha) is True
