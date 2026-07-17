from pathlib import Path
import pytest
from crypto_decision_lab.scripts.phase382_rollback_and_raw_coexistence_audit_research_only import build
from tests.unit._phase376_385_fixtures import setup_previous_chain, base, write_json, sha256

def artifacts(tmp_path):
    p=setup_previous_chain(tmp_path); p379=base(379,candidate_contract={"candidate_dataset_path":p["candidate"].relative_to(tmp_path).as_posix(),"rollback_method":"REMOVE_METADATA_REGISTRY_REFERENCE_ONLY","canonical_data_writes":0}); p381=base(381,integrity_pass=True); return p,write_json(tmp_path/"379.json",p379),write_json(tmp_path/"381.json",p381)

def test_phase382_proves_raw_coexistence_and_rollback(tmp_path:Path):
    p,a,b=artifacts(tmp_path); r=build(p["p367"],a,b,tmp_path/"out",project_root=tmp_path); assert r["coexistence_pass"] and r["rollback_ready"]

def test_phase382_rejects_missing_raw_input(tmp_path:Path):
    p,a,b=artifacts(tmp_path); first=next((tmp_path/"data").glob("*.gz")); first.unlink()
    with pytest.raises(RuntimeError,match="all_raw_inputs_preserved"): build(p["p367"],a,b,tmp_path/"out",project_root=tmp_path)
