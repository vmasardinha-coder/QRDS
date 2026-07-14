from crypto_decision_lab.scripts.phase246_255_public_shadow_decision_common import p253
def test_phase253_abstains():
 p=p253({"evidence_fingerprint":"a"*64,"snapshot_evidence_admitted":True},{"consensus_passed":True},{"descriptive_only":True,"predictive_claim":False,"trading_signal":False});assert p["passed"] and p["must_abstain"] and p["action"]=="NO_ACTION_RESEARCH_ONLY"
