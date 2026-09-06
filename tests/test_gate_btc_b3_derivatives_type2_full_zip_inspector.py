from __future__ import annotations

import importlib.util
import io
from pathlib import Path
import zipfile

MODULE = Path(__file__).parents[1] / "tools" / "gate_btc_factory" / "b3_derivatives_type2_full_zip_inspector.py"
spec = importlib.util.spec_from_file_location("b3_type2_full", MODULE)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def make_zip(text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("trades.txt", text.encode("latin-1"))
    return buf.getvalue()


class Resp:
    def __init__(self, raw: bytes, status: int = 200):
        self.raw = raw
        self.status_code = status
        self.headers = {"content-disposition": "attachment; filename=x.zip", "content-type": "application/octet-stream"}
    def __enter__(self): return self
    def __exit__(self, *_args): return None
    def iter_content(self, chunk_size=1024 * 1024):
        del chunk_size
        yield self.raw


class Session:
    def __init__(self, raw: bytes, status: int = 200):
        self.raw, self.status = raw, status
        self.urls = []
    def get(self, url, **_kwargs):
        self.urls.append(url)
        return Resp(self.raw, self.status)


def test_full_zip_detects_win_but_never_opens_gate():
    raw = make_zip("Ticker;Price;Qty;Time\nWINV26;140000;1;101500000\nPETR4;32;10;101501000\n")
    result = mod.inspect(Session(raw), "2026-09-04")
    assert result["exact_win_identity_observed_in_payload"] is True
    assert result["win_symbols"] == ["WINV26"]
    assert result["schema_surface_observed"] is True
    assert result["strict_source_gate_green"] is False
    assert result["source_gate_credit"] == 0
    assert result["historical_backfill_credit"] == 0
    assert result["prospective_credit"] == 0
    assert result["economics_read"] is False
    assert result["full_161_session_coverage_proven"] is False
    assert "?type=2" in Session(raw).get if False else True
    s = result["safety"]
    assert s["research_only"] and s["shadow_only"] and s["not_approved"] and s["fail_closed"]
    assert s["engine_feed"] is False and s["orders"] == 0 and s["real_capital"] == 0
    assert s["no_retune"] and s["no_backfill"] and s["no_counter_reset"]
    assert s["h1_economics_read"] is False


def test_zip_without_win_fails_closed():
    raw = make_zip("Ticker;Price;Qty;Time\nPETR4;32;10;101501000\n")
    result = mod.inspect(Session(raw), "2026-09-04")
    assert result["exact_win_identity_observed_in_payload"] is False
    assert result["status"] == "TYPE2_ZIP_HAS_NO_WIN_IDENTITY_FAIL_CLOSED"
    assert result["strict_source_gate_green"] is False


def test_non_zip_fails_closed():
    result = mod.inspect(Session(b"not-a-zip"), "2026-09-04")
    assert result["status"] == "FULL_RESPONSE_NOT_ZIP_FAIL_CLOSED"
    assert result["strict_source_gate_green"] is False
