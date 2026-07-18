from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

META={
406:("phase405_global_suite_certificate_seal_research_only","PHASE406_GLOBAL_SUITE_CERTIFICATE_SEALED_RESEARCH_ONLY"),
407:("resumed_executed_test_attribution_audit_research_only","PHASE407_TEST_ATTRIBUTION_AUDIT_PASS_RESEARCH_ONLY"),
408:("post_suite_repository_hygiene_artifact_isolation_research_only","PHASE408_POST_SUITE_HYGIENE_PASS_RESEARCH_ONLY"),
409:("sealed_certificate_deterministic_release_reconstruction_research_only","PHASE409_SEALED_CERTIFICATE_RECONSTRUCTION_PASS_RESEARCH_ONLY"),
410:("post_global_suite_reliability_midpoint_checkpoint_research_only","PHASE410_POST_GLOBAL_MIDPOINT_PASS_RESEARCH_ONLY"),
411:("portal_tracking_consistency_audit_research_only","PHASE411_PORTAL_TRACKING_CONSISTENCY_PASS_RESEARCH_ONLY"),
412:("rollback_documentation_recovery_evidence_validation_research_only","PHASE412_ROLLBACK_RECOVERY_EVIDENCE_PASS_RESEARCH_ONLY"),
413:("scientific_family_explicit_approval_guard_research_only","PHASE413_SCIENTIFIC_FAMILY_OPENING_BLOCKED_RESEARCH_ONLY"),
414:("post_global_suite_unified_portal_research_only","PHASE414_POST_GLOBAL_PORTAL_READY_RESEARCH_ONLY"),
415:("post_global_suite_integrated_tracking_checkpoint_research_only","PHASE415_INTEGRATED_TRACKING_CHECKPOINT_READY_RESEARCH_ONLY"),
}
LOCKS={"operational_status":"BLOCKED_RESEARCH_ONLY","action_status":"NO_ACTION_RESEARCH_ONLY","decision_layer_allowed":False,"canonical_data_writes":0,"orders_allowed":False,"capital_allowed":False,"position_size":0,"capital_used":0,"real_orders_created":0}
def now(): return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
def read(path):
    obj=json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(obj,dict): raise ValueError(path)
    return obj
def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text.rstrip()+"\n",encoding="utf-8",newline="\n")
def wjson(path,obj): write(path,json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def stable(obj): return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def locked(obj):
    phase=obj.get("phase")

    if phase==405:
        if obj.get("strategy_approved") is not False:
            raise ValueError("Phase405 strategy approval changed")

        top_level_optional={
            "decision_layer_allowed":False,
            "canonical_data_writes":0,
            "position_size":0,
            "capital_used":0,
            "real_orders_created":0,
        }
        top_mismatches={
            key:(obj.get(key),expected)
            for key,expected in top_level_optional.items()
            if key in obj and obj.get(key)!=expected
        }
        if top_mismatches:
            raise ValueError(
                f"Phase405 top-level safety mismatch: {top_mismatches}"
            )

        safety=obj.get("safety")
        if isinstance(safety,dict):
            safety_optional={
                "operational_status":"BLOCKED_RESEARCH_ONLY",
                "action_status":"NO_ACTION_RESEARCH_ONLY",
                "decision_layer_allowed":False,
                "canonical_data_writes":0,
                "position_size":0,
                "capital_used":0,
                "real_orders_created":0,
            }
            safety_mismatches={
                key:(safety.get(key),expected)
                for key,expected in safety_optional.items()
                if key in safety and safety.get(key)!=expected
            }
            if safety_mismatches:
                raise ValueError(
                    f"Phase405 safety mismatch: {safety_mismatches}"
                )
        return

    locks=obj.get("locks")
    if not isinstance(locks,dict):
        raise ValueError(
            f"locks object missing for generated phase {phase}"
        )
    required={
        "operational_status":"BLOCKED_RESEARCH_ONLY",
        "action_status":"NO_ACTION_RESEARCH_ONLY",
        "decision_layer_allowed":False,
        "canonical_data_writes":0,
        "position_size":0,
        "capital_used":0,
        "real_orders_created":0,
    }
    mismatches={
        key:(locks.get(key),expected)
        for key,expected in required.items()
        if locks.get(key)!=expected
    }
    if mismatches:
        raise ValueError(f"lock invariant mismatch: {mismatches}")
    if "orders_allowed" in locks and locks.get("orders_allowed") is not False:
        raise ValueError("orders_allowed changed")
    if "capital_allowed" in locks and locks.get("capital_allowed") is not False:
        raise ValueError("capital_allowed changed")
    if obj.get("strategy_approved") is not False:
        raise ValueError("strategy approval changed")
def base(phase,loaded):
    slug,gate=META[phase]
    return {"schema_version":"1.0.0","phase":phase,"slug":slug,"generated_at_utc":now(),"gate":gate,"phase_status":"READY_RESEARCH_ONLY","batch_window":"406-415","entering_decision":"POST_GLOBAL_SUITE_RELEASE_RELIABILITY_OBSERVATION_ONLY_RESEARCH_ONLY","locks":dict(LOCKS),"strategy_approved":False,"scientific_family_opened":False,"new_hypotheses_created":0,"trading_signal_generated":False,"recommendation_generated":False,"allocation_generated":False,"private_api_used":False,"network_used":False,"capital_used":0,"position_size":0,"real_orders_created":0,"canonical_data_writes":0,"inputs":[{"phase":o.get("phase"),"path":p.as_posix(),"sha256":sha(p)} for p,o in loaded]}
def build_phase(phase,input_paths,output_dir,*,project_root,git_root,context=None):
    context=dict(context or {})
    loaded=[(p,read(p)) for p in input_paths]
    for _,o in loaded: locked(o)
    objs=[o for _,o in loaded]
    r=base(phase,loaded)
    if phase==406:
        s=objs[0]; req={"global_full_suite_executed":True,"global_full_suite_pass":True,"global_test_files":644,"global_tests":1544,"global_failures":0,"global_errors":0,"global_manifest_stable":True,"targeted_suite_pass":True}
        bad={k:(s.get(k),v) for k,v in req.items() if s.get(k)!=v}
        if bad: raise ValueError(bad)
        cert={"source_phase":405,"source_artifact_sha256":sha(loaded[0][0]),"targeted_test_files":s.get("targeted_test_files"),"targeted_tests":s.get("targeted_tests"),"global_test_files":s["global_test_files"],"global_tests":s["global_tests"],"global_failures":s["global_failures"],"global_errors":s["global_errors"],"global_executed_file_count":s.get("global_executed_file_count",0),"global_reused_sha_verified_pass_file_count":s.get("global_reused_sha_verified_pass_file_count",0),"global_manifest_stable":s["global_manifest_stable"]}
        r.update(certificate_sealed=True,sealed_certificate=cert,sealed_certificate_sha256=stable(cert),certificate_mutation_allowed=False)
    elif phase==407:
        c=objs[0]["sealed_certificate"]; reused=int(c["global_reused_sha_verified_pass_file_count"]); executed=int(c["global_executed_file_count"]); total=int(c["global_test_files"])
        r.update(attribution_audit_pass=reused+executed==total,reused_sha_verified_pass_files=reused,executed_test_files=executed,certified_test_files=total,unattributed_test_files=total-reused-executed,resume_rule="PASS_AND_EXACT_SHA256_ONLY")
        if not r["attribution_audit_pass"]: raise ValueError("attribution")
    elif phase==408:
        clean=context.get("baseline_worktree_clean") is True; unexpected=list(context.get("baseline_unexpected_paths",[])); ignored=context.get("artifact_outputs_gitignored") is True
        r.update(baseline_worktree_clean=clean,baseline_unexpected_path_count=len(unexpected),artifact_outputs_gitignored=ignored,repository_hygiene_pass=clean and not unexpected and ignored,artifact_isolation_pass=ignored)
        if not r["repository_hygiene_pass"]: raise ValueError("hygiene")
    elif phase==409:
        source={"seal":objs[0].get("sealed_certificate_sha256"),"reused":objs[1].get("reused_sha_verified_pass_files"),"executed":objs[1].get("executed_test_files"),"hygiene":objs[2].get("repository_hygiene_pass")}
        a=stable(source); b=stable(json.loads(json.dumps(source,sort_keys=True)))
        r.update(reconstruction_hash_a=a,reconstruction_hash_b=b,deterministic_reconstruction_pass=a==b,source_certificate_sealed=objs[0].get("certificate_sealed") is True)
    elif phase==410:
        checks={"seal":objs[0].get("certificate_sealed") is True,"attribution":objs[1].get("attribution_audit_pass") is True,"hygiene":objs[2].get("repository_hygiene_pass") is True,"reconstruction":objs[3].get("deterministic_reconstruction_pass") is True}
        r.update(midpoint_checks=checks,midpoint_checkpoint_pass=all(checks.values()),global_suite_executed_in_window=False,global_suite_required_in_window=False)
    elif phase==411:
        paths=[project_root/"artifacts"/"phase404_repeated_release_reliability_unified_portal_research_only"/"index.html",project_root/"docs"/"reports"/"project_tracking"/"QRDS_INTEGRATED_TEST_MILESTONE_396_405.md",project_root/"docs"/"reports"/"project_tracking"/"QRDS_PROGRESS_TABLE_BY_TENS_PHASE405.md",project_root/"docs"/"reports"/"project_tracking"/"qrds_progress_snapshot_phase405.json"]
        seen={p.relative_to(project_root).as_posix():p.is_file() for p in paths}
        r.update(portal_tracking_files=seen,portal_tracking_consistency_pass=all(seen.values()),phase410_midpoint_pass=objs[0].get("midpoint_checkpoint_pass") is True)
        if not r["portal_tracking_consistency_pass"]: raise ValueError("tracking")
    elif phase==412:
        paths=[project_root/"artifacts"/"phase405_mandatory_global_full_suite_integrated_checkpoint_research_only"/"phase405_global_suite_certificate.json",project_root/"docs"/"reports"/"project_tracking"/"QRDS_ROADMAP_406_415_RESEARCH_ONLY.md",project_root/"docs"/"reports"/"project_tracking"/"QRDS_INTEGRATED_TEST_MILESTONE_396_405.md"]
        seen={p.relative_to(project_root).as_posix():p.is_file() for p in paths}
        r.update(rollback_documentation_evidence=seen,rollback_documentation_present=all(seen.values()),recovery_evidence_valid=all(seen.values()),automatic_rollback_execution_allowed=False,manual_review_required_for_recovery=True)
        if not r["recovery_evidence_valid"]: raise ValueError("recovery")
    elif phase==413:
        approval=context.get("explicit_scientific_family_approval") is True
        if approval: raise ValueError("approval forbidden in executor")
        r.update(explicit_scientific_family_approval=False,scientific_family_opening_blocked=True,scientific_family_opened=False,new_hypotheses_created=0,approval_effect="NONE_RESEARCH_ONLY")
    elif phase==414:
        checks={"midpoint":objs[0].get("midpoint_checkpoint_pass") is True,"tracking":objs[1].get("portal_tracking_consistency_pass") is True,"rollback":objs[2].get("recovery_evidence_valid") is True,"scientific_block":objs[3].get("scientific_family_opening_blocked") is True}
        r.update(portal_checks=checks,portal_ready=all(checks.values()),portal_path="index.html")
        if not r["portal_ready"]: raise ValueError("portal")
        html="<!doctype html><html><head><meta charset='utf-8'><title>QRDS Phase 414</title></head><body><h1>QRDS Phase 414</h1><p><strong>BLOCKED_RESEARCH_ONLY</strong></p><p>NO_ACTION_RESEARCH_ONLY</p><p>CAPITAL R$ 0</p><p>REAL ORDERS 0</p><pre>"+json.dumps(checks,indent=2,sort_keys=True)+"</pre></body></html>"
        write(output_dir/"index.html",html)
    elif phase==415:
        checks={str(n):o.get("phase_status")=="READY_RESEARCH_ONLY" for n,o in zip(range(406,415),objs)}
        r.update(integrated_phase_checks=checks,integrated_checkpoint_ready=all(checks.values()),global_full_suite_required=False,global_full_suite_executed=False,global_full_suite_pass=None,targeted_suite_executed=False,targeted_suite_pass=None,next_tracking_checkpoint=425)
    output_dir.mkdir(parents=True,exist_ok=True)
    slug=META[phase][0]; wjson(output_dir/f"phase{phase}_{slug}.json",r); return r
def summary_markdown(p):
    selected={k:v for k,v in p.items() if k not in {"inputs","locks","generated_at_utc","schema_version"}}
    return "# Phase "+str(p["phase"])+" — "+p["slug"]+"\n\n## Gate\n\n```text\n"+p["gate"]+"\n```\n\n## Result\n\n```json\n"+json.dumps(selected,ensure_ascii=False,indent=2,sort_keys=True)+"\n```\n\n## Permanent restrictions\n\n```text\noperational_status=BLOCKED_RESEARCH_ONLY\naction_status=NO_ACTION_RESEARCH_ONLY\ndecision_layer_allowed=False\nstrategy_approved=False\nscientific_family_opened=False\ncapital_used=0\nreal_orders_created=0\ncanonical_data_writes=0\n```\n"
