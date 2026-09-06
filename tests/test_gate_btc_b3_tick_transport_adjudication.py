from __future__ import annotations

import json
from pathlib import Path

P = Path(__file__).parents[1] / "tools" / "gate_btc_factory" / "B3_TICK_TRANSPORT_ADJUDICATION.v1.json"


def test_adjudication_is_fail_closed_and_zero_credit():
    d = json.loads(P.read_text(encoding="utf-8"))
    assert d["classification"] == "INSUFFICIENT_EVIDENCE_FAIL_CLOSED"
    assert d["definitive_data_gap_declared"] is False
    assert d["source_gate_green"] is False
    assert d["economics_read"] is False
    assert d["evidence"]["rapinegocios_type2_recent"]["exact_win_identity_observed"] is False
    assert d["evidence"]["rapinegocios_type2_recent"]["adjudication"] == "REJECT_AS_WIN_SOURCE"
    bdi = d["evidence"]["bdi_tickbytick_derivatives"]
    assert bdi["tested_transport_variants"] == 5
    assert bdi["physical_variant_count"] == 0
    assert bdi["all_variants_http_500_empty_body"] is True
    assert all(v == 0 for v in d["credit"].values())
    s = d["safety"]
    assert s["RESEARCH_ONLY"] and s["SHADOW_ONLY"] and s["NOT_APPROVED"] and s["FAIL_CLOSED"]
    assert s["ENGINE_FEED"] is False and s["ORDERS"] == 0 and s["REAL_CAPITAL"] == 0
    assert s["NO_RETUNE"] and s["NO_BACKFILL"] and s["NO_COUNTER_RESET"]
    assert s["H1_ECONOMICS_READ"] is False
