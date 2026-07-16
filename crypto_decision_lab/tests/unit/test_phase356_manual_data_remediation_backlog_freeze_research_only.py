from crypto_decision_lab.scripts import phase356_manual_data_remediation_backlog_freeze_research_only as module
from tests.unit._phase356_365_fixtures import patch_roots,payload,write_json

def test_phase356_freezes_two_questions(monkeypatch,tmp_path):
    patch_roots(monkeypatch,tmp_path,module); p351=write_json(tmp_path/"351.json",payload(351)); p355=write_json(tmp_path/"355.json",payload(355,next_window_decision="DATA_REMEDIATION_OR_GENUINELY_NEW_QUESTION_MANUAL_REVIEW_ONLY_RESEARCH_ONLY")); out=module.build(p351,p355,tmp_path/"out"); assert out["frozen_backlog_count"]==2; assert out["public_collection_started"] is False
