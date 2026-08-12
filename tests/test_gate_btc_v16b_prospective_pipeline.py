import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tools import gate_btc_v16b_prospective_chain as chain
from tools import gate_btc_v16b_prospective_entry as entry_builder


def utc(y,m,d,h=0): return datetime(y,m,d,h,tzinfo=timezone.utc)

def signal_row():
    # Deliberately make asc tie order different from reverse(desc) to prove both ranks are preserved independently.
    scores={f"A{i:02d}":float(30-i) for i in range(20)}
    scores["A18"]=1.0; scores["A19"]=1.0
    long_rank=[f"A{i:02d}" for i in range(20)]
    short_rank=["A18","A19"]+[f"A{i:02d}" for i in range(17,-1,-1)]
    return {
      "signal_date_utc":"2026-08-13","entry_date_utc":"2026-08-14","candidate_id":chain.CANDIDATE_ID,
      "model_hash":"a"*64,"code_commit":"b"*40,"input_data_hashes":{"panel":"c"*64},
      "universe_snapshot_id":"cmc-2026-07-31","universe_snapshot_available_at_utc":"2026-08-01T00:00:00Z",
      "panel_hash":"d"*64,"model_state_hash":"e"*64,"eligible_universe_count":20,"liquidity_qualified_count":20,
      "eligible_scores":scores,"long_ranking_desc":long_rank,"short_ranking_asc":short_rank,"preliminary_longs_10":long_rank[:10],
      "risk_state":{"exposure":0.8,"trailing_vol":0.25,"prior_weights":{}},"source_coverage":{"panel":"OK"},"status":"OK","blocker_reason":None,
    }

def test_dual_rank_signal_accepts_independent_tie_order():
    e=chain.validate_signal_row(signal_row(),now=utc(2026,8,14,1))
    assert e["short_ranking_asc"] != list(reversed(e["long_ranking_desc"]))

def test_entry_must_follow_sealed_short_ascending_rank(tmp_path):
    sig=chain.validate_signal_row(signal_row(),now=utc(2026,8,14,1))
    checked=[{"asset":a,"shortable":True,"evidence_ref":"ev"} for a in sig["short_ranking_asc"][:10]]
    longs=sig["preliminary_longs_10"]; shorts=[x["asset"] for x in checked]
    row={"signal_date_utc":sig["signal_date_utc"],"entry_date_utc":sig["entry_date_utc"],"candidate_id":chain.CANDIDATE_ID,
         "signal_seal_sha256":sig["seal_sha256"],"shortability_evidence_hash":"f"*64,"shortability_checked_ranked":checked,
         "long_executability":{a:{"executable":True,"evidence_ref":"spot"} for a in longs},"longs_10":longs,"shorts_10":shorts,
         "entry_instruments":{a:a+"USDT" for a in set(longs)|set(shorts)},"exposure":0.8,"trailing_vol":0.25,"turnover_estimate":0.8,
         "transaction_cost_bps":15.0,"source_coverage":{"binance":"OK"},"status":"OK","blocker_reason":None}
    out=chain.validate_entry_row(row,sig,now=utc(2026,8,14,12)); assert out["shorts_10"]==sig["short_ranking_asc"][:10]
    row["shortability_checked_ranked"][0]["asset"]=sig["long_ranking_desc"][-1]
    with pytest.raises(ValueError,match="ascending short ranking"):
        chain.validate_entry_row(row,sig,now=utc(2026,8,14,12))

def test_entry_builder_normalizes_multiplier_contract_and_blocks_missing_long(tmp_path):
    sig=chain.validate_signal_row(signal_row(),now=utc(2026,8,14,1))
    # Replace one short-ranked asset with PEPE while keeping monotonic score/rank evidence valid.
    sig["short_ranking_asc"][0]="PEPE"; sig["eligible_scores"]["PEPE"]=sig["eligible_scores"].pop("A18")
    usdm={"symbols":[{"symbol":"1000PEPEUSDT","status":"TRADING","contractType":"PERPETUAL","quoteAsset":"USDT"}] +
                     [{"symbol":a+"USDT","status":"TRADING","contractType":"PERPETUAL","quoteAsset":"USDT"} for a in sig["short_ranking_asc"][1:12]]}
    spot={"symbols":[{"symbol":a+"USDT","status":"TRADING","baseAsset":a,"quoteAsset":"USDT","isSpotTradingAllowed":True} for a in sig["preliminary_longs_10"]]}
    up=tmp_path/"u.json"; sp=tmp_path/"s.json"; up.write_text(json.dumps(usdm)); sp.write_text(json.dumps(spot))
    r=entry_builder.build(sig,up,sp); assert r["status"]=="OK" and r["entry_instruments"]["PEPE"]=="1000PEPEUSDT"
    spot["symbols"]=spot["symbols"][1:]; sp.write_text(json.dumps(spot))
    r2=entry_builder.build(sig,up,sp); assert r2["status"]=="BLOCKED" and r2["blocker_reason"].startswith("LONG_INSTRUMENT_UNAVAILABLE")
