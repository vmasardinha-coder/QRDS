from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys, time, xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase356_365_data_remediation_common import BASELINE_PHASE355_HEAD, LOCKS, ROOT, base_payload, fingerprint, parse_junit, read_json, sha256_file, utc_now_iso, validate_phase, write_json, write_summary, write_text

MIN_TEST_FILES=594
MIN_TESTS=1501

def _rel(path:Path)->str:
    try:return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:return str(path.resolve())

def _test_manifest()->list[dict[str,Any]]:
    return [{"path":_rel(p),"size_bytes":p.stat().st_size,"sha256":sha256_file(p)} for p in sorted((ROOT/"tests").rglob("test_*.py")) if p.is_file()]

def _assign_shards(records:list[dict[str,Any]],count:int=3)->list[list[dict[str,Any]]]:
    shards=[[] for _ in range(count)]; totals=[0]*count
    for r in sorted(records,key=lambda x:(-int(x["size_bytes"]),x["path"])):
        i=min(range(count),key=lambda x:(totals[x],x)); shards[i].append(r); totals[i]+=int(r["size_bytes"])
    for s in shards:s.sort(key=lambda x:x["path"])
    return shards

def _parse_junit(path:Path)->dict[str,int]:
    totals={"tests":0,"failures":0,"errors":0,"skipped":0}; root=ET.parse(path).getroot(); suites=[root] if root.tag=="testsuite" else list(root.findall("testsuite"))
    for suite in suites:
        for key in totals: totals[key]+=int(float(suite.attrib.get(key,"0") or "0"))
    return totals

def _git_status_paths()->dict[str,str]:
    r=subprocess.run(["git","status","--porcelain=v1","-z","--untracked-files=all"],cwd=ROOT,capture_output=True,check=False)
    if r.returncode!=0: raise RuntimeError(r.stderr.decode("utf-8",errors="replace"))
    parts=[x for x in r.stdout.split(b"\0") if x]; out={}; i=0
    while i<len(parts):
        raw=parts[i].decode("utf-8",errors="surrogateescape"); status=raw[:2]; path=raw[3:].replace("\\","/")
        if path.startswith("crypto_decision_lab/"): path=path[len("crypto_decision_lab/"):]
        if status and status[0] in {"R","C"} and i+1<len(parts):
            i+=1; path=parts[i].decode("utf-8",errors="surrogateescape").replace("\\","/")
            if path.startswith("crypto_decision_lab/"): path=path[len("crypto_decision_lab/"):]
        out[path]=status; i+=1
    return out

def _cleanup_test_side_effects(before:dict[str,str],protected_roots:tuple[str,...]=())->dict[str,Any]:
    after=_git_status_paths(); new=sorted(set(after)-set(before)); restored=[]; removed=[]; refused=[]
    known_prefixes=("artifacts/","docs/reports/")
    for relative in new:
        if any(relative==r.rstrip("/") or relative.startswith(r.rstrip("/")+"/") for r in protected_roots): continue
        status=after[relative]; candidate=(ROOT/relative).resolve()
        try:candidate.relative_to(ROOT.resolve())
        except ValueError: refused.append(relative); continue
        if status=="??":
            if not relative.startswith(known_prefixes): refused.append(relative); continue
            if candidate.is_file() or candidate.is_symlink(): candidate.unlink(); removed.append(relative)
            elif candidate.is_dir(): shutil.rmtree(candidate); removed.append(relative)
            continue
        r=subprocess.run(["git","checkout","--",relative],cwd=ROOT,capture_output=True,text=True,check=False)
        (restored if r.returncode==0 else refused).append(relative)
    if refused: raise RuntimeError("Global-suite generated unexpected paths: "+", ".join(refused))
    return {"restored_tracked_paths":restored,"removed_generated_untracked_paths":removed,"refused_paths":refused}

def _safe_name(relative:str)->str:return f"{Path(relative).stem[:80]}_{hashlib.sha256(relative.encode()).hexdigest()[:12]}"

def run_resumable_full_suite(output_dir:Path,*,per_file_timeout_seconds:int=1800)->dict[str,Any]:
    output_dir.mkdir(parents=True,exist_ok=True); junit_dir=output_dir/"junit"; log_dir=output_dir/"logs"; junit_dir.mkdir(exist_ok=True); log_dir.mkdir(exist_ok=True); progress=output_dir/"phase365_full_suite_progress.json"
    before=_test_manifest()
    if len(before)<MIN_TEST_FILES: raise RuntimeError(f"Test inventory regression: expected at least {MIN_TEST_FILES}, found {len(before)}.")
    mf=hashlib.sha256(json.dumps(before,sort_keys=True,separators=(",",":")).encode()).hexdigest(); shards=_assign_shards(before); shard_by={r["path"]:i for i,s in enumerate(shards,1) for r in s}
    existing={}
    if progress.is_file():
        try:
            loaded=read_json(progress)
            if loaded.get("manifest_fingerprint")==mf: existing=dict(loaded.get("results",{}))
        except Exception: existing={}
    baseline=_git_status_paths(); protected=_rel(output_dir).rstrip("/")+"/"; results={}; reused=executed=0; started=time.monotonic()
    for pos,record in enumerate(before,1):
        rel=record["path"]; cached=existing.get(rel)
        if isinstance(cached,dict) and cached.get("sha256")==record["sha256"] and cached.get("status")=="PASS" and int(cached.get("returncode",1))==0 and not bool(cached.get("timed_out",False)) and Path(str(cached.get("junit_path",""))).is_file():
            try: totals=_parse_junit(Path(cached["junit_path"]))
            except Exception: totals=None
            if totals and totals["failures"]==0 and totals["errors"]==0:
                item=dict(cached); item["reused"]=True; item["junit"]=totals; results[rel]=item; reused+=1; print(f"[{pos}/{len(before)}] REUSE PASS {rel}",flush=True); continue
        name=_safe_name(rel); jp=junit_dir/f"{name}.xml"; lp=log_dir/f"{name}.log"; cmd=[sys.executable,"-m","pytest","-q","--tb=short",f"--junitxml={jp}",str(ROOT/rel)]
        print(f"[{pos}/{len(before)}] RUN shard {shard_by[rel]} {rel}",flush=True); start=time.monotonic(); timed=False
        try:
            c=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=per_file_timeout_seconds,check=False,env={**os.environ,"PYTHONPATH":str(ROOT/"src")}); rc=c.returncode; out=c.stdout; err=c.stderr
        except subprocess.TimeoutExpired as e:
            timed=True; rc=124; out=e.stdout or ""; err=e.stderr or ""; out=out.decode("utf-8",errors="replace") if isinstance(out,bytes) else out; err=err.decode("utf-8",errors="replace") if isinstance(err,bytes) else err
        duration=time.monotonic()-start; lp.write_text(f"COMMAND: {' '.join(cmd)}\nRETURN_CODE: {rc}\nTIMED_OUT: {timed}\nDURATION_SECONDS: {duration:.3f}\n\nSTDOUT\n{out}\n\nSTDERR\n{err}\n",encoding="utf-8")
        totals=_parse_junit(jp) if jp.is_file() else {"tests":0,"failures":0,"errors":1,"skipped":0}; passed=rc==0 and not timed and totals["failures"]==0 and totals["errors"]==0
        item={"path":rel,"sha256":record["sha256"],"shard":shard_by[rel],"status":"PASS" if passed else "FAIL","returncode":rc,"timed_out":timed,"duration_seconds":duration,"junit_path":str(jp),"log_path":str(lp),"junit":totals,"reused":False}; results[rel]=item; executed+=1
        write_json(progress,{"phase":365,"manifest_fingerprint":mf,"updated_at_utc":utc_now_iso(),"test_file_count":len(before),"results":results})
        if not passed:
            cleanup=_cleanup_test_side_effects(baseline,(protected,)); raise RuntimeError(f"Global-suite failure in {rel}. TEST_OR_FIXTURE_FAILURE, not scientific failure. returncode={rc}, timed_out={timed}, junit={totals}, log={lp}, cleanup={cleanup}")
    cleanup=_cleanup_test_side_effects(baseline,(protected,)); after=_test_manifest(); stable=before==after; totals={"tests":0,"failures":0,"errors":0,"skipped":0}
    for item in results.values():
        for key in totals: totals[key]+=int(item["junit"][key])
    passed=len(results)==len(before) and all(x["status"]=="PASS" for x in results.values()) and totals["failures"]==0 and totals["errors"]==0 and totals["tests"]>=MIN_TESTS and stable
    return {"mode":"RESUMABLE_FILEWISE_THREE_SHARD_MANIFEST","duration_seconds":time.monotonic()-started,"per_file_timeout_seconds":per_file_timeout_seconds,"test_file_count":len(before),"minimum_test_file_count":MIN_TEST_FILES,"minimum_tests":MIN_TESTS,"manifest_fingerprint":mf,"manifest_before":before,"manifest_after":after,"manifest_stable":stable,"shard_count":3,"shards":[{"shard":i,"file_count":len(s),"total_bytes":sum(int(r["size_bytes"]) for r in s),"files":[r["path"] for r in s]} for i,s in enumerate(shards,1)],"reused_file_count":reused,"executed_file_count":executed,"all_files_completed":len(results)==len(before),"totals":totals,"cleanup":cleanup,"passed":passed}

def _write_tracking(payload:dict[str,Any],tracking_dir:Path)->None:
    full=payload["global_full_suite"]; decision=payload["next_window_decision"]
    master=f"""# QRDS Master Progress by Tens — Phase 365

## Current decision

`{decision}`

## Window 356–365

- Remediation questions frozen: `2`
- Manual decision: `{payload['manual_decision']}`
- Selected remediation: `{payload.get('selected_remediation_id') or 'NONE'}`
- Contract frozen: `{payload['contract_frozen']}`
- Real-data remediation evaluation started: `False`
- Strategy approved: `False`
- Capital used: `R$ 0`

## Mandatory global suite

- Test files: `{full['test_file_count']}`
- Tests: `{full['totals']['tests']}`
- Failures: `{full['totals']['failures']}`
- Errors: `{full['totals']['errors']}`
- Manifest stable: `{full['manifest_stable']}`
"""
    mermaid=f"""# QRDS Architecture Mermaid — Phase 365

```mermaid
flowchart TD
 A[Two closed scientific families] --> B[Two data-remediation questions frozen]
 B --> C[Public coverage feasibility]
 B --> D[Timestamp and consensus feasibility]
 C --> E[Manual decision]
 D --> E
 E --> F[One finite preregistration or no-go]
 F --> G[Synthetic and fixture dry-runs]
 G --> H[Future real-data contract frozen]
 H --> I[Unified portal updated]
 I --> J[Mandatory global suite]
 J --> K[NO_ACTION_RESEARCH_ONLY]
```

**VOCE ESTA AQUI:** `{decision}`. Capital authorized: `R$ 0`.
"""
    table=f"""# QRDS Progress Table by Tens — Phase 365

| Range | Dominant delivery | State |
|---|---|---|
| 0–345 | Foundation and two finite scientific families | Complete; no survivor |
| 346–355 | Negative-evidence closure and unified navigation | Complete |
| **356–365** | **Finite data-remediation governance, dry-runs, portal and mandatory global suite** | **PASS; {decision}** |
| 366–375 | One frozen remediation execution review or preserved no-go | Planned, research-only |

Operational: `BLOCKED_RESEARCH_ONLY`. Capital: `R$ 0`.
"""
    milestone=f"""# QRDS Integrated Test Milestone 356–365

- Phases completed: `356–365`
- Targeted tests: `{payload['targeted_tests']['tests']}`
- Global test files: `{full['test_file_count']}`
- Global tests: `{full['totals']['tests']}`
- Failures: `{full['totals']['failures']}`
- Errors: `{full['totals']['errors']}`
- Manifest stable: `{full['manifest_stable']}`
- Contract frozen: `{payload['contract_frozen']}`
- Strategy approved: `False`
- Capital used: `R$ 0`
"""
    if payload["contract_frozen"]:
        roadmap_body="""- **366:** manual review of the exact frozen remediation contract.
- **367:** execute one declared real-data remediation evaluation only after explicit approval; use existing data if possible.
- **368:** compare raw versus remediated data-quality metrics only.
- **369:** prove that no closed-family performance metric was used.
- **370:** decide whether one declared public re-collection is needed; no silent network action.
- **371–373:** lineage, hashes, reproducibility and stop-rule audit.
- **374:** update the unified portal with the data-quality result.
- **375:** integrated checkpoint; no strategy promotion."""
    else:
        roadmap_body="""- **366–369:** preserve the data-remediation no-go and audit whether any genuinely new question exists.
- **370–373:** no experiment unless a new manual review passes all governance gates.
- **374:** update the unified portal.
- **375:** integrated checkpoint retaining zero active budget."""
    roadmap=f"""# QRDS Roadmap 366–375 — Research Only

## Entering decision

`{decision}`

## Recommended sequence

{roadmap_body}

## Permanent prohibition

Data remediation cannot rescue closed families, create a signal, authorize allocation, connect a private account, place orders or use capital.
"""
    snapshot={"project":"QRDS/QOS/GATE BTC","baseline_phase":365,"baseline_phase355_head":BASELINE_PHASE355_HEAD,"readiness":{"framework":100,"evidence":0,"operational":0},"data_remediation":{"manual_decision":payload["manual_decision"],"selected_remediation_id":payload.get("selected_remediation_id"),"contract_frozen":payload["contract_frozen"],"real_data_evaluation_started":False},"global_full_suite":{"passed":full["passed"],"test_files":full["test_file_count"],"tests":full["totals"]["tests"],"failures":full["totals"]["failures"],"errors":full["totals"]["errors"],"manifest_stable":full["manifest_stable"]},"safety":dict(LOCKS),"next_tracking_checkpoint":375,"next_mandatory_global_full_suite":385,"roadmap_window":"366-375"}
    tracking_dir.mkdir(parents=True,exist_ok=True); write_text(tracking_dir/"QRDS_MASTER_PROGRESS_BY_TENS_PHASE365.md",master); write_text(tracking_dir/"QRDS_ARCHITECTURE_MERMAID_PHASE365.md",mermaid); write_text(tracking_dir/"QRDS_PROGRESS_TABLE_BY_TENS_PHASE365.md",table); write_text(tracking_dir/"QRDS_INTEGRATED_TEST_MILESTONE_356_365.md",milestone); write_text(tracking_dir/"QRDS_ROADMAP_366_375_RESEARCH_ONLY.md",roadmap); write_json(tracking_dir/"qrds_progress_snapshot_phase365.json",snapshot)

def build_checkpoint(paths:dict[int,Path],*,targeted_junit_path:Path,artifact_path:Path,documentation_path:Path,tracking_dir:Path,full_suite_output_dir:Path,per_file_timeout_seconds:int=1800,full_suite_override:dict[str,Any]|None=None)->dict[str,Any]:
    items={p:read_json(path) for p,path in paths.items()}
    for p,item in items.items(): validate_phase(item,p)
    if items[355].get("closure_sealed") is not True: raise RuntimeError("Phase 355 closure is not sealed.")
    if int(items[356].get("frozen_backlog_count",0))!=2: raise RuntimeError("Phase 356 backlog mismatch.")
    if items[360].get("active_experiment_budget")!=0: raise RuntimeError("Phase 360 opened an active experiment budget.")
    if items[361].get("dry_run_pass") is not True or items[362].get("dry_run_pass") is not True: raise RuntimeError("Dry-run failure.")
    if items[364].get("capital_authorized_brl")!=0: raise RuntimeError("Portal authorized capital.")
    targeted=parse_junit(targeted_junit_path)
    if not targeted["passed"]: raise RuntimeError(f"Targeted tests failed: {targeted}")
    full=full_suite_override or run_resumable_full_suite(full_suite_output_dir,per_file_timeout_seconds=per_file_timeout_seconds)
    if not full.get("passed"): raise RuntimeError(f"Mandatory global full-suite failed: {full}")
    frozen=bool(items[363].get("contract_frozen")); decision=items[363].get("next_decision")
    payload=base_payload(365,"DATA_REMEDIATION_FULL_INTEGRATION_CHECKPOINT_PASS_RESEARCH_ONLY")
    payload.update({"gate":"PHASE365_DATA_REMEDIATION_FULL_INTEGRATION_CHECKPOINT_READY_RESEARCH_ONLY","batch_gate":"PHASE356_365_DATA_REMEDIATION_CHECKPOINT_PASS_RESEARCH_ONLY","baseline_phase355_head":BASELINE_PHASE355_HEAD,"phase_chain":{str(p):{"gate":items[p].get("gate"),"artifact_fingerprint":items[p].get("artifact_fingerprint")} for p in range(356,365)},"manual_decision":items[359].get("selected_decision"),"selected_remediation_id":items[359].get("selected_remediation_id"),"preregistration_created":items[360].get("preregistration_created"),"future_experiment_budget":items[360].get("future_experiment_budget"),"active_experiment_budget":0,"synthetic_dry_run_pass":items[361].get("dry_run_pass"),"fixture_dry_run_pass":items[362].get("dry_run_pass"),"contract_frozen":frozen,"contract_fingerprint":items[363].get("contract_fingerprint"),"real_data_remediation_evaluation_started":False,"public_collection_started":False,"closed_families_reopened":False,"new_family_opened":False,"active_hypotheses":0,"targeted_tests":targeted,"global_full_suite":full,"current_portal_relative_path":items[364].get("portal_relative_path"),"next_window_decision":decision,"next_tracking_checkpoint":375,"next_mandatory_global_full_suite":385,"candidate_freeze_created":False,"forward_evidence_clock_started":False,"forward_evidence_credit":0})
    payload["artifact_fingerprint"]=fingerprint(payload); artifact_path.parent.mkdir(parents=True,exist_ok=True); write_json(artifact_path,payload)
    write_summary(documentation_path,title="Phase 365 — Data-remediation Full Integration Checkpoint",gate=payload["gate"],bullets=[f"Global test files: `{full['test_file_count']}`",f"Global tests: `{full['totals']['tests']}`",f"Contract frozen: `{frozen}`","Real-data remediation evaluation started: `False`","Closed families reopened: `False`","Capital used: `R$ 0`"])
    _write_tracking(payload,tracking_dir); return payload

def main()->int:
    a=argparse.ArgumentParser(); art=ROOT/"artifacts"; defs={355:"negative_evidence_navigation_checkpoint",356:"manual_data_remediation_backlog_freeze",357:"public_derivatives_coverage_feasibility",358:"timestamp_consensus_alignment_feasibility",359:"manual_data_remediation_decision",360:"finite_data_remediation_preregistration",361:"synthetic_data_remediation_contract_dry_run",362:"fixture_data_remediation_pipeline_dry_run",363:"future_real_data_remediation_contract_freeze",364:"data_remediation_decision_portal"}
    for p,slug in defs.items(): a.add_argument(f"--phase{p}-artifact",type=Path,default=art/f"phase{p}_{slug}_research_only"/f"phase{p}_{slug}.json")
    a.add_argument("--targeted-junit",type=Path,required=True); a.add_argument("--artifact",type=Path,default=art/"phase365_data_remediation_full_integration_checkpoint_research_only/phase365_data_remediation_full_integration_checkpoint.json"); a.add_argument("--documentation",type=Path,default=ROOT/"docs/reports/integration/phase365_data_remediation_full_integration_checkpoint_summary.md"); a.add_argument("--tracking-dir",type=Path,default=ROOT/"docs/reports/project_tracking"); a.add_argument("--full-suite-output-dir",type=Path,default=art/"phase365_data_remediation_full_integration_checkpoint_research_only/full_suite"); a.add_argument("--per-file-timeout-seconds",type=int,default=1800)
    x=a.parse_args(); paths={p:getattr(x,f"phase{p}_artifact") for p in range(355,365)}; payload=build_checkpoint(paths,targeted_junit_path=x.targeted_junit,artifact_path=x.artifact,documentation_path=x.documentation,tracking_dir=x.tracking_dir,full_suite_output_dir=x.full_suite_output_dir,per_file_timeout_seconds=x.per_file_timeout_seconds); full=payload["global_full_suite"]
    print(payload["gate"]); print("Global full-suite: PASS"); print("Test files:",full["test_file_count"]); print("Tests:",full["totals"]["tests"]); print("Failures:",full["totals"]["failures"]); print("Errors:",full["totals"]["errors"]); print("Manifest stable:",full["manifest_stable"]); print("Contract frozen:",payload["contract_frozen"]); print("Next-window decision:",payload["next_window_decision"]); return 0
if __name__=="__main__": raise SystemExit(main())
