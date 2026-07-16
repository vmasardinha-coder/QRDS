from crypto_decision_lab.scripts import phase363_future_real_data_remediation_contract_freeze_research_only as module
from tests.unit._phase356_365_fixtures import patch_roots,payload,write_json

def test_phase363_freezes_without_starting(monkeypatch,tmp_path):
    patch_roots(monkeypatch,tmp_path,module); p359=write_json(tmp_path/"359.json",payload(359,remediation_accepted_for_preregistration=True,selected_remediation_id="TIMESTAMP_CONSENSUS_ALIGNMENT_REMEDIATION_V1")); p360=write_json(tmp_path/"360.json",payload(360,preregistration_fingerprint="x",future_experiment_budget=1,success_criteria={},primary_metrics=[])); p361=write_json(tmp_path/"361.json",payload(361,dry_run_pass=True)); p362=write_json(tmp_path/"362.json",payload(362,dry_run_pass=True)); out=module.build(p359,p360,p361,p362,tmp_path/"out"); assert out["contract_frozen"] is True; assert out["real_data_remediation_evaluation_started"] is False; assert out["public_collection_authorized"] is False
