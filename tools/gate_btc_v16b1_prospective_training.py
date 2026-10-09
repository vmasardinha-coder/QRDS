#!/usr/bin/env python3
"""Append-only V16B.1 prospective training corpus.

Plumbing only: persists frozen feature rows already produced by the authoritative
V16B panel and matures fwd_ret only after the frozen exit. No backfill/retune.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import pandas as pd
from tools import gate_btc_v16b_feature_panel as frozen

BASE=Path("runtime/evidence/v16b1/prospective_training")
FEATURES=list(frozen.FROZEN_FEATURES)

def sha(b:bytes)->str: return hashlib.sha256(b).hexdigest()
def enc(o)->bytes: return (json.dumps(o,indent=2,sort_keys=True)+"\n").encode()
def immutable(p:Path,b:bytes):
    if p.exists():
        if p.read_bytes()!=b: raise ValueError("immutable evidence conflict: "+str(p))
    else:
        p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(b)

def seal_features(panel_path:Path, manifest_path:Path, runtime:Path, signal_date:str, source_sha:str):
    p=pd.read_csv(panel_path); m=json.loads(manifest_path.read_text())
    if m.get("producer_version")!=frozen.PRODUCER_VERSION or m.get("features")!=FEATURES: raise ValueError("frozen feature contract mismatch")
    if m.get("panel_sha256")!=frozen.sha256_file(panel_path): raise ValueError("panel hash mismatch")
    s=pd.Timestamp(signal_date).normalize()
    if s.weekday()!=3: raise ValueError("signal must be Thursday")
    q=p[p.signal_date.astype(str).eq(s.date().isoformat())].copy()
    if q.empty or not q.evidence_class.eq(frozen.PROSPECTIVE_PIT).all(): raise ValueError("prospective PIT rows required")
    if q.symbol.duplicated().any(): raise ValueError("duplicate prospective feature symbol")
    # The frozen source contract excludes incomplete feature rows; no filling
    # or replacement symbol is allowed. Preserve every excluded identity.
    bad=q[~q.feature_ok.astype(bool)].copy()
    exclusions=pd.DataFrame([
        {"symbol":str(row.symbol),
         "reason":"INCOMPLETE_FROZEN_FEATURES",
         "missing_features":",".join(name for name in FEATURES if pd.isna(getattr(row,name)))}
        for row in bad.itertuples(index=False)
    ],columns=["symbol","reason","missing_features"]).sort_values("symbol")
    q=q[q.feature_ok.astype(bool)].copy()
    if q.empty: raise ValueError("no complete frozen features")
    cols=["signal_date","symbol","evidence_class","snapshot_effective_date","retrieved_at_utc","universe_source_ref","universe_snapshot_sha256"]+FEATURES+["feature_ok"]
    q=q[cols].sort_values("symbol")
    data=q.to_csv(index=False,lineterminator="\n").encode()
    excluded=exclusions.to_csv(index=False,lineterminator="\n").encode()
    d=runtime/BASE/"weeks"/s.date().isoformat()
    immutable(d/"FEATURES.csv",data)
    immutable(d/"EXCLUSIONS.csv",excluded)
    meta={"schema":"gate_btc.v16b1.prospective_training_week.v1","signal_date":s.date().isoformat(),"entry_date":(s+pd.Timedelta(days=1)).date().isoformat(),"exit_date":(s+pd.Timedelta(days=8)).date().isoformat(),"features_sha256":sha(data),"exclusions_sha256":sha(excluded),"eligible_feature_rows":int(len(q)),"excluded_incomplete_rows":int(len(bad)),"panel_manifest_sha256":frozen.sha256_file(manifest_path),"source_code_sha":source_sha,"label_status":"PENDING_FROZEN_EXIT","scientific_credit":0,"RESEARCH_ONLY":True,"SHADOW_ONLY":True,"NOT_APPROVED":True,"ENGINE_FEED":False,"ORDERS":0,"REAL_CAPITAL":0,"NO_BACKFILL":True,"NO_RETUNE":True,"NO_COUNTER_RESET":True,"FAIL_CLOSED":True}
    immutable(d/"WEEK.json",enc(meta)); return meta

def mature(panel_path:Path, runtime:Path, signal_date:str):
    s=pd.Timestamp(signal_date).normalize(); d=runtime/BASE/"weeks"/s.date().isoformat()
    meta=json.loads((d/"WEEK.json").read_text()); p=pd.read_csv(panel_path)
    features=pd.read_csv(d/"FEATURES.csv")
    if sha((d/"FEATURES.csv").read_bytes()) != meta["features_sha256"]: raise ValueError("features hash mismatch")
    if sha((d/"EXCLUSIONS.csv").read_bytes()) != meta["exclusions_sha256"]: raise ValueError("exclusions hash mismatch")
    q=p[p.signal_date.astype(str).eq(s.date().isoformat())][["symbol","fwd_ret"]]
    if q.symbol.duplicated().any(): raise ValueError("duplicate label symbol")
    q=q[q.symbol.astype(str).isin(features.symbol.astype(str))].sort_values("symbol")
    if q.empty or q.fwd_ret.isna().any(): raise ValueError("frozen exit not fully available")
    if sorted(features.symbol.astype(str))!=sorted(q.symbol.astype(str)): raise ValueError("label universe mismatch")
    data=q.to_csv(index=False,lineterminator="\n").encode(); immutable(d/"LABELS.csv",data)
    sealed={**meta,"labels_sha256":sha(data),"label_status":"SEALED_AFTER_FROZEN_EXIT","scientific_credit":0}
    immutable(d/"MATURED.json",enc(sealed)); return sealed

def main():
    a=argparse.ArgumentParser(); sub=a.add_subparsers(dest="cmd",required=True)
    f=sub.add_parser("seal-features"); f.add_argument("--panel",required=True); f.add_argument("--manifest",required=True); f.add_argument("--runtime-root",required=True); f.add_argument("--signal-date",required=True); f.add_argument("--source-sha",required=True)
    m=sub.add_parser("mature-labels"); m.add_argument("--panel",required=True); m.add_argument("--runtime-root",required=True); m.add_argument("--signal-date",required=True)
    x=a.parse_args()
    out=seal_features(Path(x.panel),Path(x.manifest),Path(x.runtime_root),x.signal_date,x.source_sha) if x.cmd=="seal-features" else mature(Path(x.panel),Path(x.runtime_root),x.signal_date)
    print(json.dumps(out,sort_keys=True))
if __name__=="__main__": main()
