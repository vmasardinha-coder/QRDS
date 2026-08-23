from datetime import date

from tools.gate_btc_b3_h_win_contract_manifest import (
    build_manifest,
    closest_wednesday_to_15,
    source_binding,
    win_front,
)


def test_august_2026_roll_matches_frozen_h1_boundary():
    assert win_front(date(2026, 8, 12)).symbol == "WINQ26"
    assert win_front(date(2026, 8, 13)).symbol == "WINV26"


def test_expiry_rule():
    assert closest_wednesday_to_15(2026, 8) == date(2026, 8, 12)
    assert closest_wednesday_to_15(2026, 10) == date(2026, 10, 14)


def test_manifest_never_crosses_h1_cutoff():
    m = build_manifest(date(2026, 8, 3), date(2026, 8, 10))
    assert m["h1_economics_read"] is False
    assert m["stage0_required_before_economics"] is True
    assert all(date.fromisoformat(r["date"]) < date(2026, 8, 10) for r in m["sessions"])


def test_manifest_rejects_post_cutoff():
    try:
        build_manifest(date(2026, 8, 3), date(2026, 8, 11))
    except ValueError as exc:
        assert "PRE_H1" in str(exc)
    else:
        raise AssertionError("post-cutoff manifest must fail closed")


def test_b3_source_transition_is_not_hidden():
    legacy = source_binding(date(2025, 12, 12))
    transition = source_binding(date(2026, 1, 6))
    bdi = source_binding(date(2026, 8, 7))
    assert legacy["source_family"] == "B3_LEGACY_TRADE_BY_TRADE_ARCHIVE"
    assert legacy["candidate_url"].startswith("https://arquivos.b3.com.br/rapinegocios/")
    assert transition["source_family"] == "B3_TRANSITION_LEGACY_OR_BDI"
    assert transition["candidate_url"] is None
    assert bdi["source_family"] == "B3_BDI_TRADE_BY_TRADE"
    assert bdi["candidate_url"] is None
    assert "REQUIRES_STAGE0" in bdi["binding_status"]
