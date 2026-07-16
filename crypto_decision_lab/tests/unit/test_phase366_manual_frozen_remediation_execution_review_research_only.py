from crypto_decision_lab.scripts import phase366_manual_frozen_remediation_execution_review_research_only as module
from tests.unit._phase366_375_fixtures import create_prior_state, patch_roots


def test_phase366_records_both_explicit_manual_paths(monkeypatch, tmp_path):
    state = create_prior_state(tmp_path)
    patch_roots(monkeypatch, state["repo"], state["project"], module)

    approved = module.build(
        state["phase363"],
        state["phase365"],
        "APPROVE_ONE_FROZEN_REMEDIATION_EVALUATION",
        "Victor Sardinha",
        tmp_path / "approved",
    )
    assert approved["one_real_data_quality_evaluation_approved"] is True
    assert approved["approved_scope"] == "ONE_DATA_QUALITY_EVALUATION_ONLY"

    rejected = module.build(
        state["phase363"],
        state["phase365"],
        "REJECT_REAL_DATA_REMEDIATION_EVALUATION",
        "Victor Sardinha",
        tmp_path / "rejected",
    )
    assert rejected["one_real_data_quality_evaluation_approved"] is False
    assert rejected["approved_scope"] == "NONE"
    assert rejected["selected_decision"] == "REJECT_REAL_DATA_REMEDIATION_EVALUATION"
    assert rejected["locks"]["capital_used"] == 0
