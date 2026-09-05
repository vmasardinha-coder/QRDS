#!/usr/bin/env python3
"""Physical, fail-closed qualification of the 2026-09-05 preregistered V2A source batch.

Scientific/source failures are evidence and do not make this evidence-capture process
itself fail. Mechanical inability to write the batch summary does fail. No source is
admitted here and no historical/prospective/D0 credit is granted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

UA = "QRDS-GateBTC2-ResearchOnly/1"
END = date(2026, 9, 4)
START = END - timedelta(days=32)

TARGETS = {
    "USDY": {"coin_id":"ondo-us-dollar-yield","kind":"gate","pair":"USDY_USDT","base":"USDY","quote":"USDT"},
    "GHO": {"coin_id":"gho","kind":"gate","pair":"GHO_USDT","base":"GHO","quote":"USDT"},
    "USDGO": {"coin_id":"usdgo","kind":"kraken","pair":"USDGO/USD","base":"USDGO","quote":"USD"},
    "APXUSD": {"coin_id":"apxusd","kind":"kraken","pair":"APXUSD/USD","base":"APXUSD","quote":"USD"},
    "AUSD": {"coin_id":"agora-dollar","kind":"kraken","pair":"AUSD/USD","base":"AUSD","quote":"USD"},
    "USELESS": {"coin_id":"useless-3","kind":"coinbase","pair":"USELESS-USD","base":"USELESS","quote":"USD"},
    "A7A5": {"coin_id":"a7a5","kind":"gecko","network":"eth","pool":"0x14d7aab5b4bca6a02e52ac22520b033bf35f4091","base":"A7A5","quote":"USDT"},
    "USDAI": {"coin_id":"usdai","kind":"gecko","network":"arbitrum","pool":"0xba9ed8ae94c70ef9aa2cd1045ed473aaa405c6c7","base":"USDAI","quote":"USDC"},
    "REUSD": {"coin_id":"re-protocol-reusd","kind":"gecko","network":"eth","pool":"0xb96cee75211700bc148b95b1c907d726791f4457","base":"REUSD","quote":"USDT"},
    "CRVUSD": {"coin_id":"crvusd","kind":"gecko","network":"eth","pool":"0x4dece678ceceb27446b35c672dc7d61f30bad69e","base":"CRVUSD","quote":"USDC"},
    "EURCV": {"coin_id":"societe-generale-forge-eurcv","kind":"gecko","network":"eth","pool":"0x1f195908f2ee7a6fc15d33b30c82298f568e805c","base":"EURCV","quote":"USDC"},
}


def req(url: str, retries: int = 4) -> bytes:
    last = None
    for n in range(retries):
        try:
            r = urllib.request.Request(url, headers={"Accept":"application/json","User-Agent":UA,"Accept-Version":"20230302"})
            with urllib.request.urlopen(r, timeout=60) as resp:
                return resp.read()
        except Exception as exc:
            last = exc
            time.sleep(2 ** n)
    raise RuntimeError(f"request failed after {retries} attempts: {url}: {last}")


def dump_raw(out: Path, name: str, raw: bytes) -> str:
    (out / name).write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def day(ts: int) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).date().isoformat()


def assess(rows: list[dict]) -> dict:
    rows = sorted(rows, key=lambda x: x["timestamp"])
    timestamps = [r["timestamp"] for r in rows]
    duplicate_rows = len(timestamps) - len(set(timestamps))
    monotonic = all(timestamps[i] < timestamps[i+1] for i in range(len(timestamps)-1))
    have = {r["day"] for r in rows}
    missing = []
    cur = START
    while cur <= END:
        if cur.isoformat() not in have:
            missing.append(cur.isoformat())
        cur += timedelta(days=1)
    return {
        "physical_rows_ok": len(rows),
        "earliest_day": rows[0]["day"] if rows else None,
        "latest_day": rows[-1]["day"] if rows else None,
        "duplicate_rows": duplicate_rows,
        "monotonic": monotonic,
        "missing_days_in_requested_window": missing,
        "qa_pass": len(rows) == 33 and duplicate_rows == 0 and monotonic and not missing,
    }


def valid_ohlc(o: float, h: float, l: float, c: float, v: float) -> bool:
    return all(x == x for x in (o,h,l,c,v)) and v >= 0 and not (o == h == l == c == 0.0) and l <= min(o,c) <= max(o,c) <= h


def qualify_gate(symbol: str, cfg: dict, out: Path) -> tuple[list[dict], dict]:
    base = "https://api.gateio.ws/api/v4"
    ident_raw = req(f"{base}/spot/currency_pairs/{cfg['pair']}")
    ident_sha = dump_raw(out, "RAW_IDENTITY.json", ident_raw)
    ident = json.loads(ident_raw)
    if ident.get("id") != cfg["pair"] or str(ident.get("base","")).upper() != cfg["base"] or str(ident.get("quote","")).upper() != cfg["quote"]:
        raise ValueError("Gate exact instrument identity mismatch")
    start_ts = int(datetime.combine(START, datetime.min.time(), tzinfo=timezone.utc).timestamp())
    end_ts = int(datetime.combine(END + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc).timestamp()) - 1
    q = urllib.parse.urlencode({"currency_pair":cfg["pair"],"interval":"1d","from":start_ts,"to":end_ts})
    raw = req(f"{base}/spot/candlesticks?{q}")
    candle_sha = dump_raw(out, "RAW_OHLCV.json", raw)
    payload = json.loads(raw)
    if not isinstance(payload, list):
        raise ValueError(f"Gate candle envelope/error: {payload}")
    rows = []
    for x in payload:
        if not isinstance(x,list) or len(x) < 7:
            raise ValueError("Gate candle schema mismatch")
        ts=int(float(x[0])); qv=float(x[1]); c=float(x[2]); h=float(x[3]); l=float(x[4]); o=float(x[5]); v=float(x[6])
        d=date.fromisoformat(day(ts))
        if START <= d <= END:
            if not valid_ohlc(o,h,l,c,v) or qv < 0: raise ValueError("Gate OHLC/volume invariant failed")
            rows.append({"timestamp":ts,"day":d.isoformat(),"open":o,"high":h,"low":l,"close":c,"base_volume":v,"quote_volume":qv})
    return rows, {"provider":"GATE","source_identity":cfg["pair"],"identity":ident,"raw_sha256":{"identity":ident_sha,"ohlcv":candle_sha}}


def qualify_kraken(symbol: str, cfg: dict, out: Path) -> tuple[list[dict], dict]:
    base = "https://api.kraken.com/0/public"
    assets_raw=req(f"{base}/Assets"); pairs_raw=req(f"{base}/AssetPairs")
    sha_assets=dump_raw(out,"RAW_ASSETS.json",assets_raw); sha_pairs=dump_raw(out,"RAW_PAIRS.json",pairs_raw)
    assets=json.loads(assets_raw); pairs=json.loads(pairs_raw)
    if assets.get("error") or pairs.get("error"): raise ValueError("Kraken metadata error")
    b=cfg["base"].upper(); q=cfg["quote"].upper(); hits=[]
    for key,obj in (pairs.get("result") or {}).items():
        alt=str(obj.get("altname","")).upper(); ws=str(obj.get("wsname","")).upper(); base_asset=str(obj.get("base","")).upper().lstrip("XZ"); quote_asset=str(obj.get("quote","")).upper().lstrip("XZ")
        if (ws == f"{b}/{q}" or (alt.startswith(b) and quote_asset == q) or (base_asset == b and quote_asset == q)):
            hits.append((key,obj))
    if len(hits) != 1: raise ValueError(f"Kraken exact pair not uniquely present: {len(hits)}")
    key, ident=hits[0]; pair_arg=str(ident.get("altname") or key)
    since=int(datetime.combine(START, datetime.min.time(), tzinfo=timezone.utc).timestamp())
    raw=req(f"{base}/OHLC?"+urllib.parse.urlencode({"pair":pair_arg,"interval":1440,"since":since}))
    sha_ohlc=dump_raw(out,"RAW_OHLCV.json",raw); payload=json.loads(raw)
    if payload.get("error"): raise ValueError(f"Kraken OHLC error: {payload.get('error')}")
    series=next((v for k,v in (payload.get("result") or {}).items() if k != "last" and isinstance(v,list)),[])
    rows=[]; sentinel=0
    for x in series:
        if len(x)<7: continue
        ts=int(x[0]); d=date.fromisoformat(day(ts))
        if START <= d <= END:
            o,h,l,c,v=map(float,[x[1],x[2],x[3],x[4],x[6]])
            if ts<=0 or not valid_ohlc(o,h,l,c,v): sentinel += 1; continue
            rows.append({"timestamp":ts,"day":d.isoformat(),"open":o,"high":h,"low":l,"close":c,"volume":v})
    return rows, {"provider":"KRAKEN","source_identity":pair_arg,"identity":ident,"sentinel_rows_rejected":sentinel,"raw_sha256":{"assets":sha_assets,"pairs":sha_pairs,"ohlcv":sha_ohlc}}


def qualify_coinbase(symbol: str, cfg: dict, out: Path) -> tuple[list[dict], dict]:
    base="https://api.exchange.coinbase.com"
    ident_raw=req(f"{base}/products/{cfg['pair']}"); ident_sha=dump_raw(out,"RAW_IDENTITY.json",ident_raw); ident=json.loads(ident_raw)
    if ident.get("id") != cfg["pair"] or str(ident.get("base_currency","")).upper()!=cfg["base"] or str(ident.get("quote_currency","")).upper()!=cfg["quote"]:
        raise ValueError("Coinbase exact product identity mismatch")
    start=datetime.combine(START,datetime.min.time(),tzinfo=timezone.utc).isoformat().replace("+00:00","Z")
    end=datetime.combine(END+timedelta(days=1),datetime.min.time(),tzinfo=timezone.utc).isoformat().replace("+00:00","Z")
    raw=req(f"{base}/products/{cfg['pair']}/candles?"+urllib.parse.urlencode({"granularity":86400,"start":start,"end":end}))
    candle_sha=dump_raw(out,"RAW_OHLCV.json",raw); payload=json.loads(raw)
    if not isinstance(payload,list): raise ValueError(f"Coinbase candle envelope/error: {payload}")
    rows=[]
    for x in payload:
        if not isinstance(x,list) or len(x)<6: raise ValueError("Coinbase candle schema mismatch")
        ts=int(x[0]); l,h,o,c,v=map(float,x[1:6]); d=date.fromisoformat(day(ts))
        if START <= d <= END:
            if not valid_ohlc(o,h,l,c,v): raise ValueError("Coinbase OHLC/volume invariant failed")
            rows.append({"timestamp":ts,"day":d.isoformat(),"open":o,"high":h,"low":l,"close":c,"volume":v})
    return rows,{"provider":"COINBASE","source_identity":cfg["pair"],"identity":ident,"raw_sha256":{"identity":ident_sha,"ohlcv":candle_sha}}


def token_symbols(pool_payload: dict) -> set[str]:
    out=set()
    for item in pool_payload.get("included") or []:
        if item.get("type") == "token":
            a=item.get("attributes") or {}
            s=str(a.get("symbol","")).upper()
            if s: out.add(s)
    return out


def qualify_gecko(symbol: str, cfg: dict, out: Path) -> tuple[list[dict], dict]:
    base="https://api.geckoterminal.com/api/v2"; net=cfg["network"]; pool=cfg["pool"]
    ident_raw=req(f"{base}/networks/{net}/pools/{pool}?include=base_token,quote_token")
    ident_sha=dump_raw(out,"RAW_POOL.json",ident_raw); ident=json.loads(ident_raw); syms=token_symbols(ident)
    if cfg["base"].upper() not in syms or cfg["quote"].upper() not in syms:
        raise ValueError(f"GeckoTerminal pool token identity mismatch: {sorted(syms)}")
    end_ts=int(datetime.combine(END+timedelta(days=1),datetime.min.time(),tzinfo=timezone.utc).timestamp())-1
    q=urllib.parse.urlencode({"aggregate":1,"before_timestamp":end_ts,"limit":33,"currency":"usd"})
    raw=req(f"{base}/networks/{net}/pools/{pool}/ohlcv/day?{q}")
    ohlc_sha=dump_raw(out,"RAW_OHLCV.json",raw); payload=json.loads(raw)
    series=((((payload.get("data") or {}).get("attributes") or {}).get("ohlcv_list")) or [])
    rows=[]
    for x in series:
        if len(x)<6: continue
        ts=int(x[0]); d=date.fromisoformat(day(ts)); o,h,l,c,v=map(float,x[1:6])
        if START <= d <= END:
            if not valid_ohlc(o,h,l,c,v): raise ValueError("GeckoTerminal OHLC/volume invariant failed")
            rows.append({"timestamp":ts,"day":d.isoformat(),"open":o,"high":h,"low":l,"close":c,"volume":v})
    return rows,{"provider":"GECKOTERMINAL_PUBLIC_ONCHAIN","source_identity":f"{net}:{pool}","pool_token_symbols":sorted(syms),"raw_sha256":{"pool":ident_sha,"ohlcv":ohlc_sha}}


def qualify(symbol: str, root: Path) -> dict:
    cfg=TARGETS[symbol]; out=root/symbol.lower(); out.mkdir(parents=True,exist_ok=True)
    error=None; rows=[]; meta={}
    try:
        if cfg["kind"]=="gate": rows,meta=qualify_gate(symbol,cfg,out)
        elif cfg["kind"]=="kraken": rows,meta=qualify_kraken(symbol,cfg,out)
        elif cfg["kind"]=="coinbase": rows,meta=qualify_coinbase(symbol,cfg,out)
        elif cfg["kind"]=="gecko": rows,meta=qualify_gecko(symbol,cfg,out)
        else: raise ValueError("unsupported provider")
        qa=assess(rows)
        status="QUALIFIED_PHYSICAL_SOURCE_PENDING_SEPARATE_ADJUDICATION" if qa["qa_pass"] else "FAIL_CLOSED_FULL_CORPUS_QA"
    except Exception as exc:
        error=str(exc); qa=assess([]); status="FAIL_CLOSED_SOURCE_IDENTITY_OR_PARSE"
    summary={
        "schema_version":"GATE_BTC_2_V2A_SOURCE_QUALIFICATION_V1","symbol":symbol,"coin_id":cfg["coin_id"],
        "requested_start_utc":START.isoformat(),"requested_end_utc":END.isoformat(),"timezone":"UTC",
        "status":status,"error":error,**meta,**qa,
        "source_admitted":False,"historical_credit":0,"scientific_credit":False,"prospective_credit":False,"d0_credit":0,
        "qualification_only":True,"research_only":True,"shadow_only":True,"not_approved":True,"engine_feed":False,"orders":0,"real_capital_brl":0,
        "no_retune":True,"no_backfill":True,"no_counter_reset":True,"no_silent_source_substitution":True,"fail_closed":True,
    }
    (out/"CANDLES.jsonl").write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in sorted(rows,key=lambda x:x["timestamp"])),encoding="utf-8")
    (out/"SUMMARY.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return summary


def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--output",required=True); p.add_argument("--targets",default=",")
    a=p.parse_args(); root=Path(a.output); root.mkdir(parents=True,exist_ok=True)
    requested=[x.strip().upper() for x in a.targets.split(",") if x.strip()] if a.targets != "," else list(TARGETS)
    if not requested: requested=list(TARGETS)
    unknown=[x for x in requested if x not in TARGETS]
    if unknown: raise SystemExit(f"unknown targets: {unknown}")
    results=[qualify(s,root) for s in requested]
    batch={
        "schema_version":"GATE_BTC_2_V2A_SOURCE_QUALIFICATION_BATCH_V1","date":"2026-09-05","requested_end_utc":END.isoformat(),
        "targets":requested,"qualified_count":sum(1 for r in results if r["qa_pass"]),"failed_count":sum(1 for r in results if not r["qa_pass"]),
        "results":[{"symbol":r["symbol"],"status":r["status"],"qa_pass":r["qa_pass"],"error":r["error"]} for r in results],
        "source_admission_changed":False,"d0_started":False,"scientific_credit":False,"prospective_credit":False,
        "RESEARCH_ONLY":True,"SHADOW_ONLY":True,"NOT_APPROVED":True,"ENGINE_FEED":False,"ORDERS":0,"REAL_CAPITAL_BRL":0,"NO_RETUNE":True,"NO_BACKFILL":True,"NO_COUNTER_RESET":True,"NO_SILENT_SOURCE_SUBSTITUTION":True,"FAIL_CLOSED":True
    }
    (root/"BATCH_SUMMARY.json").write_text(json.dumps(batch,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(batch,indent=2,sort_keys=True))
    return 0

if __name__ == "__main__": raise SystemExit(main())
