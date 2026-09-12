import json
from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parents[1]

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def test_crypto_queue_is_waiting_source_and_isolated():
    m=load(Path("tools/gate_btc_factory/generate_crypto_family_queue.py"),"cg")
    c=json.loads((ROOT/"tools/gate_btc_factory/CRYPTO_FAMILY_FACTORY_CONTRACT.v1.json").read_text())
    q=m.build_queue(c)
    assert q["family_count"]==8
    assert q["counts"]=={"WAITING_SOURCE":8}
    assert q["economics_read"] is False
    assert q["promotion_allowed"] is False
    assert all(x["id"].startswith(("CRBF","CRCV")) for x in q["families"])

def test_router_preserves_512_and_redirects_capacity():
    m=load(Path("tools/gate_btc_factory/multi_frontier_router.py"),"r")
    c=json.loads((ROOT/"tools/gate_btc_factory/MULTI_FRONTIER_ROUTING_CONTRACT.v1.json").read_text())
    out=m.route(c)
    assert out["b3_win_waiting_families"]==512
    assert out["b3_win_source_gate_green"] is False
    assert out["economics_read_from_blocked_frontiers"] is False
    assert out["scientific_credit_transfer"] is False
    assert out["primary_capacity_target"]=="CRYPTO_FORWARD_UNSEEN_V1"

def test_b3_daily_is_materially_distinct_and_pre_economics():
    c=json.loads((ROOT/"tools/gate_btc_factory/B3_DAILY_CROSS_SECTIONAL_PREREG.v1.json").read_text())
    assert c["family_count"]==6
    assert c["economics_read_for_this_family_block"] is False
    assert c["anti_leakage"]["eqb_outcomes_used_for_threshold_selection"] is False
    assert "Cross-sectional" in c["material_difference"]
