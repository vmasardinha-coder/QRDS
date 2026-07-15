from crypto_decision_lab.scripts.phase266_275_regime_replication_common import p273
def test_phase273_cost_matrix():
 rows=[{"row_id":i,"regime":"RANGE" if i%2 else "HIGH_VOL","future_return_1h":.001 if i%3 else -.001} for i in range(240)];pred=[{"fold":i//48+1,"row_id":i,"probability_up":.58 if i%2 else .42} for i in range(240)];p=p273({"rows":rows},{"selected_candidate_name":"X","selected_candidate":{"predictions":pred}});assert p["passed"] and p["stress_costs_bps"]==[10.0,25.0,50.0] and not p["edge_validated"]
