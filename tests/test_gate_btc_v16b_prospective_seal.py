import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tools import gate_btc_v16b_prospective_seal as v16b

CANDIDATE_ID = v16b.CANDIDATE_ID


def utc(y, m, d, h=0):
    return datetime(y, m, d, h, tzinfo=timezone.utc)


def signal_row(status="OK"):
    scores = {f"A{i:02d}": float(20 - i) for i in range(20)}
    ranking = sorted(scores, key=lambda a: (-scores[a], a))
    row = {
        "signal_date_utc": "2026-08-13", "entry_date_utc": "2026-08-14", "candidate_id": CANDIDATE_ID,
        "model_hash": "b" * 64, "code_commit": "c" * 40, "input_data_hashes": {"pit": "d" * 64},
        "universe_snapshot_id": "snap", "universe_snapshot_available_at_utc": "2026-08-13T20:00:00Z",
        "panel_hash": "e" * 64, "model_state_hash": "f" * 64, "eligible_universe_count": 20,
        "liquidity_qualified_count": 20, "eligible_scores": scores, "score_ranking_desc": ranking,
        "preliminary_longs_10": ranking[:10], "source_coverage": {"pit": "OK"}, "status": status,
        "blocker_reason": None,
    }
    if status == "BLOCKED":
        row.update(eligible_scores={}, score_ranking_desc=[], preliminary_longs_10=[], blocker_reason="missing source")
    return row


def entry_row(sig, status="OK"):
    ranking, longs = sig["score_ranking_desc"], sig["preliminary_longs_10"]
    checked = [{"asset": a, "shortable": True, "evidence_ref": "ev"} for a in list(reversed(ranking))[:10]]
    shorts = [x["asset"] for x in checked]
    row = {
        "signal_date_utc": sig["signal_date_utc"], "entry_date_utc": sig["entry_date_utc"], "candidate_id": CANDIDATE_ID,
        "signal_seal_sha256": sig["seal_sha256"], "shortability_evidence_hash": "1" * 64,
        "shortability_checked_ranked": checked,
        "long_executability": {a: {"executable": True, "evidence_ref": "ev"} for a in longs},
        "longs_10": longs, "shorts_10": shorts, "entry_instruments": {a: a + "USDT" for a in longs + shorts},
        "exposure": 0.9, "trailing_vol": 0.22, "turnover_estimate": 0.8, "transaction_cost_bps": 15.0,
        "source_coverage": {"shortability": "OK"}, "status": status, "blocker_reason": None,
    }
    if status == "BLOCKED":
        row.update(longs_10=[], shorts_10=[], entry_instruments={}, exposure=None, trailing_vol=None,
                   turnover_estimate=None, transaction_cost_bps=None, blocker_reason="shortability unavailable")
    return row


def result_row(ent, status="OK"):
    longs, shorts, details = ent["longs_10"], ent["shorts_10"], []
    for asset in longs + shorts:
        side = "LONG" if asset in longs else "SHORT"
        weight = 0.05 * ent["exposure"] * (1 if side == "LONG" else -1)
        raw = 0.01
        details.append({
            "asset": asset, "side": side, "instrument": ent["entry_instruments"][asset],
            "entry_price": 100.0, "exit_price": 101.0, "raw_return": raw, "weight": weight,
            "weighted_pnl": weight * raw, "price_source_hash": "2" * 64,
        })
    funding = {a: 0.00001 for a in shorts}
    gl = sum(x["weighted_pnl"] for x in details if x["side"] == "LONG")
    gs = sum(x["weighted_pnl"] for x in details if x["side"] == "SHORT")
    cost = 0.0015 * ent["turnover_estimate"]
    net = gl + gs + sum(funding.values()) - cost
    row = {
        "signal_date_utc": ent["signal_date_utc"], "entry_date_utc": ent["entry_date_utc"],
        "exit_date_utc": "2026-08-21", "candidate_id": CANDIDATE_ID, "entry_seal_sha256": ent["seal_sha256"],
        "execution_ledger_hash": "3" * 64, "price_source_hashes": {"prices": "4" * 64},
        "per_asset_pnl": details, "transaction_cost": cost, "short_funding": funding,
        "funding_evidence_hash": "5" * 64, "gross_long_pnl": gl, "gross_short_pnl": gs, "net_pnl": net,
        "btc_benchmark_return": 0.02, "btc_entry_price": 100.0, "btc_exit_price": 102.0,
        "btc_source_hash": "6" * 64, "source_coverage": {"prices": "OK"}, "status": status,
        "blocker_reason": None,
    }
    if status == "BLOCKED":
        for k in ("transaction_cost", "short_funding", "gross_long_pnl", "gross_short_pnl", "net_pnl",
                  "btc_benchmark_return", "btc_entry_price", "btc_exit_price"):
            row[k] = None
        row["per_asset_pnl"] = []
        row["blocker_reason"] = "price source missing"
    return row


def write(tmp_path: Path, name, row):
    p = tmp_path / name
    p.write_text(json.dumps(row), encoding="utf-8")
    return p


def build_to_entry(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    se = v16b.seal_signal(write(tmp_path, "s.json", signal_row()), ledger, now=utc(2026, 8, 14, 1))
    ee = v16b.seal_entry(write(tmp_path, "e.json", entry_row(se)), ledger, now=utc(2026, 8, 14, 12))
    return ledger, se, ee


def test_staged_happy_path_and_delta(tmp_path):
    ledger, _, ee = build_to_entry(tmp_path)
    re = v16b.seal_result(write(tmp_path, "r.json", result_row(ee)), ledger, now=utc(2026, 8, 22, 1))
    assert re["event_type"] == "V16B_RESULT_SEAL"
    assert re["ORDERS"] == 0 and re["REAL_CAPITAL"] == 0 and re["ENGINE_FEED"] is False
    de = v16b.attach_delta("2026-08-13", 0.01, "2026-08-22T02:00:00Z", "source", ledger)
    assert de["result_seal_sha256"] == re["seal_sha256"]
    assert len(v16b.load_events(ledger)) == 4


def test_signal_must_be_created_in_pre_entry_window(tmp_path):
    with pytest.raises(ValueError, match="signal seal must be created"):
        v16b.seal_signal(write(tmp_path, "s.json", signal_row()), tmp_path / "l.jsonl", now=utc(2026, 8, 15, 1))


def test_signal_ranking_is_frozen_from_scores():
    row = signal_row()
    row["score_ranking_desc"][0], row["score_ranking_desc"][1] = row["score_ranking_desc"][1], row["score_ranking_desc"][0]
    with pytest.raises(ValueError, match="inconsistent with eligible_scores"):
        v16b.validate_signal_row(row, now=utc(2026, 8, 14, 1))


def test_entry_cannot_change_longs(tmp_path):
    ledger = tmp_path / "l.jsonl"
    se = v16b.seal_signal(write(tmp_path, "s.json", signal_row()), ledger, now=utc(2026, 8, 14, 1))
    row = entry_row(se)
    row["longs_10"][0], row["longs_10"][1] = row["longs_10"][1], row["longs_10"][0]
    with pytest.raises(ValueError, match="cannot change"):
        v16b.seal_entry(write(tmp_path, "e.json", row), ledger, now=utc(2026, 8, 14, 12))


def test_entry_short_selection_must_follow_frozen_bottom_up_rank(tmp_path):
    ledger = tmp_path / "l.jsonl"
    se = v16b.seal_signal(write(tmp_path, "s.json", signal_row()), ledger, now=utc(2026, 8, 14, 1))
    row = entry_row(se)
    row["shortability_checked_ranked"][0]["asset"] = se["score_ranking_desc"][0]
    with pytest.raises(ValueError, match="bottom-up ranking"):
        v16b.seal_entry(write(tmp_path, "e.json", row), ledger, now=utc(2026, 8, 14, 12))


def test_entry_must_be_sealed_before_entry_close(tmp_path):
    ledger = tmp_path / "l.jsonl"
    se = v16b.seal_signal(write(tmp_path, "s.json", signal_row()), ledger, now=utc(2026, 8, 14, 1))
    with pytest.raises(ValueError, match="before entry-day UTC close"):
        v16b.seal_entry(write(tmp_path, "e.json", entry_row(se)), ledger, now=utc(2026, 8, 15, 0))


def test_result_recomputes_net_pnl(tmp_path):
    ledger, _, ee = build_to_entry(tmp_path)
    row = result_row(ee)
    row["net_pnl"] += 0.001
    with pytest.raises(ValueError, match="net_pnl inconsistent"):
        v16b.seal_result(write(tmp_path, "r.json", row), ledger, now=utc(2026, 8, 22, 1))


def test_result_cannot_be_sealed_before_exit_close(tmp_path):
    ledger, _, ee = build_to_entry(tmp_path)
    with pytest.raises(ValueError, match="before exit-day UTC close"):
        v16b.seal_result(write(tmp_path, "r.json", result_row(ee)), ledger, now=utc(2026, 8, 21, 23))


def test_delta_requires_result_not_just_signal_or_entry(tmp_path):
    ledger, _, _ = build_to_entry(tmp_path)
    with pytest.raises(ValueError, match="requires exactly one V16B_RESULT_SEAL"):
        v16b.attach_delta("2026-08-13", 0.01, "2026-08-22T02:00:00Z", "source", ledger)


def test_legacy_one_stage_sealing_disabled(tmp_path):
    with pytest.raises(ValueError, match="legacy one-stage"):
        v16b.seal_self(write(tmp_path, "r.json", {}), tmp_path / "l.jsonl")
