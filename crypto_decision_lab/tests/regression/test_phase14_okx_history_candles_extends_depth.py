from pathlib import Path

import crypto_decision_lab.reports.phase14_okx_public_data_adapter_pack as okx_pack


def test_phase14_okx_history_candles_extends_depth(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def fake_http_get_json(url: str, timeout: int = 25):
        calls.append(url)
        if "/api/v5/market/candles" in url:
            return {
                "code": "0",
                "data": [
                    ["5000", "104", "105", "103", "104.5", "1000", "10", "100000", "1"],
                    ["4000", "103", "104", "102", "103.5", "1000", "10", "100000", "1"],
                ],
            }
        if "/api/v5/market/history-candles" in url:
            return {
                "code": "0",
                "data": [
                    ["3000", "102", "103", "101", "102.5", "1000", "10", "100000", "1"],
                    ["2000", "101", "102", "100", "101.5", "1000", "10", "100000", "1"],
                    ["1000", "100", "101", "99", "100.5", "1000", "10", "100000", "1"],
                ],
            }
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

    assert payload["gate_answer"] == "PHASE14_OKX_PUBLIC_DATA_ADAPTER_READY_RESEARCH_ONLY"
    assert payload["okx_adapter_ready"] is True
    assert payload["okx_rows_total"] == 5
    assert payload["source_endpoint_family"] == "OKX_V5_MARKET_CANDLES_AND_HISTORY_CANDLES"
    assert any("/api/v5/market/history-candles" in url for url in calls)
    assert payload["canonical_data_writes"] == 0
    assert payload["promotion_allowed"] is False
    assert payload["safe_apply_allowed"] is False
