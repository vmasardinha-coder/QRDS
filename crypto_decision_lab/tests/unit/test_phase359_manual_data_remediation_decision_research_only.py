from crypto_decision_lab.scripts import phase359_manual_data_remediation_decision_research_only as module
from tests.unit._phase356_365_fixtures import patch_roots,payload,write_json

def test_phase359_accepts_only_feasible_question(monkeypatch,tmp_path):
    patch_roots(monkeypatch,tmp_path,module); p356=write_json(tmp_path/"356.json",payload(356)); p357=write_json(tmp_path/"357.json",payload(357,material_improvement_feasible_without_private_api=True)); p358=write_json(tmp_path/"358.json",payload(358,material_improvement_feasible_with_existing_data=True)); out=module.build(p356,p357,p358,"ACCEPT_TIMESTAMP_CONSENSUS","Victor Sardinha",tmp_path/"out"); assert out["remediation_accepted_for_preregistration"] is True; assert out["new_family_opened"] is False
