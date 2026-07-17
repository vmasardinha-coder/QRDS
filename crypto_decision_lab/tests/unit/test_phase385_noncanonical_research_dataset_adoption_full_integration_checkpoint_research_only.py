from pathlib import Path
import json, pytest
from crypto_decision_lab.scripts.phase385_noncanonical_research_dataset_adoption_full_integration_checkpoint_research_only import build_checkpoint
from tests.unit._phase376_385_fixtures import base, write_json, junit, full_suite_override

def chain(tmp_path):
    values={375:base(375,data_quality_contract_pass=True),376:base(376,data_quality_contract_pass=True),377:base(377,candidate_adoption_approved=True,canonical_adoption_approved=False,selected_decision="ADOPT_AS_NONCANONICAL_RESEARCH_INPUT_ONLY"),378:base(378,isolation_pass=True),379:base(379,candidate_contract_frozen=True,candidate_dataset_adopted_noncanonical=True,candidate_dataset_adopted_canonical=False,candidate_contract_fingerprint="fp"),380:base(380,dry_run_pass=True,real_rows_used=0),381:base(381,integrity_pass=True,candidate_row_count=2),382:base(382,rollback_ready=True,coexistence_pass=True,raw_input_count=4),383:base(383,release_harness_pass=True,observed_failure_classes=["X"],workflow_installed=".github/workflows/x.yml",workflow_trigger_mode="MANUAL_OR_PULL_REQUEST_ONLY"),384:base(384,candidate_dataset_adopted_noncanonical=True,capital_authorized_brl=0,portal_relative_path="portal/index.html")}; return {p:write_json(tmp_path/f"{p}.json",v) for p,v in values.items()}

def test_phase385_integrates_adoption_and_global_suite(tmp_path:Path):
    r=build_checkpoint(chain(tmp_path),targeted_junit_path=junit(tmp_path/"junit.xml"),artifact_path=tmp_path/"out.json",documentation_path=tmp_path/"doc.md",tracking_dir=tmp_path/"tracking",full_suite_output_dir=tmp_path/"full",full_suite_override=full_suite_override()); assert r["candidate_dataset_adopted_noncanonical"] is True and r["global_full_suite"]["passed"]

def test_phase385_rejects_canonical_adoption(tmp_path:Path):
    paths=chain(tmp_path); value=json.loads(paths[377].read_text()); value["canonical_adoption_approved"]=True; write_json(paths[377],value)
    with pytest.raises(RuntimeError,match="phase377_canonical_adoption_forbidden"): build_checkpoint(paths,targeted_junit_path=junit(tmp_path/"junit.xml"),artifact_path=tmp_path/"out.json",documentation_path=tmp_path/"doc.md",tracking_dir=tmp_path/"tracking",full_suite_output_dir=tmp_path/"full",full_suite_override=full_suite_override())
