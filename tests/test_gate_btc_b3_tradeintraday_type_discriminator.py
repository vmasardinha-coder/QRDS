from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE = Path(__file__).parents[1] / "tools" / "gate_btc_factory" / "b3_tradeintraday_type_discriminator.py"
spec = importlib.util.spec_from_file_location("b3_tradeintraday_type_discriminator", MODULE)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class FakeResponse:
    def __init__(self, raw: bytes, url: str, disposition: str):
        self.status_code = 200
        self.url = url
        self._raw = raw
        self.headers = {"content-type": "application/octet-stream", "content-disposition": disposition}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def iter_content(self, chunk_size=16384):
        del chunk_size
        yield self._raw


class FakeSession:
    def get(self, url, **_kwargs):
        if "type=2" in url:
            raw = b"PK\x03\x04DERIVATIVES"
            disp = "attachment; filename=type2.zip"
        else:
            raw = b"PK\x03\x04RV"
            disp = "attachment; filename=rv.zip"
        return FakeResponse(raw, url, disp)


def test_discriminator_compares_none_type1_type2_and_never_grants_credit():
    result = mod.probe(FakeSession(), "2026-09-04")
    variants = {(row["host"], row["variant"]) for row in result["probes"]}
    for host in mod.HOSTS:
        assert (host, "none") in variants
        assert (host, "type1") in variants
        assert (host, "type2") in variants
    assert result["type2_distinct_from_untyped_proven"] is True
    assert result["type2_distinct_from_type1_proven"] is True
    assert result["exact_derivatives_identity_proven"] is False
    assert result["exact_win_identity_proven"] is False
    assert result["strict_source_gate_green"] is False
    assert result["source_gate_credit"] == 0
    assert result["historical_backfill_credit"] == 0
    assert result["prospective_credit"] == 0


def test_identical_payloads_fail_closed_as_not_differentiated():
    class SameSession:
        def get(self, url, **_kwargs):
            return FakeResponse(b"PK\x03\x04SAME", url, "attachment; filename=same.zip")

    result = mod.probe(SameSession(), "2026-09-04")
    assert result["type2_distinct_from_untyped_proven"] is False
    assert result["type2_distinct_from_type1_proven"] is False
    assert result["status"] == "TYPE2_NOT_DIFFERENTIATED_FAIL_CLOSED"
    assert result["strict_source_gate_green"] is False
    assert result["safety"] == {
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders": 0,
        "real_capital": 0,
        "no_retune": True,
        "no_backfill": True,
        "no_counter_reset": True,
        "fail_closed": True,
        "h1_economics_read": False,
    }
