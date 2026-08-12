#!/usr/bin/env python3
from __future__ import annotations

import argparse, io, json, zipfile, hashlib, re, time
from pathlib import Path
import requests
import pandas as pd
import numpy as np

URL = "https://arquivos.b3.com.br/rapinegocios/tickercsv/{date}"
USECOLS = [
    "CodigoInstrumento","AcaoAtualizacao","PrecoNegocio","QuantidadeNegociada",
    "HoraFechamento","CodigoIdentificadorNegocio","TipoSessaoPregao"
]
CHUNK = 500_000

def dump(p,o):
    Path(p).write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def sha(b): return hashlib.sha256(b).hexdigest()

def brnum(s):
    return pd.to_numeric(
        s.astype(str).str.replace(".","",regex=False).str.replace(",",".",regex=False),
        errors="raise"
    )

def time_ms(series):
    s = series.astype(str).str.strip()
    has_colon = s.str.contains(":", regex=False)
    out = pd.Series(index=s.index, dtype="int64")
    if has_colon.any():
        a = s[has_colon].str.extract(r"(?P<h>\d{1,2}):(?P<m>\d{2}):(?P<sec>\d{2})(?:\.(?P<ms>\d{1,3}))?")
        ms = a["ms"].fillna("0").str.pad(3, side="right", fillchar="0").str[:3].astype(int)
        out.loc[has_colon] = ((a["h"].astype(int)*60+a["m"].astype(int))*60+a["sec"].astype(int))*1000+ms
    if (~has_colon).any():
        d = s[~has_colon].str.replace(r"\D","",regex=True)
        h=d.str[:2].astype(int); m=d.str[2:4].astype(int); sec=d.str[4:6].astype(int)
        ms=d.str[6:9].fillna("").str.pad(3,side="right",fillchar="0").replace("", "0").astype(int)
        out.loc[~has_colon]=((h*60+m)*60+sec)*1000+ms
    return out.astype("int64")

def bucket_min_from_ms(ms, size):
    mins = (ms // 60000).astype("int64")
    return (mins // size) * size

def newer_key(t1,id1,t2,id2):
    if t1 != t2: return t1 > t2
    return str(id1) > str(id2)

def older_key(t1,id1,t2,id2):
    if t1 != t2: return t1 < t2
    return str(id1) < str(id2)

def merge_agg(store, rows):
    for r in rows.itertuples(index=False):
        key=(r.root,int(r.bucket_min))
        cur=store.get(key)
        if cur is None:
            store[key]={
                "open":float(r.open),"high":float(r.high),"low":float(r.low),"close":float(r.close),
                "volume":float(r.volume),"trades":int(r.trades),
                "first_time":int(r.first_time),"first_id":str(r.first_id),
                "last_time":int(r.last_time),"last_id":str(r.last_id),
            }
        else:
            cur["high"]=max(cur["high"],float(r.high))
            cur["low"]=min(cur["low"],float(r.low))
            cur["volume"]+=float(r.volume); cur["trades"]+=int(r.trades)
            if older_key(int(r.first_time),str(r.first_id),cur["first_time"],cur["first_id"]):
                cur["first_time"]=int(r.first_time); cur["first_id"]=str(r.first_id); cur["open"]=float(r.open)
            if newer_key(int(r.last_time),str(r.last_id),cur["last_time"],cur["last_id"]):
                cur["last_time"]=int(r.last_time); cur["last_id"]=str(r.last_id); cur["close"]=float(r.close)

def aggregate_chunk(x, size):
    if x.empty:
        return pd.DataFrame()
    x=x.copy()
    x["bucket_min"]=bucket_min_from_ms(x["time_ms"],size)
    x=x.sort_values(["root","bucket_min","time_ms","trade_id"],kind="mergesort")
    g=x.groupby(["root","bucket_min"],sort=False)
    core=g.agg(
        high=("price","max"), low=("price","min"),
        volume=("qty","sum"), trades=("trade_id","size"),
        first_time=("time_ms","first"), first_id=("trade_id","first"),
        last_time=("time_ms","last"), last_id=("trade_id","last"),
        open=("price","first"), close=("price","last")
    ).reset_index()
    return core

def dataframe_from_store(store,date,front):
    rows=[]
    for (root,b),v in sorted(store.items(), key=lambda kv:(kv[0][0],kv[0][1])):
        hh=b//60; mm=b%60
        ts=pd.Timestamp(f"{date} {hh:02d}:{mm:02d}", tz="America/Sao_Paulo")
        rows.append({
            "timestamp":ts.isoformat(),"date":date,"root":root,"symbol":front[root],
            "open":v["open"],"high":v["high"],"low":v["low"],"close":v["close"],
            "volume":v["volume"],"trades":v["trades"]
        })
    return pd.DataFrame(rows)

def process_zip(raw,date,front):
    z=zipfile.ZipFile(io.BytesIO(raw))
    files=[x for x in z.infolist() if not x.is_dir()]
    if len(files)!=1:
        z.close(); raise RuntimeError(f"ZIP member count {len(files)}")
    m=files[0]
    if "_NEGOCIOSAVISTA.TXT" not in m.filename.upper():
        z.close(); raise RuntimeError(f"unexpected member {m.filename}")

    s1={}; s5={}
    stats={"source_rows":0,"front_rows":0,"kept_rows":0,"cancel_rows":0,
           "unknown_actions":[],"off_lattice":0}
    with z.open(m) as fh:
        for ch in pd.read_csv(
            fh, sep=";", encoding="iso-8859-1", usecols=USECOLS,
            dtype=str, chunksize=CHUNK, low_memory=False
        ):
            stats["source_rows"] += len(ch)
            ch["CodigoInstrumento"]=ch["CodigoInstrumento"].astype(str).str.strip().str.upper()
            x=ch[ch["CodigoInstrumento"].isin([front["WIN"],front["WDO"]])].copy()
            if x.empty: continue
            stats["front_rows"] += len(x)
            x["root"]=np.where(x["CodigoInstrumento"].eq(front["WIN"]),"WIN","WDO")

            act=pd.to_numeric(x["AcaoAtualizacao"].fillna("0").replace("", "0"),errors="coerce")
            bad=act[~act.isin([0,2]) & act.notna()]
            if len(bad):
                stats["unknown_actions"].extend(sorted(set(bad.astype(str).tolist())))
            stats["cancel_rows"] += int((act==2).sum())
            x=x[act.eq(0)].copy()

            sess=pd.to_numeric(x["TipoSessaoPregao"],errors="coerce")
            x=x[sess.isna() | sess.eq(1)].copy()
            if x.empty: continue

            x["price"]=brnum(x["PrecoNegocio"])
            x["qty"]=brnum(x["QuantidadeNegociada"])
            x["trade_id"]=x["CodigoIdentificadorNegocio"].astype(str).str.strip()
            x["time_ms"]=time_ms(x["HoraFechamento"])

            mins=(x["time_ms"]//60000).astype(int)
            x=x[(mins>=9*60)&(mins<17*60+30)].copy()
            if x.empty: continue

            ztick=np.where(x["root"].eq("WIN"),5.0,0.5)
            ratio=x["price"].to_numpy()/ztick
            ok=np.abs(ratio-np.round(ratio)) <= 1e-7*np.maximum(1.0,np.abs(ratio))
            stats["off_lattice"] += int((~ok).sum())
            x=x.loc[ok].copy()
            stats["kept_rows"] += len(x)

            merge_agg(s1, aggregate_chunk(x,1))
            merge_agg(s5, aggregate_chunk(x,5))
    z.close()

    if stats["cancel_rows"] or stats["unknown_actions"] or stats["off_lattice"]:
        raise RuntimeError(f"fail-closed front update/lattice: {stats}")

    return dataframe_from_store(s1,date,front), dataframe_from_store(s5,date,front), stats, m.filename
