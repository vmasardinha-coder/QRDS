from crypto_decision_lab.scripts import phase365_data_remediation_full_integration_checkpoint_research_only as module
from tests.unit._phase356_365_fixtures import patch_roots,payload,write_json

def test_phase365_checkpoint_with_override(monkeypatch,tmp_path):
    patch_roots(monkeypatch,tmp_path,module); paths={}
    updates={355:{"closure_sealed":True},356:{"frozen_backlog_count":2},359:{"selected_decision":"ACCEPT_TIMESTAMP_CONSENSUS","selected_remediation_id":"TIMESTAMP_CONSENSUS_ALIGNMENT_REMEDIATION_V1"},360:{"active_experiment_budget":0,"preregistration_created":True,"future_experiment_budget":1},361:{"dry_run_pass":True},362:{"dry_run_pass":True},363:{"contract_frozen":True,"contract_fingerprint":"x","next_decision":"MANUAL_REAL_DATA_REMEDIATION_EXECUTION_REVIEW_ONLY_RESEARCH_ONLY"},364:{"capital_authorized_brl":0,"portal_relative_path":"artifacts/x/portal/index.html"}}
    for phase in range(355,365): paths[phase]=write_json(tmp_path/f"{phase}.json",payload(phase,**updates.get(phase,{})))
    junit=tmp_path/"junit.xml"; junit.write_text('<testsuite tests="10" failures="0" errors="0" skipped="0"/>')
    full={"passed":True,"test_file_count":594,"totals":{"tests":1501,"failures":0,"errors":0,"skipped":0},"manifest_stable":True}
    out=module.build_checkpoint(paths,targeted_junit_path=junit,artifact_path=tmp_path/"out.json",documentation_path=tmp_path/"out.md",tracking_dir=tmp_path/"tracking",full_suite_output_dir=tmp_path/"full",full_suite_override=full); assert out["contract_frozen"] is True; assert out["closed_families_reopened"] is False; assert out["global_full_suite"]["passed"] is True
