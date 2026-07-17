from pathlib import Path
from crypto_decision_lab.scripts.phase376_successful_data_quality_remediation_result_registry_research_only import build as b376
from crypto_decision_lab.scripts.phase377_manual_noncanonical_research_input_adoption_review_research_only import build
from tests.unit._phase376_385_fixtures import setup_previous_chain

def test_phase377_approves_noncanonical_scope_only(tmp_path:Path):
    paths=setup_previous_chain(tmp_path); p376=b376(paths["p375"],tmp_path/"376")
    result=build(paths["p367"],tmp_path/"376/phase376_successful_data_quality_remediation_result_registry.json",tmp_path/"377",decision="ADOPT_AS_NONCANONICAL_RESEARCH_INPUT_ONLY",reviewer_label="Victor")
    assert result["candidate_adoption_approved"] is True
    assert result["canonical_adoption_approved"] is False

def test_phase377_preserve_decision_keeps_candidate_unadopted(tmp_path:Path):
    paths=setup_previous_chain(tmp_path); b376(paths["p375"],tmp_path/"376")
    result=build(paths["p367"],tmp_path/"376/phase376_successful_data_quality_remediation_result_registry.json",tmp_path/"377",decision="PRESERVE_CANDIDATE_UNADOPTED",reviewer_label="Victor")
    assert result["candidate_adoption_approved"] is False
