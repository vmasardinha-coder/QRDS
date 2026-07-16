from crypto_decision_lab.scripts import phase360_finite_data_remediation_preregistration_research_only as module
from tests.unit._phase356_365_fixtures import patch_roots,payload,write_json

def test_phase360_opens_only_future_budget_one(monkeypatch,tmp_path):
    patch_roots(monkeypatch,tmp_path,module); p357=write_json(tmp_path/"357.json",payload(357)); p358=write_json(tmp_path/"358.json",payload(358)); p359=write_json(tmp_path/"359.json",payload(359,selected_remediation_id="TIMESTAMP_CONSENSUS_ALIGNMENT_REMEDIATION_V1",remediation_accepted_for_preregistration=True)); out=module.build(p357,p358,p359,tmp_path/"out"); assert out["future_experiment_budget"]==1; assert out["active_experiment_budget"]==0; assert out["strategy_or_return_metric_allowed"] is False
