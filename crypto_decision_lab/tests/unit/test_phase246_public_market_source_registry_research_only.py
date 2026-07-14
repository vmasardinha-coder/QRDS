from crypto_decision_lab.scripts.phase246_255_public_shadow_decision_common import p246
def test_phase246_sources():
 p=p246();assert p["passed"] and p["source_count"]==4 and p["minimum_successful_sources"]==2
