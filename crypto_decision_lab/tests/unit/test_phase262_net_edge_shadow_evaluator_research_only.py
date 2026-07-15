from crypto_decision_lab.scripts.phase256_265_predictive_edge_validation_common import p261,p262
def test_phase262_costs_reduce_gross_return():
 rows=[{"row_id":i,"future_return_1h":.001 if i%2==0 else -.001} for i in range(72)]
 d={"examples":rows};pred=[{"fold":i//24+1,"row_id":i,"probability_up":.58 if i%2==0 else .42} for i in range(72)]
 c={"selected_candidate_name":"X","selected_candidate":{"predictions":pred,"mean_gross_return":.001}}
 p=p262(d,c,p261());assert p["passed"] and p["observations"]==72 and p["mean_net_return"]<p["mean_gross_return"] and not p["edge_validated"]
