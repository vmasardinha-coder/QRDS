from datetime import date

from tools.gate_btc_b3_h_win_contract_manifest import build_manifest, closest_wednesday_to_15, win_front


def test_august_2026_roll_matches_frozen_h1_boundary():
    assert win_front(date(2026,8,12)).symbol == "WINQ26"
    assert win_front(date(2026,8,13)).symbol == "WINV26"


def test_expiry_rule():
    assert closest_wednesday_to_15(2026,8) == date(2026,8,12)
    assert closest_wednesday_to_15(2026,10) == date(2026,10,14)


def test_manifest_never_crosses_h1_cutoff():
    m=build_manifest(date(2026,8,3), date(2026,8,10))
    assert m["h1_economics_read"] is False
    assert all(date.fromisoformat(r["date"]) < date(2026,8,10) for r in m["sessions"])


def test_manifest_rejects_post_cutoff():
    try:
        build_manifest(date(2026,8,3), date(2026,8,11))
    except ValueError as exc:
        assert "PRE_H1" in str(exc)
    else:
        raise AssertionError("post-cutoff manifest must fail closed")
