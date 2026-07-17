from pathlib import Path
import pytest
from crypto_decision_lab.scripts.phase376_successful_data_quality_remediation_result_registry_research_only import build
from tests.unit._phase376_385_fixtures import setup_previous_chain, write_json

def test_phase376_registers_success_without_adoption(tmp_path:Path):
    paths=setup_previous_chain(tmp_path); result=build(paths["p375"],tmp_path/"out")
    assert result["candidate_dataset_adopted"] is False
    assert result["canonical_data_writes"]==0

def test_phase376_rejects_failed_quality_contract(tmp_path:Path):
    paths=setup_previous_chain(tmp_path); import json
    p=json.loads(paths["p375"].read_text()); p["data_quality_contract_pass"]=False; write_json(paths["p375"],p)
    with pytest.raises(RuntimeError,match="data_quality_contract_pass"): build(paths["p375"],tmp_path/"out")
