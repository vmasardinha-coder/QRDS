from crypto_decision_lab.scripts import phase317_prohibited_retest_signature_registry_research_only as module
from tests.unit._phase316_325_fixtures import patch_roots,payload,phase303_fixture,write_json

def test_phase317_blocks_exact_and_semantic_retests(monkeypatch,tmp_path):
    patch_roots(monkeypatch,tmp_path,module); p303=write_json(tmp_path/'p303.json',phase303_fixture()); p316=write_json(tmp_path/'p316.json',payload(316,closed_family_signature_sha256='a'*64))
    result=module.build(p303,p316,tmp_path/'artifacts/phase317'); assert result['prohibited_signature_count']==24; assert result['registry_closed'] is True; assert result['automatic_waiver_allowed'] is False; assert result['new_experiment_budget']==0
