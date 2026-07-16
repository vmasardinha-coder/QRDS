from crypto_decision_lab.scripts import phase358_timestamp_consensus_alignment_feasibility_research_only as module
from tests.unit._phase356_365_fixtures import patch_roots,payload,write_json

def test_phase358_freezes_no_leakage_alignment(monkeypatch,tmp_path):
    patch_roots(monkeypatch,tmp_path,module); p301=write_json(tmp_path/"301.json",payload(301)); p320=write_json(tmp_path/"320.json",payload(320,provider_dataset_count=4,common_hour_count=26270,spread_bps_p95=13.63)); p356=write_json(tmp_path/"356.json",payload(356)); out=module.build(p301,p320,p356,tmp_path/"out"); assert out["material_improvement_feasible_with_existing_data"] is True; assert out["future_leakage_allowed"] is False
