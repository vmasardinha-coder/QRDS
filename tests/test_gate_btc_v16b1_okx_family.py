from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from tools import gate_btc_v16b1_chain as chain
from tools import gate_btc_v16b1_okx_entry as entry
from tools import gate_btc_v16b1_okx_result as result
from tools import gate_btc_v16b1_okx_signal as signal


def _signal_input():
    symbols=[f"A{i:02d}USDT" for i in range(30)]
    scores={s: float(30-i) for i,s in enumerate(symbols)}
    return {
        "signal_date_utc":"2026-09-17","entry_date_utc":"2026-09-18","candidate_id":chain.CANDIDATE_ID,
        "model_hash":"a"*64,"code_commit":"b"*40,"input_data_hashes":{"panel":"c"*64},
        "universe_snapshot_id":"cmc-test","universe_snapshot_available_at_utc":"2026-09-17T23:00:00Z",
        "panel_hash":"d"*64,"model_state_hash":"e"*64,"eligible_universe_count":30,"liquidity_qualified_count":30,
        "eligible_scores":scores,"long_ranking_desc":symbols,"short_ranking_asc":list(reversed(symbols)),
        "preliminary_longs_10":symbols[:10],"risk_state":{"exposure":1.0,"trailing_vol":None,"prior_weights":{}},
        "source_coverage":{"signal_market_source":{"availability":"HASH_BOUND"}},"status":"OK","blocker_reason":None,
    }


def _write(path: Path, obj):
    path.write_text(json.dumps(obj),encoding="utf-8"); return path


def _entry_files(tmp_path: Path, signal_event: dict, missing_okx: set[str] | None=None, post_only: set[str] | None=None):
    missing_okx=missing_okx or set(); post_only=post_only or set()
    symbols=list(signal_event["eligible_scores"])
    spot={"symbols":[{"symbol":s,"baseAsset":s.removesuffix("USDT"),"quoteAsset":"USDT","status":"TRADING","isSpotTradingAllowed":True} for s in symbols]}
    okx=[]
    for s in symbols:
        base=s.removesuffix("USDT")
        if s in missing_okx: continue
        okx.append({"instType":"SWAP","instId":f"{base}-USDT-SWAP","settleCcy":"USDT","state":"post_only" if s in post_only else "live"})
    okx_payload={"code":"0","data":okx}
    # Signal sealed at 00:15; both evidence clocks are causally after it and before Friday close.
    ms=int(pd.Timestamp("2026-09-18T01:00:00Z").timestamp()*1000)
    okx_time={"code":"0","data":[{"ts":str(ms)}]}; bin_time={"serverTime":ms}
    return (
        _write(tmp_path/"okx.json",okx_payload),_write(tmp_path/"okx_time.json",okx_time),
        _write(tmp_path/"spot.json",spot),_write(tmp_path/"bin_time.json",bin_time),
    )


def test_family_does_not_inherit_parent_shortability(tmp_path):
    p=tmp_path/"short.csv"
    pd.DataFrame([{"friday_utc":"2026-09-11","asset":"BTCUSDT"}]).to_csv(p,index=False)
    with pytest.raises(ValueError,match="cannot inherit"):
        signal._validate_v16b1_shortability_history(p,pd.Timestamp("2026-09-17"))
    pd.DataFrame(columns=["friday_utc","asset"]).to_csv(p,index=False)
    signal._validate_v16b1_shortability_history(p,pd.Timestamp("2026-09-17"))


def test_signal_entry_result_and_stress_children_end_to_end(tmp_path):
    sig=chain.validate_signal_row(_signal_input(),now=datetime(2026,9,18,0,15,tzinfo=timezone.utc))
    files=_entry_files(tmp_path,sig,missing_okx={"A29USDT"})
    ent_input=entry.build(sig,*files)
    assert ent_input["status"]=="OK"
    assert len(ent_input["shorts_10"])==10
    assert "A29USDT" not in ent_input["shorts_10"]
    assert ent_input["shorts_10"][0]=="A28USDT"
    assert all(ent_input["entry_instruments"][x].startswith("OKX_SWAP|") for x in ent_input["shorts_10"])
    ent=chain.validate_entry_row(ent_input,sig,now=datetime(2026,9,18,2,0,tzinfo=timezone.utc))

    prices={}
    for a in ent["longs_10"]:
        prices[a]={"instrument":ent["entry_instruments"][a],"entry_price":100.0,"exit_price":102.0,"source_hash":"1"*64}
    for a in ent["shorts_10"]:
        prices[a]={"instrument":ent["entry_instruments"][a],"entry_price":100.0,"exit_price":98.0,"source_hash":"2"*64}
    price_path=_write(tmp_path/"prices.json",{"assets":prices})
    funds={a:{"instrument":ent["entry_instruments"][a],"source_hash":"3"*64,"events":[{"funding_time":"2026-09-20T00:00:00Z","realized_rate":0.0001,"mark_price":99.0,"mark_price_source_hash":"4"*64}]} for a in ent["shorts_10"]}
    fund_path=_write(tmp_path/"funding.json",{"shorts":funds})
    btc_path=_write(tmp_path/"btc.json",{"instrument":"BINANCE_SPOT|BTCUSDT","entry_price":100000.0,"exit_price":101000.0,"source_hash":"5"*64})
    res_input=result.build(ent,price_path,fund_path,btc_path,"6"*64)
    res=chain.validate_result_row(res_input,ent,now=datetime(2026,9,26,0,1,tzinfo=timezone.utc))
    assert res["status"]=="OK"
    assert res["net_pnl"]>0
    kids=chain.derive_stress_children(res,ent)
    assert [x["child_id"] for x in kids]==["GATE_BTC_V16B1_OKX_COST30_STRESS","GATE_BTC_V16B1_OKX_COST50_STRESS"]
    assert kids[0]["net_pnl"]>kids[1]["net_pnl"]
    assert all(x["selection_power"] is False and x["same_holdings_as_core"] is True for x in kids)


def test_okx_post_only_is_not_admitted_for_short_entry(tmp_path):
    sig=chain.validate_signal_row(_signal_input(),now=datetime(2026,9,18,0,15,tzinfo=timezone.utc))
    files=_entry_files(tmp_path,sig,post_only={"A29USDT"})
    ent=entry.build(sig,*files)
    assert ent["status"]=="OK"
    assert ent["shorts_10"][0]=="A28USDT"
    assert "A29USDT" not in ent["shorts_10"]


def test_no_backfilled_signal():
    x=_signal_input(); x["signal_date_utc"]="2026-09-10"; x["entry_date_utc"]="2026-09-11"
    with pytest.raises(ValueError,match="invalid/pre-family"):
        chain.validate_signal_row(x,now=datetime(2026,9,11,0,15,tzinfo=timezone.utc))


def test_child_stress_cannot_exist_without_core_result():
    with pytest.raises(ValueError,match="sealed OK CORE"):
        chain.derive_stress_children({"event_type":"V16B1_RESULT_SEAL","status":"BLOCKED"},{})
