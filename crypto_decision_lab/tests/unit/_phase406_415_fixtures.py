from __future__ import annotations
import importlib,json
from pathlib import Path
LOCKS={"operational_status":"BLOCKED_RESEARCH_ONLY","action_status":"NO_ACTION_RESEARCH_ONLY","decision_layer_allowed":False,"canonical_data_writes":0,"orders_allowed":False,"capital_allowed":False,"position_size":0,"capital_used":0,"real_orders_created":0}
META={406:"phase405_global_suite_certificate_seal_research_only",407:"resumed_executed_test_attribution_audit_research_only",408:"post_suite_repository_hygiene_artifact_isolation_research_only",409:"sealed_certificate_deterministic_release_reconstruction_research_only",410:"post_global_suite_reliability_midpoint_checkpoint_research_only",411:"portal_tracking_consistency_audit_research_only",412:"rollback_documentation_recovery_evidence_validation_research_only",413:"scientific_family_explicit_approval_guard_research_only",414:"post_global_suite_unified_portal_research_only",415:"post_global_suite_integrated_tracking_checkpoint_research_only"}
INPUTS={406:[405],407:[406],408:[406,407],409:[406,407,408],410:[406,407,408,409],411:[410],412:[410,411],413:[412],414:[410,411,412,413],415:list(range(406,415))}
def w(path,obj): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8"); return path
def assert_locked(o):
    locks=o["locks"]
    for key in ("operational_status","action_status","decision_layer_allowed","canonical_data_writes","position_size","capital_used","real_orders_created"):
        assert locks[key]==LOCKS[key]
    assert o["strategy_approved"] is False
    assert o["capital_used"]==0
    assert o["real_orders_created"]==0
def seed(tmp):
    project=tmp/"crypto_decision_lab"
    portal=project/"artifacts"/"phase404_repeated_release_reliability_unified_portal_research_only"/"index.html"; portal.parent.mkdir(parents=True,exist_ok=True); portal.write_text("ok",encoding="utf-8")
    tr=project/"docs"/"reports"/"project_tracking"; tr.mkdir(parents=True,exist_ok=True)
    for name in ("QRDS_INTEGRATED_TEST_MILESTONE_396_405.md","QRDS_PROGRESS_TABLE_BY_TENS_PHASE405.md","QRDS_ROADMAP_406_415_RESEARCH_ONLY.md"): (tr/name).write_text("ok",encoding="utf-8")
    w(tr/"qrds_progress_snapshot_phase405.json",{"ok":True})
    w(project/"artifacts"/"phase405_mandatory_global_full_suite_integrated_checkpoint_research_only"/"phase405_global_suite_certificate.json",{"ok":True})
    return project
def p405():
    return {
        "phase":405,
        "gate":"P405",
        "phase_status":"READY_RESEARCH_ONLY",
        "strategy_approved":False,
        "decision_layer_allowed":False,
        "canonical_data_writes":0,
        "position_size":0,
        "capital_used":0,
        "real_orders_created":0,
        "global_full_suite_executed":True,
        "global_full_suite_pass":True,
        "global_test_files":644,
        "global_tests":1544,
        "global_failures":0,
        "global_errors":0,
        "global_manifest_stable":True,
        "global_executed_file_count":0,
        "global_reused_sha_verified_pass_file_count":644,
        "targeted_suite_pass":True,
        "targeted_test_files":38,
        "targeted_tests":75,
    }
def build_chain(tmp,through):
    project=seed(tmp); paths={405:w(project/"p405.json",p405())}; results={}
    ctx={"baseline_worktree_clean":True,"baseline_unexpected_paths":[],"artifact_outputs_gitignored":True,"explicit_scientific_family_approval":False}
    for phase in range(406,through+1):
        slug=META[phase]; mod=importlib.import_module(f"crypto_decision_lab.scripts.phase{phase}_{slug}"); out=project/"artifacts"/f"phase{phase}_{slug}"
        results[phase]=mod.build(*[paths[n] for n in INPUTS[phase]],output_dir=out,project_root=project,git_root=tmp,context=ctx)
        paths[phase]=out/f"phase{phase}_{slug}.json"
    return project,results,paths
