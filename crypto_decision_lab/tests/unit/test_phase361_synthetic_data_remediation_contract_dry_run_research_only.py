from crypto_decision_lab.scripts import phase361_synthetic_data_remediation_contract_dry_run_research_only as module
from tests.unit._phase356_365_fixtures import patch_roots,payload,write_json

def test_phase361_synthetic_only(monkeypatch,tmp_path):
    patch_roots(monkeypatch,tmp_path,module); p360=write_json(tmp_path/"360.json",payload(360,preregistration_created=True,selected_remediation_id="TIMESTAMP_CONSENSUS_ALIGNMENT_REMEDIATION_V1")); out=module.build(p360,tmp_path/"out"); assert out["dry_run_pass"] is True; assert out["real_historical_rows_used"]==0
