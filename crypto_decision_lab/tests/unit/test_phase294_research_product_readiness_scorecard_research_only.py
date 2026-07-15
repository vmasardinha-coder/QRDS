from crypto_decision_lab.scripts.phase286_295_calibration_shadow_readiness_common import p294
def test_phase294_scorecard():
 m={"passed":True};g={"search_validated":False};c={"passed":True,"calibration_validated":False};s={"passed":True,"selection_stable":False};gate={"passed":True,"eligible_for_forward_shadow":False};portal={"passed":True};p=p294(m,g,c,s,gate,portal);assert p["passed"] and p["framework_readiness_score"]==100 and p["operational_readiness_score"]==0
