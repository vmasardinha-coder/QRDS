from crypto_decision_lab.scripts import phase321_derivatives_missingness_audit_research_only as module
from tests.unit._phase316_325_fixtures import patch_roots,phase301_fixture,write_json

def test_phase321_audits_missingness_without_signal(monkeypatch,tmp_path):
    patch_roots(monkeypatch,tmp_path,module); p301=write_json(tmp_path/'p301.json',phase301_fixture(tmp_path)); result=module.build(p301,tmp_path/'artifacts/phase321'); assert result['usable_funding_dataset_count']>=1; assert result['usable_open_interest_dataset_count']>=1; assert result['derivatives_context_usable'] is True; assert result['missingness_used_as_directional_signal'] is False
