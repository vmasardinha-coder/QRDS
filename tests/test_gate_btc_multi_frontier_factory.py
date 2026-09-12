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
    assert q["family_count"]==16
    assert q["counts"]=={"WAITING_SOURCE":16}
    assert q["economics_read"] is False
    assert q["promotion_allowed"] is False
    assert all(x["id"].startswith(("CRBF","CRCV","COKBF","COCV")) for x in q["families"])

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


def _accessible_packet(ts, bucket_ms):
    rec=[]
    for asset in ("BTC","ETH"):
        rec += [
          {"venue":"OKX","asset":asset,"market":"SPOT","bar":{"start_ms":bucket_ms,"open":"100","close":"101"}},
          {"venue":"OKX","asset":asset,"market":"PERPETUAL","bar":{"start_ms":bucket_ms,"open":"100","close":"101.1"}},
          {"venue":"OKX","asset":asset,"market":"FUNDING","funding_rate":"0.0001"},
          {"venue":"COINBASE","asset":asset,"market":"SPOT","bar":{"start_s":bucket_ms//1000,"open":"100","close":"100.9"}},
        ]
    return {"captured_at_utc":ts,"records":rec,"packet_sha256":"a"*64}

def test_accessible_source_requires_three_complete_packets(tmp_path):
    m=load(Path("tools/gate_btc_factory/crypto_accessible_source_admission.py"),"ca")
    for i in range(2):
        (tmp_path/f"{i}.json").write_text(json.dumps(_accessible_packet(f"2026-09-14T00:0{i}:00Z",1000+i*300000)))
    x=m.evaluate(tmp_path,None,3)
    assert x["source_admitted_forward_only"] is False
    (tmp_path/"2.json").write_text(json.dumps(_accessible_packet("2026-09-14T00:10:00Z",601000)))
    x=m.evaluate(tmp_path,None,3)
    assert x["source_admitted_forward_only"] is True
    assert x["family_state"]=="READY_FORWARD"
    assert x["economics_read"] is False

def test_accessible_prereg_freezes_no_partial_feedback():
    p=json.loads((ROOT/"tools/gate_btc_factory/CRYPTO_ACCESSIBLE_FORWARD_PREREG.v1.json").read_text())
    assert p["family_count"]==8
    assert p["economics_read_before_prereg"] is False
    assert p["blind_evaluation"]["minimum_observations_before_aggregate_economics"]==60
    assert p["blind_evaluation"]["partial_aggregate_economics_visible"] is False
    assert p["safety"]["NO_RETUNE"] is True
