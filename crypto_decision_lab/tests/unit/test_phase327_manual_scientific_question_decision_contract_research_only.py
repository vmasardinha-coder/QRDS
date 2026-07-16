from crypto_decision_lab.scripts import (
    phase327_manual_scientific_question_decision_contract_research_only as module,
)
from tests.unit._phase326_335_fixtures import (
    patch_roots,
    payload,
    write_json,
)


def test_phase327_records_explicit_acceptance_without_opening_anything(
    monkeypatch, tmp_path
):
    patch_roots(monkeypatch, tmp_path, module)
    phase326 = write_json(
        tmp_path / "p326.json",
        payload(
            326,
            review_recommendation=(
                "ACCEPT_QUESTION_FOR_PREREGISTRATION_REVIEW_ONLY"
            ),
            failed_review_gate_count=0,
        ),
    )
    accepted = module.build(
        phase326,
        "ACCEPT",
        "Victor Sardinha",
        tmp_path / "artifacts/phase327",
    )
    rejected = module.build(
        phase326,
        "REJECT",
        "Victor Sardinha",
        tmp_path / "artifacts/phase327_reject",
    )
    assert accepted["question_accepted_for_preregistration"] is True
    assert accepted["new_family_opened"] is False
    assert accepted["experiment_budget_opened"] is False
    assert accepted["historical_evaluation_started"] is False
    assert rejected["question_rejected"] is True
