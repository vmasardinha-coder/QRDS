from crypto_decision_lab.scripts import phase316_negative_evidence_registry_research_only as module
from tests.unit._phase316_325_fixtures import patch_roots, phase303_fixture, phase304_fixture, phase311_fixture, phase315_fixture, write_json

def test_phase316_registers_closed_negative_family(monkeypatch,tmp_path):
    patch_roots(monkeypatch,tmp_path,module); p303=write_json(tmp_path/'p303.json',phase303_fixture()); p304=write_json(tmp_path/'p304.json',phase304_fixture()); p311=write_json(tmp_path/'p311.json',phase311_fixture()); p315=write_json(tmp_path/'p315.json',phase315_fixture())
    result=module.build(p303,p304,p311,p315,tmp_path/'artifacts/phase316')
    assert result['negative_result_registered'] is True; assert result['hypothesis_count']==24; assert result['retest_unchanged_family_allowed'] is False; assert result['experiment_budget_reopened'] is False; assert result['strategy_approved'] is False
