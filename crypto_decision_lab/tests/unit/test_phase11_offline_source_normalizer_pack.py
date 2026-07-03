import json
from pathlib import Path
from crypto_decision_lab.reports.phase11_offline_source_normalizer_pack import build_phase11_offline_source_normalizer_pack

def test_phase11_offline_source_normalizer_pack_builds_with_csv(tmp_path: Path):
    root=tmp_path/"repo"; inbox=root/"crypto_decision_lab/manual_intake/inbox"; inbox.mkdir(parents=True)
    (inbox/"btc_usdt.csv").write_text("open_time,open,high,low,close,volume,symbol,interval,source\n2026-01-01T00:00:00Z,100,101,99,100.5,1000,BTC-USDT,1h,TEST\n",encoding="utf-8")
    r=build_phase11_offline_source_normalizer_pack(tmp_path/"out",root); p=r["payload"]
    assert p["policy_lock"]=="ACTIVE"; assert p["app_mode"]=="INTERACTIVE_RESEARCH_ONLY"
    assert p["inbox_file_count"]==1; assert p["fallback_samples_used"] is False
    assert p["files_normalized"]==1; assert p["rows_normalized"]==1
    assert p["canonical_data_writes"]==0; assert p["promotion_allowed"] is False
    assert Path(r["html_path"]).exists()

def test_phase11_offline_source_normalizer_pack_has_no_operational_flags(tmp_path: Path):
    r=build_phase11_offline_source_normalizer_pack(tmp_path/"out",tmp_path/"repo"); p=r["payload"]
    for key in ["api_key_present","authenticated_connection_used","orders_generated","real_orders_generated","real_capital_used","trading_signal_generated","executable_signal_generated","recommendation_generated","allocation_generated","portfolio_decision_generated","operational_decision_allowed"]:
        assert p[key] is False
