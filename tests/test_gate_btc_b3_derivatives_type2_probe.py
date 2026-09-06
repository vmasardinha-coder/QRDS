from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE = Path(__file__).parents[1] / "tools" / "gate_btc_factory" / "b3_derivatives_type2_probe.py"
spec = importlib.util.spec_from_file_location("b3_derivatives_type2_probe", MODULE)
assert spec and spec.loader
probe_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe_mod)


class FakeResponse:
    def __init__(self, status: int, raw: bytes, url: str):
        self.status_code = status
        self._raw = raw
        self.url = url
        self.headers = {"content-type": "application/zip", "content-length": str(len(raw))}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def iter_content(self, chunk_size=16384):
        del chunk_size
        yield self._raw


class FakeSession:
    def __init__(self, raw: bytes = b"PK\x03\x04payload"):
        self.raw = raw
        self.urls: list[str] = []

    def get(self, url, **_kwargs):
        self.urls.append(url)
        return FakeResponse(200, self.raw, url)


def test_probe_requires_derivatives_type_2_and_keeps_gate_closed():
    session = FakeSession()
    result = probe_mod.probe(session, "2026-09-04")
    assert session.urls
    assert all("?type=2" in url for url in session.urls)
    assert any("drp.b3.com.br" in url for url in session.urls)
    assert any("arquivos.b3.com.br" in url for url in session.urls)
    assert result["physical_zip_observation_count"] == len(session.urls)
    assert result["strict_source_gate_green"] is False
    assert result["source_gate_credit"] == 0
    assert result["historical_backfill_credit"] == 0
    assert result["prospective_credit"] == 0
    assert result["full_161_session_coverage_proven"] is False
    assert result["exact_win_identity_proven"] is False


def test_non_zip_response_fails_closed():
    result = probe_mod.probe(FakeSession(b"not-a-zip"), "2026-09-04")
    assert result["physical_zip_observation_count"] == 0
    assert result["status"] == "DERIVATIVES_TYPE2_SURFACE_NOT_PHYSICALLY_OBSERVED_FAIL_CLOSED"
    assert result["strict_source_gate_green"] is False
    safety = result["safety"]
    assert safety == {
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
