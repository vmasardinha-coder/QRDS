from types import SimpleNamespace
from datetime import datetime, timezone

from tools.gate_btc_factory import invalidated_512_mt5_strict_v2_probe as p


def info(name="WINV26", description="IBOVESPA MINI", path="BVMF-Derivatives\\WINV26", expiration_time=1797552000):
    return SimpleNamespace(name=name, description=description, path=path, expiration_time=expiration_time, trade_mode=4)


def meta(symbol, expiry):
    return {"symbol": symbol, "expiration_time": int(expiry.timestamp()), "description": "IBOVESPA MINI", "path": "BVMF-Derivatives"}


def rows(day, symbol="WINV26", n=40, gap_at=None, duplicate=False):
    start = datetime.fromisoformat(day + "T09:00:00-03:00")
    out = []
    for i in range(n):
        minute = i * 5
        if gap_at is not None and i >= gap_at:
            minute += 5
        ts = start.timestamp() + minute * 60
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(p.TZ)
        out.append({"symbol": symbol, "timestamp": dt.isoformat(), "epoch": int(ts), "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.0, "tick_volume": 1, "spread": 0, "real_volume": 0})
    if duplicate:
        out.append(dict(out[-1]))
    return out


def test_exact_delivery_symbol_identity_only():
    assert p.eligible(info("WINV26"))
    assert not p.eligible(info("WIN$N"))
    assert not p.eligible(info("WINFUT"))
    assert not p.eligible(info("WINV26", description="IBOVESPA"))
    assert not p.eligible(info("WINV26", path="OTHER"))


def test_expiry_chronology_is_deterministic_and_price_free():
    a = meta("WINV25", datetime(2025, 10, 15, 20, tzinfo=timezone.utc))
    b = meta("WINZ25", datetime(2025, 12, 17, 20, tzinfo=timezone.utc))
    assert p.choose_contract("2025-09-01", [b, a]) == "WINV25"
    assert p.choose_contract("2025-11-01", [a, b]) == "WINZ25"
    assert p.choose_contract("2026-01-01", [a, b]) is None


def test_partition_counts_use_canonical_calendar_windows():
    valid = ["2025-01-02", "2025-12-31", "2026-01-02", "2026-08-07"]
    assert p.counts(valid) == {"total": 4, "discovery": 2, "replication": 2}


def test_session_requires_40_bars_and_exact_300_second_spacing():
    exp = datetime(2026, 12, 16, 20, tzinfo=timezone.utc)
    metas = [meta("WINZ26", exp)]
    cand, qa = p.build_candidate({"WINZ26": rows("2025-06-02", "WINZ26", 40)}, metas)
    assert len(cand) == 40
    assert qa["sessions"][0]["structurally_valid"] is True


def test_internal_gap_invalidates_session_without_interpolation():
    exp = datetime(2026, 12, 16, 20, tzinfo=timezone.utc)
    cand, qa = p.build_candidate({"WINZ26": rows("2025-06-02", "WINZ26", 40, gap_at=20)}, [meta("WINZ26", exp)])
    assert cand == []
    assert qa["sessions"][0]["exact_300s_spacing"] is False
    assert qa["sessions"][0]["structurally_valid"] is False


def test_duplicate_timestamp_invalidates_session():
    exp = datetime(2026, 12, 16, 20, tzinfo=timezone.utc)
    cand, qa = p.build_candidate({"WINZ26": rows("2025-06-02", "WINZ26", 40, duplicate=True)}, [meta("WINZ26", exp)])
    assert cand == []
    assert qa["sessions"][0]["duplicate"] is True
    assert qa["sessions"][0]["structurally_valid"] is False


def test_missing_expiry_cannot_select_contract():
    m = {"symbol": "WINZ26", "expiration_time": 0, "description": "IBOVESPA MINI", "path": "BVMF-Derivatives"}
    assert p.choose_contract("2025-06-02", [m]) is None


def test_strict_constants_cannot_regress_to_v1_floor():
    assert p.NAMESPACE == "RQ_STRICT_FORWARD_UNSEEN_2025_2026_V2"
    assert p.MIN_TOTAL == 322
    assert p.MIN_PART == 161
    assert p.START == "2025-01-01"
    assert p.DISC_END == "2025-12-31"
    assert p.REPL_START == "2026-01-01"
    assert p.END == "2026-08-09"


def test_mt5_is_hard_bound_to_independent_secondary_cross_validation_only():
    assert p.SOURCE_ROLE == "INDEPENDENT_SECONDARY_SOURCE"
    assert p.USAGE_CONSTRAINT == "CROSS_VALIDATION_ONLY"
    text = open(p.__file__, encoding="utf-8").read()
    assert '"source_admission_pass":False' in text
    assert '"may_be_primary_source":False' in text
    assert '"may_reconstruct_lost_clocks":False' in text
    assert '"requalification_economics_allowed":False' in text


def test_probe_provenance_stays_fail_closed():
    text = open(p.__file__, encoding="utf-8").read()
    assert '"publication_semantics_proven":False' in text
    assert '"revision_semantics_proven":False' in text
    assert '"point_in_time_validity_proven":False' in text


def test_no_order_send_codepath():
    text = open(p.__file__, encoding="utf-8").read().lower()
    assert "order_send(" not in text
    assert p.SAFETY["ORDERS"] == 0
    assert p.SAFETY["REAL_CAPITAL"] == 0
    assert p.SAFETY["ENGINE_FEED"] is False
