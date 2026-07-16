from tests.unit._phase366_375_fixtures import run_chain


def test_phase370_never_turns_manual_rejection_into_recollection_request(monkeypatch, tmp_path):
    executed = run_chain(monkeypatch, tmp_path / "executed")["phase370_payload"]
    assert executed["recollection_assessment_applicable"] is True
    assert executed["existing_data_sufficient"] is True
    assert executed["public_recollection_needed"] is False

    rejected = run_chain(
        monkeypatch,
        tmp_path / "rejected",
        decision="REJECT_REAL_DATA_REMEDIATION_EVALUATION",
    )["phase370_payload"]
    assert rejected["recollection_assessment_applicable"] is False
    assert rejected["public_recollection_needed"] is False
    assert rejected["decision"] == "NO_PUBLIC_RECOLLECTION_EVALUATION_REJECTED_RESEARCH_ONLY"
    assert rejected["public_collection_started"] is False
