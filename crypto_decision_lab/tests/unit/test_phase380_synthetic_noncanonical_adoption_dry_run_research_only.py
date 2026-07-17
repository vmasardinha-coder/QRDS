from pathlib import Path
import json, pytest
from crypto_decision_lab.scripts.phase380_synthetic_noncanonical_adoption_dry_run_research_only import build
from tests.unit._phase376_385_fixtures import base, write_json, SCHEMA

def test_phase380_uses_synthetic_rows_only(tmp_path:Path):
    p=base(379,candidate_contract_frozen=True,candidate_contract={"schema_fields":list(SCHEMA),"canonical_data_writes":0}); path=write_json(tmp_path/"379.json",p); r=build(path,tmp_path/"out"); assert r["dry_run_pass"] and r["real_rows_used"]==0

def test_phase380_rejects_schema_drift(tmp_path:Path):
    p=base(379,candidate_contract_frozen=True,candidate_contract={"schema_fields":["wrong"],"canonical_data_writes":0}); path=write_json(tmp_path/"379.json",p)
    with pytest.raises(RuntimeError,match="schema_exact"): build(path,tmp_path/"out")
