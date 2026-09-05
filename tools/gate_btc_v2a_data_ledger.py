#!/usr/bin/env python3
"""Immutable V2A point-in-time universe and data-quality evidence ledger."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import os
from datetime import date
from pathlib import Path
from typing import Any

REQUIRED_UNIVERSE_COLUMNS = {"id", "symbol", "name", "market_cap_rank", "standard_ticker", "is_stable", "is_blocked"}
REQUIRED_QUALITY_COLUMNS = {"data_as_of", "attempted_symbols", "loaded_symbols", "failed_symbols", "coverage_ratio", "data_quality_status", "survivorship_bias_present"}
REQUIRED_FAILURE_COLUMNS = {"symbol", "reason"}

def require(condition: bool, message: str) -> None:
    if not condition: raise RuntimeError(message)
def sha256_bytes(raw: bytes) -> str: return hashlib.sha256(raw).hexdigest()
def canonical_sha(payload: dict[str, Any], field: str) -> str:
    clean=dict(payload); clean.pop(field,None)
    return sha256_bytes(json.dumps(clean,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8"))
def load_json(path: Path) -> dict[str, Any]: return json.loads(path.read_text(encoding="utf-8-sig"))
def read_csv(raw: bytes) -> tuple[list[str], list[dict[str,str]]]:
    r=csv.DictReader(io.StringIO(raw.decode("utf-8-sig"),newline="")); return list(r.fieldnames or []),list(r)
def atomic_json(path: Path,payload: dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+".partial")
    tmp.write_text(json.dumps(payload,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8"); os.replace(tmp,path)
def write_immutable_bytes(path: Path,raw: bytes)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists(): require(path.read_bytes()==raw,f"immutable file differs: {path}"); return
    tmp=path.with_suffix(path.suffix+".partial"); tmp.write_bytes(raw); os.replace(tmp,path)
def iso_day(value:str,field:str)->date:
    try:return date.fromisoformat(value)
    except ValueError as exc: raise RuntimeError(f"invalid {field}: {value}") from exc
def validate_archive(ledger_dir:Path,metadata:dict[str,Any])->None:
    path=ledger_dir/str(metadata.get("archive_path","")); require(path.is_file(),f"archive missing: {path}")
    compressed=path.read_bytes(); require(sha256_bytes(compressed)==metadata.get("archive_sha256"),f"archive hash mismatch: {path}")
    raw=gzip.decompress(compressed); require(sha256_bytes(raw)==metadata.get("raw_sha256"),f"raw hash mismatch: {path}"); require(len(raw)==int(metadata.get("raw_size_bytes",-1)),f"raw size mismatch: {path}")
def validate_record(path:Path,record:dict[str,Any],ledger_dir:Path)->None:
    require(record.get("record_sha256")==canonical_sha(record,"record_sha256"),f"invalid record hash: {path}")
    require(record.get("research_only") is True,f"research_only changed: {path}"); require(record.get("not_approved") is True,f"not_approved changed: {path}")
    require(record.get("feeds_frozen_engine") is False,f"V2A data ledger must not feed frozen engine: {path}"); require(record.get("retrospective_reconstruction") is False,f"retrospective reconstruction prohibited: {path}")
    for key in ("universe_archive","quality_archive","failures_archive"): validate_archive(ledger_dir,record[key])
def validated_records(ledger_dir:Path)->list[tuple[int,Path,dict[str,Any]]]:
    records=[]
    for path in (ledger_dir/"snapshots").glob("*.json"):
        record=load_json(path); validate_record(path,record,ledger_dir); sequence=int(record.get("sequence",0)); require(sequence>=1,f"invalid V2A data sequence: {path}"); records.append((sequence,path,record))
    records.sort(key=lambda x:x[0]); require([x[0] for x in records]==list(range(1,len(records)+1)),"V2A data ledger sequence is not contiguous"); return records
def archive_metadata(ledger_dir:Path,archive_rel:Path,raw:bytes)->dict[str,Any]:
    compressed=gzip.compress(raw,compresslevel=9,mtime=0); write_immutable_bytes(ledger_dir/archive_rel,compressed)
    return {"archive_path":archive_rel.as_posix(),"archive_sha256":sha256_bytes(compressed),"raw_sha256":sha256_bytes(raw),"raw_size_bytes":len(raw),"archive_format":"gzip_mtime_0_exact_source_bytes"}

def append(args:argparse.Namespace)->int:
    manifest=load_json(args.manifest); universe_raw=args.universe_csv.read_bytes(); quality_raw=args.quality_csv.read_bytes(); failures_raw=args.failures_csv.read_bytes()
    universe_columns,universe_rows=read_csv(universe_raw); quality_columns,quality_rows=read_csv(quality_raw); failure_columns,failure_rows=read_csv(failures_raw)
    require(REQUIRED_UNIVERSE_COLUMNS.issubset(set(universe_columns)),"V2A universe CSV missing required columns"); require(REQUIRED_QUALITY_COLUMNS.issubset(set(quality_columns)),"V2A quality CSV missing required columns"); require(REQUIRED_FAILURE_COLUMNS.issubset(set(failure_columns)),"V2A failures CSV missing required columns")
    require(len(quality_rows)==1,"V2A quality summary must contain exactly one row"); require(len(universe_rows)>0,"V2A current universe is empty")
    source_day=str(manifest.get("data_as_of","")); iso_day(source_day,"V2A data_as_of"); require(manifest.get("technical_status")=="PASS","V2A technical status must be PASS"); require(manifest.get("evidence_status")=="RESEARCH_ONLY_NOT_PROMOTED","V2A evidence boundary changed"); require(manifest.get("operational_status")=="NOT_APPROVED","V2A operational status changed"); require(manifest.get("real_orders")==0,"V2A real orders must remain zero"); require(manifest.get("capital_used")==0,"V2A real capital must remain zero"); require(args.source_run_id.isdigit(),"source_run_id must be a GitHub Actions numeric run ID")
    expected_id=f"{source_day}-run-{args.source_run_id}"; require(args.snapshot_id==expected_id,f"snapshot_id must equal {expected_id}")
    quality=quality_rows[0]; attempted=int(quality["attempted_symbols"]); loaded=int(quality["loaded_symbols"]); failed=int(quality["failed_symbols"]); coverage=float(quality["coverage_ratio"])
    require(quality["data_as_of"]==source_day,"V2A quality data_as_of differs from manifest"); require(attempted==int(manifest.get("attempted_symbols",-1)),"V2A attempted count differs from manifest"); require(loaded==int(manifest.get("loaded_symbols",-1)),"V2A loaded count differs from manifest"); require(failed==int(manifest.get("failed_symbols",-1)),"V2A failed count differs from manifest"); require(failed==len(failure_rows),"V2A failure rows differ from failed count"); require(attempted==loaded+failed,"V2A attempted != loaded + failed"); require(math.isclose(coverage,float(manifest.get("coverage_ratio",-1)),rel_tol=0.0,abs_tol=1e-12),"V2A coverage differs from manifest"); require(quality["survivorship_bias_present"].strip().lower()=="true","V2A historical survivorship-bias warning unexpectedly absent")
    ledger_dir=args.ledger_dir; record_path=ledger_dir/"snapshots"/f"{args.snapshot_id}.json"; source_hashes={"manifest_sha256":sha256_bytes(args.manifest.read_bytes()),"universe_sha256":sha256_bytes(universe_raw),"quality_sha256":sha256_bytes(quality_raw),"failures_sha256":sha256_bytes(failures_raw)}
    if record_path.exists():
        existing=load_json(record_path); validate_record(record_path,existing,ledger_dir); require(existing.get("source_hashes")==source_hashes,"immutable V2A point-in-time source bytes changed"); require(existing.get("source_run_id")==args.source_run_id,"existing V2A source run ID mismatch"); print(json.dumps({"result":"IDENTICAL_ALREADY_RECORDED","snapshot_id":args.snapshot_id,"sequence":existing.get("sequence"),"coverage_ratio":existing.get("coverage_ratio"),"counter_incremented":False,"feeds_frozen_engine":False},indent=2)); return 0
    records=validated_records(ledger_dir); previous=records[-1][2] if records else None
    if previous:
        require(iso_day(source_day,"V2A data_as_of")>=iso_day(str(previous.get("source_data_as_of")),"previous V2A data_as_of"),"V2A source date moved backwards; retrospective backfill is prohibited"); require(previous.get("source_run_id")!=args.source_run_id,"V2A source run already recorded")
    sequence=int(previous.get("sequence",0))+1 if previous else 1; prefix=Path("archives")/args.snapshot_id
    universe_archive=archive_metadata(ledger_dir,Path(str(prefix)+".coingecko_current_universe.csv.gz"),universe_raw); quality_archive=archive_metadata(ledger_dir,Path(str(prefix)+".data_quality_summary.csv.gz"),quality_raw); failures_archive=archive_metadata(ledger_dir,Path(str(prefix)+".download_failures.csv.gz"),failures_raw)
    short_history_failures=sum("only " in row["reason"] and " rows" in row["reason"] for row in failure_rows); no_candle_failures=sum("returned no candles" in row["reason"] for row in failure_rows)
    record={"schema":"gate_btc.v2a_point_in_time_data_snapshot.v1","sequence":sequence,"snapshot_id":args.snapshot_id,"source_data_as_of":source_day,"source_run_id":args.source_run_id,"source_run_utc":manifest.get("run_utc"),"v2a_version":manifest.get("version"),"attempted_symbols":attempted,"loaded_symbols":loaded,"failed_symbols":failed,"coverage_ratio":coverage,"universe_row_count":len(universe_rows),"download_failure_row_count":len(failure_rows),"short_history_failure_count":short_history_failures,"no_candle_failure_count":no_candle_failures,"survivorship_bias_present":True,"historical_model_survivorship_bias_present":True,"prospective_point_in_time_universe_observed":True,"prospective_point_in_time_universe_bias_present":False,"source_hashes":source_hashes,"universe_archive":universe_archive,"quality_archive":quality_archive,"failures_archive":failures_archive,"purpose":"FUTURE_POINT_IN_TIME_UNIVERSE_AND_DATA_QUALITY_EVIDENCE_ONLY","feeds_frozen_engine":False,"retrospective_reconstruction":False,"research_only":True,"shadow_only":True,"not_approved":True,"orders_generated":0,"real_capital_used":0,"promotion_allowed":False}
    record["record_sha256"]=canonical_sha(record,"record_sha256"); atomic_json(record_path,record)
    status={"schema":"gate_btc.v2a_point_in_time_data_ledger_status.v1","status":"ACTIVE_RESEARCH_ONLY","snapshot_count":sequence,"latest_snapshot_id":args.snapshot_id,"latest_source_data_as_of":source_day,"latest_source_run_id":args.source_run_id,"latest_attempted_symbols":attempted,"latest_loaded_symbols":loaded,"latest_failed_symbols":failed,"latest_coverage_ratio":coverage,"latest_short_history_failure_count":short_history_failures,"latest_no_candle_failure_count":no_candle_failures,"survivorship_bias_present":True,"historical_model_survivorship_bias_present":True,"prospective_point_in_time_universe_observed":True,"prospective_point_in_time_universe_bias_present":False,"future_point_in_time_only":True,"retrospective_backfill_allowed":False,"feeds_frozen_engine":False,"research_only":True,"shadow_only":True,"not_approved":True,"orders_generated":0,"real_capital_used":0,"promotion_allowed":False}
    status["status_sha256"]=canonical_sha(status,"status_sha256"); atomic_json(ledger_dir/"STATUS.json",status)
    print(json.dumps({"result":"APPENDED_V2A_POINT_IN_TIME_DATA_SNAPSHOT","snapshot_id":args.snapshot_id,"sequence":sequence,"attempted_symbols":attempted,"loaded_symbols":loaded,"failed_symbols":failed,"coverage_ratio":coverage,"short_history_failure_count":short_history_failures,"no_candle_failure_count":no_candle_failures,"historical_model_survivorship_bias_present":True,"prospective_point_in_time_universe_bias_present":False,"feeds_frozen_engine":False},indent=2)); return 0

def build_parser()->argparse.ArgumentParser:
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest="command",required=True); p=sub.add_parser("append"); p.add_argument("--manifest",type=Path,required=True); p.add_argument("--universe-csv",type=Path,required=True); p.add_argument("--quality-csv",type=Path,required=True); p.add_argument("--failures-csv",type=Path,required=True); p.add_argument("--snapshot-id",required=True); p.add_argument("--source-run-id",required=True); p.add_argument("--ledger-dir",type=Path,required=True); p.set_defaults(func=append); return parser
def main()->int:
    args=build_parser().parse_args()
    if os.environ.get("GATE_BTC_RESEARCH_ONLY","true").strip().lower() not in {"1","true","yes","on"}: raise RuntimeError("GATE_BTC_RESEARCH_ONLY must remain true")
    return int(args.func(args))
if __name__=="__main__": raise SystemExit(main())
