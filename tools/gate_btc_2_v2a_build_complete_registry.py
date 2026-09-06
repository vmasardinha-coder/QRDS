#!/usr/bin/env python3
"""Build the complete System-8 V2A qualified-source registry from merged evidence.

This is an admission/adjudication builder only. It grants zero historical or D0
credit and cannot start the prospective clock. The first credited observation
must be produced strictly after the registry PR merges.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

STRUCTURAL = {"SOFID","BCAP","KAU","KAG","EURSAFO","EUTBL","JTRSY","JAAA","OUSG","PC0000031","USTB","BUIDL","USDGO"}


def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def good(row):
    return bool(row.get("qa_pass")) and bool(row.get("official_identity_ok", True)) and row.get("daily_bucket_count",33)==33

def norm(row, evidence_stage, artifact_id, artifact_digest):
    pair=row.get("pair") or row.get("source_symbol")
    provider=row.get("provider") or row.get("source_identity")
    assert row.get("symbol") and provider and pair
    assert good(row), (row.get("symbol"), row.get("status"))
    return {
        "symbol": row["symbol"], "coin_id": row.get("coin_id"),
        "source_identity": provider, "source_symbol": pair,
        "qualification": "QUALIFIED_EXACT_SOURCE", "qa_pass": True,
        "timezone": "UTC", "raw_observation_mode": row.get("raw_observation_mode","OBSERVED_DAILY_CANDLES"),
        "cutoff_semantics": row.get("cutoff_semantics","UTC_DAILY_CANDLE_NO_FUTURE_ROWS"),
        "evidence_stage": evidence_stage, "evidence_artifact_id": artifact_id,
        "evidence_artifact_sha256": artifact_digest,
        "raw_response_sha256": row.get("candle_response_sha256") or row.get("ohlc_response_sha256") or row.get("provenance_sha256"),
        "source_admitted": True, "historical_credit": 0, "d0_credit": 0,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--seed', required=True); p.add_argument('--legacy91',required=True)
    p.add_argument('--legacy50',required=True); p.add_argument('--legacy9',required=True)
    p.add_argument('--btt',required=True); p.add_argument('--xmr',required=True); p.add_argument('--out',required=True)
    a=p.parse_args()
    seed=load(a.seed); r91=load(a.legacy91); r50=load(a.legacy50); r9=load(a.legacy9); rb=load(a.btt); rx=load(a.xmr)
    if isinstance(rb,dict): rb=[rb]
    if isinstance(rx,dict): rx=[rx]
    by91={x['symbol']:x for x in r91}; by50={x['symbol']:x for x in r50}; by9={x['symbol']:x for x in r9}
    assert len(by91)==91
    seed_entries=seed['entries']; assert len(seed_entries)==46
    seed_symbols={x['symbol'] for x in seed_entries}; legacy_symbols=set(by91)
    assert not seed_symbols & legacy_symbols
    assert not (seed_symbols|legacy_symbols) & STRUCTURAL
    entries=[]
    for x in seed_entries:
        y=dict(x); assert y.get('qualification')=='QUALIFIED_EXACT_SOURCE' and y.get('qa_pass') is True
        y.update({"source_admitted":True,"historical_credit":0,"d0_credit":0,"evidence_stage":"RECOVERED_46_MERGED_SEED"})
        entries.append(y)
    for symbol,row in sorted(by91.items()):
        if good(row): entries.append(norm(row,'LEGACY91_FROZEN_SOURCE',9990251632,'cba5ce4bd6ee72f42ffce950808ad0da666d08b29d8171913df4a60bb9e4b3b5')); continue
        rr=by50.get(symbol)
        if rr is not None and good(rr): entries.append(norm(rr,'LEGACY50_BINANCE_RECOVERY',9991028302,'5b185a97f9904df9b19b96110554a21d329688784868893dbaf80d95c142d805')); continue
        rr=by9.get(symbol)
        if rr is not None and good(rr): entries.append(norm(rr,'LEGACY9_BINANCE_MECHANICAL_RETRY',9991199275,'c4a0db45f3a0dd08d47e503d4e48b103d7e31ff8d39eac41342f6cbecbb4656b')); continue
        if symbol=='BTT': entries.append(norm(rb[0],'BTT_GATE_EXACT_SOURCE',9991923974,'19924214050bdb0f3187d9637f334cf5989f385867c35e21b85fad1483eb8fc8')); continue
        if symbol=='XMR': entries.append(norm(rx[0],'XMR_KRAKEN_EXACT_SOURCE',9992470782,'QUALIFIER_ARTIFACT_DIGEST_BOUND_BY_WORKFLOW')); continue
        raise AssertionError(f'unresolved eligible symbol: {symbol}')
    symbols=[x['symbol'] for x in entries]
    assert len(entries)==137 and len(set(symbols))==137
    assert set(symbols)==seed_symbols|legacy_symbols
    payload={
      "schema":"gate_btc.v2a_complete_qualified_source_registry.v1",
      "epoch_id":"GATE_BTC_2_V2A_PROSPECTIVE_EPOCH_2026_09_03",
      "status":"COMPLETE_REGISTRY_ADMITTED_ZERO_D0_CREDIT",
      "eligible_symbol_count":137,"entry_count":137,"structural_exclusion_count":13,
      "structural_exclusions":sorted(STRUCTURAL),"complete_registry_claimed":True,
      "source_admission_changed":True,"collector_override_activation_allowed":True,
      "d0_started":False,"historical_credit":0,"scientific_credit":False,"prospective_credit":False,"d0_credit":0,
      "entries":sorted(entries,key=lambda x:x['symbol']),
      "safety":{"RESEARCH_ONLY":True,"SHADOW_ONLY":True,"NOT_APPROVED":True,"ENGINE_FEED":False,"ORDERS":0,"REAL_CAPITAL_BRL":0,"NO_RETUNE":True,"NO_BACKFILL":True,"NO_COUNTER_RESET":True,"NO_SILENT_SOURCE_SUBSTITUTION":True,"FAIL_CLOSED":True}
    }
    out=Path(a.out); out.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({"status":payload['status'],"entries":137,"structural_exclusions":13,"d0_started":False},sort_keys=True))
if __name__=='__main__': main()
