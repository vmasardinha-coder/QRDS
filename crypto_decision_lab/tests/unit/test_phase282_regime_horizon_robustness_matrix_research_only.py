from crypto_decision_lab.scripts.phase276_285_strategy_search_common import p282
def test_phase282_cost_matrix():
 rows=[{"row_id":i,"regime":"RANGE" if i%2 else "HIGH_VOL","ret_6h":.01 if i%2 else -.01,"future_return_1h":.001 if i%3 else -.001} for i in range(480)]
 folds=[]
 for f in range(5):
  folds.append({"fold":f+1,"selected_hypothesis_id":"MOMENTUM_LB6_H1_P58","selected_spec":{"family":"MOMENTUM","lookback_hours":6,"forecast_horizon_hours":1,"probability_strength":.58},"outer_row_ids":list(range(f*96,(f+1)*96))})
 p=p282({"rows":rows},{"outer_folds":folds},{"modal_hypothesis_id":"MOMENTUM_LB6_H1_P58","search_validated":False})
 assert p["passed"] and len(p["cost_matrix"])==3 and not p["edge_validated"]
