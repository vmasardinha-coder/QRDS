from crypto_decision_lab.scripts import (
    phase326_human_readable_novelty_non_overlap_review_research_only as module,
)
from tests.unit._phase326_335_fixtures import (
    patch_roots,
    payload,
    phase325_fixture,
    write_json,
)


def test_phase326_recommends_question_only_when_all_review_gates_pass(
    monkeypatch, tmp_path
):
    patch_roots(monkeypatch, tmp_path, module)
    values = {
        316: payload(
            316,
            negative_result_registered=True,
            current_family_decision="CLOSE_CURRENT_FAMILY_RESEARCH_ONLY",
        ),
        317: payload(
            317,
            registry_closed=True,
            prohibited_signature_count=24,
        ),
        318: payload(
            318,
            failure_category_count=5,
            failure_category_counts={"A": 1},
        ),
        319: payload(
            319,
            coverage_audit_pass=True,
            candle_datasets_meeting_threshold=4,
        ),
        320: payload(
            320,
            disagreement_context_available=True,
            common_hour_count=26270,
            spread_bps_p95=13.63,
        ),
        321: payload(
            321,
            derivatives_context_usable=True,
            dataset_audits=[],
        ),
        322: payload(
            322,
            genuinely_different_question_justified=True,
            passed_novelty_gate_count=8,
            novelty_gate_count=8,
            question_output="RESEARCH_ABSTAIN_OR_EVALUATE_ONLY",
            target_type="ABSTENTION_RELIABILITY_NOT_DIRECTIONAL_RETURN",
        ),
        323: payload(
            323,
            preregistration_draft_created=True,
            new_family_opened=False,
            experiment_budget_opened=False,
            preregistration_contract={},
        ),
        325: phase325_fixture(),
    }
    paths = {
        phase: write_json(tmp_path / f"p{phase}.json", value)
        for phase, value in values.items()
    }
    result = module.build(paths, tmp_path / "artifacts/phase326")
    assert result["passed_review_gate_count"] == 10
    assert (
        result["review_recommendation"]
        == "ACCEPT_QUESTION_FOR_PREREGISTRATION_REVIEW_ONLY"
    )
    assert result["new_family_opened"] is False
    assert result["experiment_budget_opened"] is False
