from pathlib import Path
import gzip, pytest
from crypto_decision_lab.scripts.phase376_successful_data_quality_remediation_result_registry_research_only import build as b376
from crypto_decision_lab.scripts.phase377_manual_noncanonical_research_input_adoption_review_research_only import build as b377
from crypto_decision_lab.scripts.phase378_closed_family_isolation_audit_research_only import build as b378
from crypto_decision_lab.scripts.phase379_noncanonical_research_dataset_schema_and_lineage_contract_research_only import build
from tests.unit._phase376_385_fixtures import setup_previous_chain

def chain(tmp_path):
    p=setup_previous_chain(tmp_path); b376(p["p375"],tmp_path/"376"); b377(p["p367"],tmp_path/"376/phase376_successful_data_quality_remediation_result_registry.json",tmp_path/"377",decision="ADOPT_AS_NONCANONICAL_RESEARCH_INPUT_ONLY",reviewer_label="Victor"); b378(p["p369"],p["p375"],tmp_path/"377/phase377_manual_noncanonical_research_input_adoption_review.json",tmp_path/"378"); return p

def test_phase379_freezes_noncanonical_contract(tmp_path:Path):
    p=chain(tmp_path); r=build(p["p367"],p["p371"],tmp_path/"377/phase377_manual_noncanonical_research_input_adoption_review.json",tmp_path/"378/phase378_closed_family_isolation_audit.json",tmp_path/"379",project_root=tmp_path); assert r["candidate_contract_frozen"] is True and r["candidate_dataset_adopted_canonical"] is False

def test_phase379_rejects_candidate_hash_change(tmp_path:Path):
    p=chain(tmp_path); p["candidate"].write_bytes(p["candidate"].read_bytes()+b"x")
    with pytest.raises(RuntimeError,match="candidate_hash_matches"): build(p["p367"],p["p371"],tmp_path/"377/phase377_manual_noncanonical_research_input_adoption_review.json",tmp_path/"378/phase378_closed_family_isolation_audit.json",tmp_path/"379",project_root=tmp_path)
