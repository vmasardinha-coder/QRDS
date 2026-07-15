from crypto_decision_lab.scripts.phase286_295_calibration_shadow_readiness_common import p291
def test_phase291_ledger(tmp_path):
 m={"dependency_fingerprint":"a"*64};g={"eligible_for_forward_shadow":False,"reason_codes":["X"]};f={"freeze_contract":{"freeze_id":"id","hypothesis_id":"X"}};p=p291(m,g,f,tmp_path/"ledger.jsonl");e=p["ledger_event"];assert p["passed"] and e["orders_created"]==0 and e["capital_used"]==0 and e["signal"]=="NO_SIGNAL"
