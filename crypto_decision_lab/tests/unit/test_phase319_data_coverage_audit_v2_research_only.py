from crypto_decision_lab.scripts import phase319_data_coverage_audit_v2_research_only as module
from tests.unit._phase316_325_fixtures import patch_roots,phase301_fixture,write_json

def test_phase319_audits_multisource_coverage(monkeypatch,tmp_path):
    patch_roots(monkeypatch,tmp_path,module); p301=write_json(tmp_path/'p301.json',phase301_fixture(tmp_path)); result=module.build(p301,tmp_path/'artifacts/phase319'); assert result['candle_dataset_count']==3; assert result['candle_datasets_meeting_threshold']==3; assert result['coverage_audit_pass'] is True; assert result['new_strategy_budget_created'] is False
