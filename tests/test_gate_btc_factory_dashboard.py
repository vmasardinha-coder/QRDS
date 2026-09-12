import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_consolidated_dashboard_is_fail_closed():
    d=json.loads((ROOT/"tools/gate_btc_factory/FACTORY_DASHBOARD_LATEST.json").read_text())
    assert d["global"]["ORDERS"]==0
    assert d["global"]["REAL_CAPITAL"]==0
    assert d["global"]["ENGINE_FEED"] is False
    by={x["id"]:x for x in d["frontiers"]}
    assert by["B3_WIN_STRICT_V2"]["family_count"]==512
    assert by["B3_WIN_STRICT_V2"]["source_gate_green"] is False
    assert by["B3_DAILY_FRONTIER_V1"]["survivor_count"]==0
    assert by["CRYPTO_ACCESSIBLE_FORWARD_V1"]["source_gate_green"] is True
    assert by["CRYPTO_ACCESSIBLE_FORWARD_V1"]["economics_read"] is False
    assert d["totals"]["tracked_families"]==534
    assert d["totals"]["survivors"]==0
