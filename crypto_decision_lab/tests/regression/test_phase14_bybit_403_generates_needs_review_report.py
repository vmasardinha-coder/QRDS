from pathlib import Path

import crypto_decision_lab.reports.phase14_bybit_public_data_adapter_pack as bybit_pack


def test_phase14_bybit_403_generates_needs_review_report(monkeypatch, tmp_path: Path) -> None:
    def fake_http_get_json(url: str, timeout: int = 25):
        return {
            "__network_error__": True,
            "error_type": "HTTPError",
            "status_code": 403,
            "reason": "Forbidden",
            "url": url,
            "research_status": "PUBLIC_ENDPOINT_BLOCKED_OR_UNAVAILABLE_RESEARCH_ONLY",
        }

    monkeypatch.setattr(bybit_pack, "_http_get_json", fake_http_get_json)

    result = bybit_pack.build_phase14_bybit_public_data_adapter_pack(
        tmp_path / "out",
        tmp_path / "repo",
        symbols=["BTCUSDT"],
        rows_per_symbol=3,
        fetch=True,
    )
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE14_BYBIT_PUBLIC_DATA_ADAPTER_NEEDS_REVIEW_RESEARCH_ONLY"
    assert payload["bybit_adapter_ready"] is False
    assert payload["bybit_rows_total"] == 0
    assert payload["endpoint_access_status"] == "PUBLIC_ENDPOINT_BLOCKED_OR_UNAVAILABLE_RESEARCH_ONLY"
    assert payload["endpoint_blocked_or_unavailable"] is True
    assert payload["canonical_data_writes"] == 0
    assert payload["promotion_allowed"] is False
    assert payload["safe_apply_allowed"] is False
    assert payload["order_endpoint_used"] is False
    assert payload["trading_endpoint_used"] is False
    assert Path(result["html_path"]).exists()
