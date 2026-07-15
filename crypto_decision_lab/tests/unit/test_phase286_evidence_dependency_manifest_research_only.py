from crypto_decision_lab.scripts.phase286_295_calibration_shadow_readiness_common import p286
def test_phase286_manifest():
 d={"dataset_fingerprint":"a"*64,"dataset_rows":2000};n={"total_outer_oos_rows":480};g={"hypothesis_count":108,"modal_hypothesis_id":"X","search_validated":False};r={"robust_candidate":False};f={"eligible_for_forward_shadow":False};p={"product_packet":{"packet_version":"4.0"}};q=p286(d,n,g,r,f,p);assert q["passed"] and len(q["dependency_fingerprint"])==64
