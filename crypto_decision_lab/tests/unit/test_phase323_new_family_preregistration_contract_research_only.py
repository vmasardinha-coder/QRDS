from crypto_decision_lab.scripts import phase323_new_family_preregistration_contract_research_only as module
from tests.unit._phase316_325_fixtures import patch_roots,payload,write_json

def test_phase323_drafts_but_does_not_open_family(monkeypatch,tmp_path):
    patch_roots(monkeypatch,tmp_path,module); p317=write_json(tmp_path/'p317.json',payload(317,closed_family_signature_sha256='a'*64,prohibited_signature_count=24)); p322=write_json(tmp_path/'p322.json',payload(322,genuinely_different_question_justified=True,proposed_question_id='Q',proposed_scientific_question='abstain?')); result=module.build(p317,p322,tmp_path/'artifacts/phase323'); assert result['preregistration_draft_created'] is True; assert result['new_family_opened'] is False; assert result['hypotheses_registered']==0; assert result['experiment_budget_opened'] is False
