from datetime import datetime
from pathlib import Path
import hashlib
import json
import subprocess
import pytest
from tools import gate_btc_v16b1_universe_corpus as corpus

SHA = "a" * 40

def capture(root, day="2026-10-01", hour="21"):
    root.mkdir(parents=True)
    rows = [{"id": i, "symbol": "ASSET"+str(i), "slug": "asset-"+str(i), "rank": i} for i in range(1,151)]
    raw = json.dumps({"data": rows}).encode()
    sid = "CMC_TEST_"+day+"_"+hour
    (root / (sid+".raw.json")).write_bytes(raw)
    ev = {"schema": "gate_btc.v16b.cmc_universe_snapshot_evidence.v1", "snapshot_id":sid,
          "snapshot_date":day, "available_at_utc":day+"T"+hour+":00:00Z",
          "source_ref":"https://pro-api.coinmarketcap.com/public-api/v1/cryptocurrency/map",
          "raw_snapshot_sha256":hashlib.sha256(raw).hexdigest(), "rows":150,
          "research_only":True,"shadow_only":True,"not_approved":True,"engine_feed":False,
          "orders":0,"real_capital":0}
    (root / (sid+".evidence.json")).write_text(json.dumps(ev))
    return root

def run(cap, runtime, run_id="100", day="2026-10-01"):
    return corpus.persist(cap,runtime,run_id,SHA,datetime.fromisoformat(day+"T23:30:00+00:00"))

def test_live_thursday_and_retry_preserve_raw_and_week(tmp_path):
    cap=capture(tmp_path/"cap"); rt=tmp_path/"rt"
    a=run(cap,rt); b=run(cap,rt)
    assert a == b and a["observed_week_count"] == 1
    assert not a["training_ready"] and not a["historical_training_input_replaced"]
    assert a["prospective_credit"] == 0
    for p in cap.iterdir():
        assert p.read_bytes() == (rt/corpus.BASE/"captures/run_100"/p.name).read_bytes()

def test_saturday_proves_capture_without_week_credit(tmp_path):
    out=run(capture(tmp_path/"cap","2026-09-26"),tmp_path/"rt",day="2026-09-26")
    assert out["observed_week_count"] == 0
    assert out["status"] == "WAITING_FIRST_ELIGIBLE_THURSDAY"
    assert out["latest_capture"]["rows"] == 150

@pytest.mark.parametrize("capture_day,now_day",[
    ("2026-09-24","2026-09-24"), ("2026-10-01","2026-10-02"), ("2026-10-02","2026-10-01")])
def test_old_late_and_future_captures_rejected(tmp_path,capture_day,now_day):
    with pytest.raises(ValueError,match="cutover|same-day"):
        run(capture(tmp_path/"cap",capture_day),tmp_path/"rt",day=now_day)
    assert not (tmp_path/"rt").exists()

def test_hash_tampering_rejected_before_write(tmp_path):
    cap=capture(tmp_path/"cap")
    next(cap.glob("*.raw.json")).write_text("{}")
    with pytest.raises(ValueError,match="hash mismatch"):
        run(cap,tmp_path/"rt")
    assert not (tmp_path/"rt").exists()

def test_duplicate_rank_rejected_with_valid_hash(tmp_path):
    cap=capture(tmp_path/"cap")
    raw=next(cap.glob("*.raw.json")); evp=next(cap.glob("*.evidence.json"))
    data=json.loads(raw.read_text()); data["data"][1]["rank"]=1
    raw.write_text(json.dumps(data)); ev=json.loads(evp.read_text())
    ev["raw_snapshot_sha256"]=hashlib.sha256(raw.read_bytes()).hexdigest()
    evp.write_text(json.dumps(ev))
    with pytest.raises(ValueError,match="Top-150"):
        run(cap,tmp_path/"rt")

def test_first_valid_week_is_immutable_and_two_captures_count_once(tmp_path):
    rt=tmp_path/"rt"; run(capture(tmp_path/"cap1"),rt)
    selected=rt/corpus.BASE/"weeks/2026-10-01/UNIVERSE.json"
    before=selected.read_bytes()
    out=run(capture(tmp_path/"cap2",hour="23"),rt,"101")
    assert selected.read_bytes()==before and out["observed_week_count"]==1
    assert len(list((rt/corpus.BASE/"captures").glob("run_*")))==2

def test_corrupt_immutable_capture_is_not_repaired(tmp_path):
    rt=tmp_path/"rt"; cap=capture(tmp_path/"cap"); run(cap,rt)
    archived=next((rt/corpus.BASE/"captures/run_100").glob("*.raw.json"))
    archived.write_bytes(b"corrupt")
    with pytest.raises(ValueError,match="immutable"):
        run(cap,rt)
    assert archived.read_bytes()==b"corrupt"

def test_non_thursday_capture_preserves_existing_historical_input(tmp_path):
    rt=tmp_path/"rt"; hist=rt/"runtime/ledgers/v16b1/HISTORICAL_WEEKLY_UNIVERSE_MODEL_ONLY.csv"
    hist.parent.mkdir(parents=True); hist.write_bytes(b"authoritative existing bytes")
    run(capture(tmp_path/"cap","2026-09-26"),rt,day="2026-09-26")
    assert hist.read_bytes()==b"authoritative existing bytes"

def test_first_new_corpus_is_visible_to_publication_git_check(tmp_path):
    rt=tmp_path/"rt"; rt.mkdir()
    subprocess.run(["git","init",str(rt)],check=True,capture_output=True)
    run(capture(tmp_path/"cap","2026-09-26"),rt,day="2026-09-26")
    subprocess.run(["git","-C",str(rt),"add","--",str(corpus.BASE)],check=True,capture_output=True)
    assert subprocess.run(["git","-C",str(rt),"diff","--cached","--quiet"]).returncode==1
