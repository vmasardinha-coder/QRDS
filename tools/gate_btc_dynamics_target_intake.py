"""Hash-bound Gateway targets -> explicit spot rebalance inputs.

No schedule, instrument discovery, stop policy, orders or profile activation.
Scanner capture time is not publication: availability comes from the bound
delivery pointer and must precede admission and every downstream quote.
"""
from __future__ import annotations
import argparse,csv,hashlib,io,json,re
from datetime import datetime,timezone,date
from decimal import Decimal,localcontext
from pathlib import Path
import zipfile
from dataclasses import replace
from tools import gate_btc_dynamics_spot_accounting as book
from tools.gate_btc_dynamics_spot_rebalance import rebalance

FILES=("v2a1_run_manifest.json","scanner_snapshot_status.json",
       "strategy_compositions.csv","strategy_execution_profiles.csv")
SPOT={"QOS_Base","Dynamic_Defense","Vol_Target_3"}
DERIVATIVES={"Dynamic_Hedge","Delta_LS_50_50","Delta_LS_70_30",
             "Delta_LS_50_50_StopVol","Delta_LS_70_30_StopVol"}

def parse_json(raw):
    def pairs(items):
        out={}
        for k,v in items:
            if k in out:raise ValueError("duplicate JSON field")
            out[k]=v
        return out
    return json.loads(raw,object_pairs_hook=pairs)

def table(raw,required):
    reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")),strict=True)
    fields=reader.fieldnames or []
    if len(fields)!=len(set(fields)) or not set(required)<=set(fields):raise ValueError("missing/duplicate CSV columns")
    rows=list(reader)
    if not rows or any(None in r or any(r[k] is None for k in required) for r in rows):raise ValueError("invalid CSV row")
    return rows

def admit(snapshot_raw,source_files,pointer_raw,producer_run_id,now_utc):
    snapshot=parse_json(snapshot_raw);pointer=parse_json(pointer_raw)
    if set(source_files)!=set(FILES):raise ValueError("exact four source files required")
    if snapshot.get("schema")!="gate_btc.gateway_dynamics_prospective_snapshot.v1":raise ValueError("unsupported snapshot schema")
    if snapshot.get("technical_status")!="PASS" or snapshot.get("ledger_eligible") is not True:raise ValueError("snapshot not eligible")
    for obj in [snapshot,pointer]:
        if obj.get("research_only") is not True or obj.get("operational_status")!="NOT_APPROVED" or obj.get("orders_generated")!=0 or obj.get("real_capital_used")!=0:
            raise ValueError("research boundary missing")
    if snapshot.get("shadow_only") is not True or snapshot.get("retrospective_performance_status")!="PROHIBITED_CURRENT_COMPOSITION":raise ValueError("snapshot scope invalid")
    book.check_hash(snapshot["snapshot_sha256"])
    if type(snapshot.get("sequence")) is not int or snapshot["sequence"]<1:raise ValueError("invalid source sequence")
    if pointer.get("run_id")!=producer_run_id or type(producer_run_id) is not int or producer_run_id<1:raise ValueError("producer run mismatch")
    if pointer.get("branch")!="main" or not re.fullmatch("[0-9a-f]{40}",pointer.get("head_sha","")):raise ValueError("canonical producer commit required")
    available=book.timestamp(pointer["published_at_utc"])
    created=book.timestamp(snapshot["created_at_utc"]);now=book.timestamp(now_utc)
    if not created<=available<=now:raise ValueError("invalid creation/publication/admission order")
    if date.fromisoformat(snapshot["data_as_of"])>now.date() or date.fromisoformat(pointer["data_cutoff"])>now.date():raise ValueError("future source date")
    hashes={k:hashlib.sha256(v).hexdigest() for k,v in source_files.items()}
    if hashes!=snapshot["source_artifacts"]:raise ValueError("source artifact hash mismatch")
    manifest=parse_json(source_files[FILES[0]]);status=parse_json(source_files[FILES[1]])
    if (manifest.get("version")!="QOS_V2A1_GATEWAY_SCANNER_0.10" or
        manifest.get("mode")!="public_data_no_api_key_no_orders" or
        manifest.get("technical_status")!="PASS" or
        manifest.get("operational_status")!="NOT_APPROVED" or
        manifest.get("retrospective_performance_status")!="PROHIBITED_CURRENT_COMPOSITION"):
        raise ValueError("unsupported or fixture source manifest")
    allowed={"SNAPSHOT_USABLE_RESEARCH_ONLY","SNAPSHOT_USABLE_WITH_DATA_WARNINGS"}
    if status.get("snapshot_status") not in allowed or manifest.get("snapshot_status")!=status["snapshot_status"]:
        raise ValueError("source scanner status mismatch")
    if manifest.get("data_as_of")!=snapshot["data_as_of"] or book.timestamp(manifest["run_utc"])!=created:
        raise ValueError("source clock mismatch")
    comps=table(source_files[FILES[2]],["strategy","asset","weight"])
    profiles=table(source_files[FILES[3]],["strategy","gross_long","gross_short_abs","net_exposure","gross_exposure","recommended_rebalance"])
    by_profile={}
    for row in profiles:
        if row["strategy"] in by_profile:raise ValueError("duplicate profile")
        by_profile[row["strategy"]]=row
    if set(by_profile)!=SPOT|DERIVATIVES:raise ValueError("unexpected profile cohort")
    groups={}
    for r in comps:
        name,asset=r["strategy"],r["asset"]
        if name not in by_profile or not re.fullmatch("[A-Z0-9_]{1,32}",asset):raise ValueError("unknown profile or invalid logical asset")
        g=groups.setdefault(name,{})
        if asset in g:raise ValueError("duplicate profile/asset")
        g[asset]=book.number(r["weight"])
    if set(groups)!=set(by_profile):raise ValueError("profile/composition mismatch")
    out={}
    with localcontext() as ctx:
        ctx.prec=40
        for name,weights in sorted(groups.items()):
            p=by_profile[name];long=sum((w for w in weights.values() if w>0),Decimal(0))
            short=-sum((w for w in weights.values() if w<0),Decimal(0))
            for field,actual in [("gross_long",long),("gross_short_abs",short),
                                 ("net_exposure",long-short),("gross_exposure",long+short)]:
                if abs(book.number(p[field])-actual)>Decimal("1e-10"):raise ValueError("profile totals mismatch")
            target=None;correction=None
            if name in SPOT:
                if "CASH" not in weights or any(w<0 for w in weights.values()):raise ValueError("spot profile must have explicit cash and no shorts")
                correction=1-sum(weights.values())
                if abs(correction)>Decimal("1e-12"):raise ValueError("allocation residual exceeds numeric tolerance")
                target=dict(weights);target["CASH"]+=correction
                if target["CASH"]<0:raise ValueError("negative corrected cash")
            out[name]=dict(
                target_class="SPOT_TARGET_ONLY" if target is not None else "DERIVATIVE_EXECUTION_REQUIRED",
                original_weights={k:str(v) for k,v in sorted(weights.items())},
                spot_target_weights={k:str(v) for k,v in sorted(target.items())} if target is not None else None,
                cash_numeric_correction=str(correction) if correction is not None else None,
                market_long_excluding_cash=str(long-max(weights.get("CASH",Decimal(0)),Decimal(0))),
                cash_weight=str(weights.get("CASH",Decimal(0))),market_short_abs=str(short),
                recommended_rebalance=p["recommended_rebalance"],
                executable_calendar_defined=False,instrument_identity_bound=False,
                economic_result_available=False,activation_granted=False)
    result=dict(schema="gate_btc.dynamics.bound_target_intake.v1",
        status="SOURCE_BOUND_TARGETS_NOT_EXECUTION_AUTHORIZATION",
        source_snapshot_file_sha256=hashlib.sha256(snapshot_raw).hexdigest(),
        source_snapshot_semantic_sha256=snapshot["snapshot_sha256"],
        delivery_pointer_sha256=hashlib.sha256(pointer_raw).hexdigest(),
        producer_run_id=producer_run_id,producer_code_commit=pointer["head_sha"],
        source_created_at_utc=snapshot["created_at_utc"],
        source_available_at_utc=pointer["published_at_utc"],
        scanner_data_as_of=snapshot["data_as_of"],producer_market_cutoff=pointer["data_cutoff"],
        source_sequence=snapshot["sequence"],source_hashes=hashes,profiles=out,
        research_only=True,orders=0,real_capital=0,economic_observations_created=0,
        profiles_activated=0)
    result["admission_sha256"]=book.digest(result)
    return result

def spot_weights(admission,profile):
    payload={k:v for k,v in admission.items() if k!="admission_sha256"}
    if book.digest(payload)!=admission.get("admission_sha256"):raise ValueError("target admission changed")
    item=admission["profiles"][profile]
    if item["target_class"]!="SPOT_TARGET_ONLY":raise ValueError("profile requires derivative execution")
    return dict(item["spot_target_weights"])

def rebalance_admitted(state,protocol,admission,profile,*,rebalance_id,quotes,executed_at_utc):
    """Explicit caller decision only; does not infer or schedule an action."""
    weights=spot_weights(admission,profile)
    if protocol.protocol_id!="GATE_BTC_DYNAMICS_SPOT_"+profile+"_V1":
        raise ValueError("protocol must bind the exact profile")
    signal_hash=book.digest(dict(admission_sha256=admission["admission_sha256"],profile=profile,weights=weights))
    state,receipt=rebalance(state,protocol,rebalance_id=rebalance_id,target_weights=weights,
        signal_published_at_utc=admission["source_available_at_utc"],
        signal_sha256=signal_hash,quotes=quotes,executed_at_utc=executed_at_utc)
    binding=dict(event="ADMITTED_TARGET_REBALANCE_SEAL",
        previous_chain_sha256=state.chain_sha256,
        source_admission_sha256=admission["admission_sha256"],
        source_profile=profile,rebalance_receipt=receipt,
        production_activation=False,orders=0,real_capital=0)
    chain=book.digest(binding)
    return replace(state,chain_sha256=chain,
        event_ids=state.event_ids+("BOUND_TARGET:"+rebalance_id,)),dict(binding,chain_sha256=chain)

def main():
    p=argparse.ArgumentParser();p.add_argument("--source-zip",type=Path,required=True)
    p.add_argument("--snapshot",type=Path,required=True);p.add_argument("--delivery-pointer",type=Path,required=True)
    p.add_argument("--producer-run-id",type=int,required=True);p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();raw={}
    with zipfile.ZipFile(a.source_zip) as z:
        for name in FILES:
            hits=[x for x in z.namelist() if x in {name,"outputs/"+name}]
            if len(hits)!=1:raise ValueError("missing or ambiguous ZIP member: "+name)
            raw[name]=z.read(hits[0])
    result=admit(a.snapshot.read_bytes(),raw,a.delivery_pointer.read_bytes(),a.producer_run_id,datetime.now(timezone.utc).isoformat())
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(dict(status=result["status"],spot_targets=sum(x["target_class"]=="SPOT_TARGET_ONLY" for x in result["profiles"].values()),profiles_activated=0)))

if __name__=="__main__":main()
