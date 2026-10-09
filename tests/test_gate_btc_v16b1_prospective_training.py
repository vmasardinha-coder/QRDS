import json
from pathlib import Path
import pandas as pd, pytest
from tools import gate_btc_v16b1_prospective_training as t
from tools import gate_btc_v16b_feature_panel as frozen

def fixture(tmp_path, label=None):
    row={"signal_date":"2026-10-08","symbol":"AAAUSDT","evidence_class":frozen.PROSPECTIVE_PIT,"snapshot_effective_date":"2026-10-08","retrieved_at_utc":"2026-10-08 21:00:00+00:00","universe_source_ref":"cmc","universe_snapshot_sha256":"a"*64,"prospective_eligible":True,"prospective_credit":0,"fwd_ret":label,"feature_ok":True}
    row.update({x:0.1 for x in frozen.FROZEN_FEATURES})
    panel=tmp_path/"panel.csv"; pd.DataFrame([row]).to_csv(panel,index=False)
    manifest=tmp_path/"manifest.json"; m={"producer_version":frozen.PRODUCER_VERSION,"features":list(frozen.FROZEN_FEATURES)}
    manifest.write_text(json.dumps(m)); m["panel_sha256"]=frozen.sha256_file(panel); manifest.write_text(json.dumps(m))
    return panel,manifest

def test_seal_then_mature_only_with_realized_label(tmp_path):
    panel,manifest=fixture(tmp_path); rt=tmp_path/"rt"
    out=t.seal_features(panel,manifest,rt,"2026-10-08","b"*40)
    assert out["label_status"]=="PENDING_FROZEN_EXIT" and out["scientific_credit"]==0
    with pytest.raises(ValueError,match="exit"):
        t.mature(panel,rt,"2026-10-08")
    panel,_=fixture(tmp_path,0.12)
    done=t.mature(panel,rt,"2026-10-08")
    assert done["label_status"]=="SEALED_AFTER_FROZEN_EXIT" and done["scientific_credit"]==0

def test_immutable_feature_seal(tmp_path):
    panel,manifest=fixture(tmp_path); rt=tmp_path/"rt"
    t.seal_features(panel,manifest,rt,"2026-10-08","b"*40)
    df=pd.read_csv(panel); df.loc[0,"mom7"]=9; df.to_csv(panel,index=False)
    m=json.loads(manifest.read_text()); m["panel_sha256"]=frozen.sha256_file(panel); manifest.write_text(json.dumps(m))
    with pytest.raises(ValueError,match="immutable"):
        t.seal_features(panel,manifest,rt,"2026-10-08","b"*40)

def test_reject_non_thursday(tmp_path):
    panel,manifest=fixture(tmp_path)
    with pytest.raises(ValueError,match="Thursday"):
        t.seal_features(panel,manifest,tmp_path/"rt","2026-10-09","b"*40)

def test_incomplete_symbol_is_excluded_with_audit_and_never_labeled(tmp_path):
    panel,manifest=fixture(tmp_path)
    frame=pd.read_csv(panel)
    invalid=frame.iloc[0].copy()
    invalid["symbol"]="NEWUSDT"
    invalid["mom90"]=float("nan")
    invalid["feature_ok"]=False
    pd.concat([frame,pd.DataFrame([invalid])],ignore_index=True).to_csv(panel,index=False)
    m=json.loads(manifest.read_text()); m["panel_sha256"]=frozen.sha256_file(panel); manifest.write_text(json.dumps(m))
    rt=tmp_path/"rt"
    out=t.seal_features(panel,manifest,rt,"2026-10-08","b"*40)
    d=rt/t.BASE/"weeks"/"2026-10-08"
    assert out["eligible_feature_rows"]==1 and out["excluded_incomplete_rows"]==1
    assert list(pd.read_csv(d/"FEATURES.csv").symbol)==["AAAUSDT"]
    audit=pd.read_csv(d/"EXCLUSIONS.csv")
    assert audit.iloc[0].symbol=="NEWUSDT" and audit.iloc[0].missing_features=="mom90"
    frame.loc[frame.symbol.eq("AAAUSDT"),"fwd_ret"]=0.12
    frame.to_csv(panel,index=False)
    done=t.mature(panel,rt,"2026-10-08")
    assert done["label_status"]=="SEALED_AFTER_FROZEN_EXIT"
    assert list(pd.read_csv(d/"LABELS.csv").symbol)==["AAAUSDT"]

def test_all_incomplete_rows_fail_closed(tmp_path):
    panel,manifest=fixture(tmp_path)
    frame=pd.read_csv(panel)
    frame.loc[0,"mom90"]=float("nan")
    frame.loc[0,"feature_ok"]=False
    frame.to_csv(panel,index=False)
    m=json.loads(manifest.read_text()); m["panel_sha256"]=frozen.sha256_file(panel); manifest.write_text(json.dumps(m))
    with pytest.raises(ValueError,match="no complete"):
        t.seal_features(panel,manifest,tmp_path/"rt","2026-10-08","b"*40)
