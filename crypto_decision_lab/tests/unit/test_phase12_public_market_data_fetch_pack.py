from pathlib import Path
import csv
from crypto_decision_lab.reports import phase12_public_market_data_fetch_pack as m

def test_phase12_public_market_data_fetch_pack_builds_existing_files(tmp_path: Path):
    root = tmp_path / "repo"
    inbox = root / "crypto_decision_lab" / "manual_intake" / "inbox"
    inbox.mkdir(parents=True)
    p = inbox / "btcusdt_binance_public_klines_1h.csv"
    p.write_text("timestamp,open,high,low,close,volume,symbol,interval,source\n2026-01-01T00:00:00Z,100,101,99,100.5,1,BTC-USDT,1h,BINANCE_SPOT_PUBLIC_KLINES_RESEARCH_ONLY\n2026-01-01T01:00:00Z,101,102,100,101.5,2,BTC-USDT,1h,BINANCE_SPOT_PUBLIC_KLINES_RESEARCH_ONLY\n", encoding="utf-8")
    r = m.build_phase12_public_market_data_fetch_pack(tmp_path / "out", root, symbols=["BTCUSDT"], rows_per_symbol=2, fetch=False)
    payload = r["payload"]
    assert payload["policy_lock"] == "ACTIVE"
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["public_file_count"] == 1
    assert payload["public_rows_total"] == 2
    assert payload["api_key_present"] is False
    assert payload["authenticated_connection_used"] is False
    assert payload["promotion_allowed"] is False
    assert payload["canonical_data_writes"] == 0
    assert Path(r["html_path"]).exists()

def test_phase12_public_market_data_fetch_pack_has_no_operational_flags(tmp_path: Path):
    r = m.build_phase12_public_market_data_fetch_pack(tmp_path / "out", tmp_path / "repo", symbols=["BTCUSDT"], rows_per_symbol=2, fetch=False)
    p = r["payload"]
    for key in ["api_key_present","authenticated_connection_used","orders_generated","real_orders_generated","real_capital_used","trading_signal_generated","executable_signal_generated","recommendation_generated","allocation_generated","portfolio_decision_generated","operational_decision_allowed"]:
        assert p[key] is False
