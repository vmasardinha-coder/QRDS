from pathlib import Path
import pytest
from crypto_decision_lab.scripts.phase381_noncanonical_research_dataset_integrity_audit_research_only import build
from tests.unit._phase376_385_fixtures import setup_previous_chain, base, write_json, sha256, SCHEMA

def artifacts(tmp_path):
    p=setup_previous_chain(tmp_path); p379=base(379,candidate_contract={"candidate_dataset_path":p["candidate"].relative_to(tmp_path).as_posix(),"candidate_dataset_sha256":sha256(p["candidate"]),"schema_fields":list(SCHEMA)}); p380=base(380,dry_run_pass=True); return p,write_json(tmp_path/"379.json",p379),write_json(tmp_path/"380.json",p380)

def test_phase381_verifies_candidate_integrity(tmp_path:Path):
    p,a,b=artifacts(tmp_path); r=build(p["p367"],a,b,tmp_path/"out",project_root=tmp_path); assert r["integrity_pass"] and r["candidate_row_count"]==2

def test_phase381_rejects_unsorted_or_duplicate_timestamp(tmp_path:Path):
    p,a,b=artifacts(tmp_path); from tests.unit._phase376_385_fixtures import write_gz,candidate_rows; rows=candidate_rows(); rows[1]["open_time_ms"]="0"; write_gz(p["candidate"],rows)
    import json; value=json.loads(a.read_text()); value["candidate_contract"]["candidate_dataset_sha256"]=sha256(p["candidate"]); write_json(a,value)
    with pytest.raises(RuntimeError,match="timestamps_strictly_increasing"): build(p["p367"],a,b,tmp_path/"out",project_root=tmp_path)
