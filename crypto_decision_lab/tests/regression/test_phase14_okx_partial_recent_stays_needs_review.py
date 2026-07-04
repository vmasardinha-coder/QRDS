from pathlib import Path

import crypto_decision_lab.reports.phase14_okx_public_data_adapter_pack as okx_pack


def test_phase14_okx_partial_recent_stays_needs_review_when_history_empty(monkeypatch, tmp_path: Path) -> None:
    def fake_http_get_json(url: str, timeout: int = 25):
        if "/api/v5/market/candles" in url:
            return {
                "code": "0",
                "data": [
                    ["2000", "101", "102", "100", "101.5", "1000", "10", "100000", "1"],
                    ["1000", "100", "101", "99", "100.5", "1000", "10", "100000", "1"],
                ],
            }
        if "/api/v5/market/history-candles" in url:
            return {"code": "0", "data": []}
        return {"code": "0", "data": []}

    monkeypatch.setattr(okx_pack, "_http_get_json", fake_http_get_json)

    result = okx_pack.build_phase14_okx_public_data_adapter_pack(
        tmp_path / "out",
        tmp_path / "repo",
        inst_ids=["BTC-USDT-SWAP"],
        rows_per_instrument=5,
        fetch=True,
    )
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE14_OKX_PUBLIC_DATA_ADAPTER_NEEDS_REVIEW_RESEARCH_ONLY"
    assert payload["okx_adapter_ready"] is False
    assert payload["okx_rows_total"] == 2
    assert payload["endpoint_access_status"] == "PUBLIC_ENDPOINT_ACCESS_OK_RESEARCH_ONLY"
    assert payload["endpoint_blocked_or_unavailable"] is False
    assert payload["canonical_data_writes"] == 0
