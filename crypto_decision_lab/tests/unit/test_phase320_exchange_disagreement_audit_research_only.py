from crypto_decision_lab.scripts import phase320_exchange_disagreement_audit_research_only as module
from tests.unit._phase316_325_fixtures import patch_roots,payload,phase301_fixture,write_json

def test_phase320_measures_disagreement_without_directional_signal(monkeypatch,tmp_path):
    patch_roots(monkeypatch,tmp_path,module); p301=write_json(tmp_path/'p301.json',phase301_fixture(tmp_path)); p319=write_json(tmp_path/'p319.json',payload(319,coverage_audit_pass=True)); result=module.build(p301,p319,tmp_path/'artifacts/phase320'); assert result['provider_dataset_count']==3; assert result['common_hour_count']==800; assert result['disagreement_context_available'] is True; assert result['directional_signal_created'] is False
