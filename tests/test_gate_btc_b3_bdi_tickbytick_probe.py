from __future__ import annotations

import json

from tools.gate_btc_factory import b3_bdi_tickbytick_probe as mod


class Resp:
    def __init__(self, status_code: int, obj: dict):
        self.status_code = status_code
        self.content = json.dumps(obj).encode()
        self._obj = obj

    def json(self):
        return self._obj


class Session:
    def __init__(self):
        self.get_calls = []
        self.post_calls = []

    def get(self, url, timeout, headers):
        self.get_calls.append((url, timeout, headers))
        return Resp(200, {"groups": [{"tables": [{"name": "TickByTickDerivatives", "classification": "Derivativos de bolsa"}]}]})

    def post(self, url, data, headers, timeout):
        self.post_calls.append((url, data, headers, timeout))
        return Resp(200, {"limitDate": "D-21", "table": {"columns": [{"name": "TckrSymb"}, {"name": "Price"}], "values": [["WINV26", 140000]]}})


def test_probe_uses_b3_catalog_get_and_table_post_but_never_greens_gate():
    s = Session()
    out = mod.probe(s, "2026-09-04")
    assert s.get_calls[0][0].endswith("/bdi/table/classifications")
    url, body, headers, _ = s.post_calls[0]
    assert "/bdi/table/TickByTickDerivatives/2026-09-04/2026-09-04/1/1000" in url
    assert body == b"{}"
    assert headers["Content-Type"] == "application/json"
    assert out["physical_surface_observed"] is True
    assert out["table_probe"]["sample_contains_win_identity"] is True
    assert out["table_probe"]["limit_date"] == "D-21"
    assert out["strict_source_gate_green"] is False
    assert out["source_gate_credit"] == 0
    assert out["historical_backfill_credit"] == 0
    safety = out["safety"]
    assert safety["research_only"] and safety["shadow_only"] and safety["not_approved"]
    assert safety["engine_feed"] is False and safety["orders"] == 0 and safety["real_capital"] == 0
    assert safety["no_retune"] and safety["no_backfill"] and safety["no_counter_reset"] and safety["fail_closed"]


def test_empty_table_payload_stays_fail_closed():
    class Empty(Session):
        def post(self, url, data, headers, timeout):
            self.post_calls.append((url, data, headers, timeout))
            return Resp(200, {})

    out = mod.probe(Empty(), "2026-09-04")
    assert out["physical_surface_observed"] is True
    assert out["strict_source_gate_green"] is False
    assert out["table_probe"]["row_count_page1"] is None
