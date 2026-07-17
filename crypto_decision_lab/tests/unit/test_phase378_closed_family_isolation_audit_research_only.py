from pathlib import Path
import json, pytest
from crypto_decision_lab.scripts.phase376_successful_data_quality_remediation_result_registry_research_only import build as b376
from crypto_decision_lab.scripts.phase377_manual_noncanonical_research_input_adoption_review_research_only import build as b377
from crypto_decision_lab.scripts.phase378_closed_family_isolation_audit_research_only import build
from tests.unit._phase376_385_fixtures import setup_previous_chain, write_json

def chain(tmp_path):
    p=setup_previous_chain(tmp_path); b376(p["p375"],tmp_path/"376"); b377(p["p367"],tmp_path/"376/phase376_successful_data_quality_remediation_result_registry.json",tmp_path/"377",decision="ADOPT_AS_NONCANONICAL_RESEARCH_INPUT_ONLY",reviewer_label="Victor"); return p

def test_phase378_keeps_closed_families_isolated(tmp_path:Path):
    p=chain(tmp_path); r=build(p["p369"],p["p375"],tmp_path/"377/phase377_manual_noncanonical_research_input_adoption_review.json",tmp_path/"378"); assert r["isolation_pass"] is True

def test_phase378_rejects_strategy_use_permission(tmp_path:Path):
    p=chain(tmp_path); path=tmp_path/"377/phase377_manual_noncanonical_research_input_adoption_review.json"; value=json.loads(path.read_text()); value["strategy_use_approved"]=True; write_json(path,value)
    with pytest.raises(RuntimeError,match="strategy_use_forbidden"): build(p["p369"],p["p375"],path,tmp_path/"378")
