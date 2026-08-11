import json
from pathlib import Path

import pytest

from tools.gate_btc_v16b_prospective_seal import (
    CANDIDATE_ID,
    attach_delta,
    seal_self,
    validate_self_row,
)


def base_row(status="OK"):
    row = {
        "signal_date_utc": "2026-08-13",
        "entry_date_utc": "2026-08-14",
        "exit_date_utc": "2026-08-21",
        "candidate_id": CANDIDATE_ID,
        "model_hash": "m" * 64,
        "code_commit": "c" * 40,
        "input_data_hashes": {"pit": "a" * 64},
        "eligible_universe_count": 120,
        "liquidity_qualified_count": 80,
        "shortable_count": 60,
        "longs_10": [f"L{i}" for i in range(10)],
        "shorts_10": [f"S{i}" for i in range(10)],
        "scores": {**{f"L{i}": 0.1 + i / 100 for i in range(10)}, **{f"S{i}": -0.1 - i / 100 for i in range(10)}},
        "exposure": 0.9,
        "trailing_vol": 0.22,
        "turnover": 0.8,
        "transaction_cost": 0.0012,
        "short_funding": {"S0USDT": 0.0001},
        "gross_long_pnl": 0.02,
        "gross_short_pnl": -0.005,
        "net_pnl": 0.0138,
        "btc_benchmark_return": 0.01,
        "source_coverage": {"pit": "OK", "prices": "OK", "shortability": "OK"},
        "status": status,
        "blocker_reason": None,
    }
    if status == "BLOCKED":
        row["blocker_reason"] = "missing required PIT source"
        for k in ["exposure", "trailing_vol", "turnover", "transaction_cost", "short_funding", "gross_long_pnl", "gross_short_pnl", "net_pnl", "btc_benchmark_return"]:
            row[k] = None
        row["longs_10"] = []
        row["shorts_10"] = []
        row["scores"] = {}
    return row


def write_json(tmp_path: Path, row):
    p = tmp_path / "row.json"
    p.write_text(json.dumps(row), encoding="utf-8")
    return p


def test_valid_first_prospective_week_seals(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    event = seal_self(write_json(tmp_path, base_row()), ledger)
    assert event["event_type"] == "V16B_SELF_RESULT_SEAL"
    assert event["ORDERS"] == 0
    assert event["REAL_CAPITAL"] == 0
    assert event["ENGINE_FEED"] is False
    assert len(event["seal_sha256"]) == 64


def test_rejects_pre_freeze_backfill():
    row = base_row()
    row.update(signal_date_utc="2026-08-06", entry_date_utc="2026-08-07", exit_date_utc="2026-08-14")
    with pytest.raises(ValueError, match="backfilled signal"):
        validate_self_row(row)


def test_rejects_external_delta_in_initial_seal():
    row = base_row()
    row["external_delta_print"] = 0.0724
    with pytest.raises(ValueError, match="external Delta is forbidden"):
        validate_self_row(row)


def test_blocked_row_cannot_carry_synthetic_pnl():
    row = base_row("BLOCKED")
    row["net_pnl"] = 0.0
    with pytest.raises(ValueError, match="BLOCKED row must not contain synthetic"):
        validate_self_row(row)


def test_blocked_row_is_valid_without_economics():
    event = validate_self_row(base_row("BLOCKED"))
    assert event["status"] == "BLOCKED"
    assert event["net_pnl"] is None


def test_append_only_rejects_duplicate_signal(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    inp = write_json(tmp_path, base_row())
    seal_self(inp, ledger)
    with pytest.raises(ValueError, match="already sealed"):
        seal_self(inp, ledger)


def test_delta_can_only_be_attached_after_self_seal(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    with pytest.raises(ValueError, match="only after exactly one sealed"):
        attach_delta("2026-08-13", 0.01, "2026-08-22T00:00:00Z", "source", ledger)

    seal_self(write_json(tmp_path, base_row()), ledger)
    event = attach_delta("2026-08-13", 0.01, "2026-08-22T00:00:00Z", "source", ledger)
    assert event["event_type"] == "EXTERNAL_DELTA_ATTACHMENT"
    assert len(event["self_seal_sha256"]) == 64

    with pytest.raises(ValueError, match="already attached"):
        attach_delta("2026-08-13", 0.02, "2026-08-22T01:00:00Z", "source2", ledger)
