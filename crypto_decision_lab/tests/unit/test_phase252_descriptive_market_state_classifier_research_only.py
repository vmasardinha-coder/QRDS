from crypto_decision_lab.scripts.phase246_255_public_shadow_decision_common import classify,p252
def test_phase252_descriptive():
 ss=[]
 for n,o in (("A",0),("B",.01)):ss.append({"provider":n,"candles":[{"timestamp_ms":1700000000000+i*3600000,"close":100+i*.05+o} for i in range(120)]})
 p=p252({"evidence_fingerprint":"a"*64,"normalized_sources":ss},{"consensus_passed":True});assert p["passed"] and p["descriptive_only"] and not p["predictive_claim"] and not p["trading_signal"]
def test_phase252_labels():assert classify(.01,.02)=="TREND_POSITIVE_DESCRIPTIVE" and classify(-.01,-.02)=="TREND_NEGATIVE_DESCRIPTIVE"
