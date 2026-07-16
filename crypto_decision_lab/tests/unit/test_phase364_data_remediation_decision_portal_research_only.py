from crypto_decision_lab.scripts import phase364_data_remediation_decision_portal_research_only as module
from tests.unit._phase356_365_fixtures import patch_roots,payload,write_json

def test_phase364_updates_current_portal(monkeypatch,tmp_path):
    patch_roots(monkeypatch,tmp_path,module); project=tmp_path/"crypto_decision_lab"; (tmp_path/"ABRIR_QRDS.ps1").write_text("x"); paths=[]
    values=[payload(355),payload(357,material_improvement_feasible_without_private_api=True),payload(358,material_improvement_feasible_with_existing_data=True),payload(359,selected_remediation_id="TIMESTAMP_CONSENSUS_ALIGNMENT_REMEDIATION_V1",selected_decision="ACCEPT_TIMESTAMP_CONSENSUS",remediation_accepted_for_preregistration=True),payload(360,future_experiment_budget=1),payload(363,contract_frozen=True,next_decision="MANUAL_REAL_DATA_REMEDIATION_EXECUTION_REVIEW_ONLY_RESEARCH_ONLY")]
    for phase,value in zip((355,357,358,359,360,363),values): paths.append(write_json(tmp_path/f"{phase}.json",value))
    output=project/"artifacts/phase364"; out=module.build(*paths,output,project_root=project,git_root=tmp_path); text=(output/"portal/index.html").read_text(); assert out["capital_authorized_brl"]==0; assert "VOCE ESTA AQUI" in text; assert (project/"artifacts/project_portal_registry/current_portal.json").is_file()
