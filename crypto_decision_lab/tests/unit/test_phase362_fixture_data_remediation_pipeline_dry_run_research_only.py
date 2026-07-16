from crypto_decision_lab.scripts import phase362_fixture_data_remediation_pipeline_dry_run_research_only as module
from tests.unit._phase356_365_fixtures import patch_roots,payload,write_json

def test_phase362_fixture_idempotent(monkeypatch,tmp_path):
    patch_roots(monkeypatch,tmp_path,module); p360=write_json(tmp_path/"360.json",payload(360,preregistration_created=True)); p361=write_json(tmp_path/"361.json",payload(361,dry_run_pass=True)); out=module.build(p360,p361,tmp_path/"out"); assert out["dry_run_pass"] is True; assert out["checks"]["idempotent_hash"] is True; assert out["checks"]["network_calls"]==0
