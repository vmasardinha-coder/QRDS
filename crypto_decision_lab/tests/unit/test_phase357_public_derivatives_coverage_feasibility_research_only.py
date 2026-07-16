from crypto_decision_lab.scripts import phase357_public_derivatives_coverage_feasibility_research_only as module
from tests.unit._phase356_365_fixtures import patch_roots,payload,write_json

def test_phase357_detects_public_coverage_gap(monkeypatch,tmp_path):
    patch_roots(monkeypatch,tmp_path,module); p301=write_json(tmp_path/"301.json",payload(301,official_endpoint_registry={"x":{}},official_docs_verified_on="2026-07-15")); p321=write_json(tmp_path/"321.json",payload(321,dataset_audits=[{"dataset":"binance_funding","missing_ratio":0.0},{"dataset":"bybit_open_interest","missing_ratio":0.1}],usable_funding_dataset_count=1,usable_open_interest_dataset_count=1)); p356=write_json(tmp_path/"356.json",payload(356)); out=module.build(p301,p321,p356,tmp_path/"out"); assert out["material_improvement_feasible_without_private_api"] is True; assert out["public_collection_started"] is False
