from crypto_decision_lab.scripts import phase318_failure_atlas_research_only as module
from tests.unit._phase316_325_fixtures import patch_roots,payload,write_json

def test_phase318_builds_failure_atlas_without_recycling(monkeypatch,tmp_path):
    patch_roots(monkeypatch,tmp_path,module); paths=[]
    fields={306:{'failure_reasons':['PHASE304_SELECTION_NOT_STABLE']},307:{'regime_concentration_pass':False},308:{'dependency_pass':False},309:{'extreme_cost_liquidity_pass':False},310:{'timestamp_sensitivity_pass':False},311:{}}
    for phase in range(306,312): paths.append(write_json(tmp_path/f'p{phase}.json',payload(phase,**fields[phase])))
    p316=write_json(tmp_path/'p316.json',payload(316,closed_family_signature_sha256='a'*64,failed_gate_ids=['G01']))
    result=module.build(paths,p316,tmp_path/'artifacts/phase318'); assert result['failure_record_count']>=6; assert result['failure_category_count']>=4; assert result['silent_recycling_allowed'] is False
