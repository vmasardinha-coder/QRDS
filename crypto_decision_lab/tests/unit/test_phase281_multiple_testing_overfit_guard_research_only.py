from crypto_decision_lab.scripts.phase276_285_strategy_search_common import p281
def test_phase281_penalizes_search():
 f={"hypothesis_count":108};n={"total_outer_oos_rows":480,"outer_folds":[{"selected_hypothesis_id":"A","outer_metrics":{"brier_score":.24},"neutral_outer_metrics":{"brier_score":.25}} for _ in range(5)]}
 p=p281(f,n);assert p["passed"] and p["multiple_testing_penalty"]>0 and p["adjusted_brier_improvement"]<p["raw_mean_brier_improvement"]
