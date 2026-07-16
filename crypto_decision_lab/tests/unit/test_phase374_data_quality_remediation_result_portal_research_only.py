from pathlib import Path

from crypto_decision_lab.scripts.phase366_375_remediation_evaluation_common import REQUIRED_PORTAL_HEADINGS
from tests.unit._phase366_375_fixtures import run_chain


def test_phase374_explains_executed_and_rejected_paths_in_plain_language(monkeypatch, tmp_path):
    executed = run_chain(monkeypatch, tmp_path / "executed")["phase374_payload"]
    executed_text = Path(executed["portal_path"]).read_text(encoding="utf-8")
    assert all(heading in executed_text for heading in REQUIRED_PORTAL_HEADINGS)
    assert executed["result_mode"] == "EXECUTED_QUALITY_EVALUATION"

    rejected = run_chain(
        monkeypatch,
        tmp_path / "rejected",
        decision="REJECT_REAL_DATA_REMEDIATION_EVALUATION",
    )["phase374_payload"]
    rejected_text = Path(rejected["portal_path"]).read_text(encoding="utf-8")
    assert all(heading in rejected_text for heading in REQUIRED_PORTAL_HEADINGS)
    assert rejected["result_mode"] == "MANUAL_REJECTION_NO_EVALUATION"
    assert "NÃO APLICÁVEL" in rejected_text
    assert "REJEITADA / NÃO EXECUTADA" in rejected_text
    assert "R$ 0" in rejected_text
    assert rejected["capital_authorized_brl"] == 0
