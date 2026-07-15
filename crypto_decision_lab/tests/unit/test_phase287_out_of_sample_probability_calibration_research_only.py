from crypto_decision_lab.scripts.phase286_295_calibration_shadow_readiness_common import p287

def test_phase287_reconstructs_actual_phase280_predictions():
    rows=[]
    folds=[]
    for row_id in range(480):
        rows.append(
            {
                "row_id":row_id,
                "ret_3h":0.01 if row_id%2 else -0.01,
                "label_up_4h":row_id%2,
            }
        )
    for fold in range(5):
        folds.append(
            {
                "fold":fold+1,
                "selected_hypothesis_id":"MEAN_REVERSION_LB3_H4_P57",
                "selected_spec":{
                    "family":"MEAN_REVERSION",
                    "lookback_hours":3,
                    "forecast_horizon_hours":4,
                    "probability_strength":0.57,
                },
                "outer_row_ids":list(
                    range(fold*96,(fold+1)*96)
                ),
            }
        )
    payload=p287(
        {"rows":rows},
        {"outer_folds":folds},
    )
    assert payload["passed"]
    assert payload["observations"]==480
    assert payload["prediction_reconstruction_used"]
    assert payload["reconstructed_prediction_count"]==480
    assert len(payload["reliability_table"])==2
    assert all(
        item["prediction_source_mode"]
        == "DETERMINISTIC_RECONSTRUCTION_FROM_FROZEN_SPEC"
        for item in payload["fold_calibration"]
    )
