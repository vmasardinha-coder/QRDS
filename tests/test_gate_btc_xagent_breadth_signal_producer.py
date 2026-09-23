import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/gate_btc_factory"))

import xagent_breadth_signal_producer as m


class R:
    def __init__(self, d): self.d = d
    def raise_for_status(self): pass
    def json(self): return self.d


def universe(capture, n=60):
    return [
        {"instId": f"C{i:03d}-USDT", "instType": "SPOT", "baseCcy": f"C{i:03d}", "quoteCcy": "USDT", "listTime": str(capture-1000), "expTime": "", "state": "live"}
        for i in range(n)
    ]


def test_frozen_breadth_transform_and_immutable_genesis():
    capture = 1_800_003_700_000
    target = m._common_target_bar(capture)
    rows = universe(capture)
    calls = {"instruments": 0}

    def fake(url, params=None, timeout=20):
        if url == m.INSTRUMENTS:
            calls["instruments"] += 1
            return R({"code": "0", "data": rows})
        if url == m.CANDLES:
            i = int(params["instId"][1:4])
            close = "101" if i < 30 else "99"
            return R({"code": "0", "data": [[str(target), "100", "102", "98", close, "1", "1", "100", "1"]]})
        raise AssertionError(url)

    rec, genesis = m.collect(fake, capture)
    assert calls["instruments"] == 1
    assert genesis["member_count"] == 60
    assert rec["signal"] == 0.0
    assert rec["coverage_fraction"] == 1.0
    assert rec["common_closed_bar_close_ms"] <= capture
    assert rec["economic_outcomes_read"] is False
    assert rec["survivor_credit"] == 0

    def fake_second(url, params=None, timeout=20):
        if url == m.INSTRUMENTS:
            raise AssertionError("immutable genesis must not be rebuilt")
        if url == m.CANDLES:
            return R({"code": "0", "data": [[str(target), "100", "101", "99", "101", "1", "1", "100", "1"]]})
        raise AssertionError(url)

    second, genesis2 = m.collect(fake_second, capture, genesis)
    assert genesis2["genesis_sha256"] == genesis["genesis_sha256"]
    assert second["genesis_member_count"] == 60
    assert second["signal"] == 1.0
    assert second["new_listings_admitted"] is False


def test_below_frozen_80pct_coverage_is_unavailable_not_zero_fill():
    capture = 1_800_003_700_000
    target = m._common_target_bar(capture)
    genesis = m.create_genesis(lambda url, params=None, timeout=20: R({"code": "0", "data": universe(capture)}), capture)

    def fake(url, params=None, timeout=20):
        i = int(params["instId"][1:4])
        data = [[str(target), "100", "101", "99", "101", "1", "1", "100", "1"]] if i < 47 else []
        return R({"code": "0", "data": data})

    rec, _ = m.collect(fake, capture, genesis)
    assert rec["available_count"] == 47
    assert rec["coverage_fraction"] < 0.8
    assert rec["signal"] is None
    assert rec["status"] == "UNAVAILABLE_BELOW_FROZEN_COMMON_BAR_COVERAGE"
    assert rec["missing_policy"] == "UNAVAILABLE_AND_COUNT_NOT_ZERO_FILL"


def test_genesis_hash_mutation_fails_closed():
    capture = 1_800_003_700_000
    genesis = m.create_genesis(lambda url, params=None, timeout=20: R({"code": "0", "data": universe(capture)}), capture)
    genesis["members"].append("NEW-USDT")
    try:
        m.validate_genesis(genesis)
        assert False, "expected genesis mutation failure"
    except RuntimeError as exc:
        assert "GENESIS" in str(exc)


def test_target_is_last_fully_closed_utc_hour():
    capture = 10 * m.HOUR_MS + 12345
    target = m._common_target_bar(capture)
    assert target == 9 * m.HOUR_MS
    assert target + m.HOUR_MS <= capture
