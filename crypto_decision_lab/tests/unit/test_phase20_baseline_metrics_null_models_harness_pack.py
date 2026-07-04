import csv
import json
from pathlib import Path

from crypto_decision_lab.reports.phase20_baseline_metrics_null_models_harness_pack import build_phase20_baseline_metrics_null_models_harness_pack


def _write_phase19_index(root: Path) -> None:
    p = root / "crypto_decision_lab/artifacts/phase19_offline_experiment_harness_pack/phase19_offline_experiment_harness_pack_index.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"gate_answer": "READY", "offline_experiment_harness_ready": True}), encoding="utf-8")


def _write_harness(path: Path, coin: str, rows: int = 90) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "timestamp",
        "coin",
        "split",
        "source",
        "research_only",
        "target_horizon_hours",
        "return_1h",
        "log_return_1h",
        "rolling_vol_24h_ann",
        "rolling_vol_168h_ann",
        "rolling_vol_720h_ann",
        "momentum_sum_24h",
        "momentum_sum_168h",
        "drawdown_from_peak",
        "dispersion_bps",
        "dispersion_bps_mean_24h",
        "dispersion_bps_mean_168h",
        "return_24h_min",
        "return_24h_max",
        "source_count",
        "volatility_regime_24h",
        "volatility_regime_168h",
        "dispersion_regime_24h",
        "momentum_diagnostic_24h",
        "momentum_diagnostic_168h",
        "feature_maturity",
        "forward_return_24h_research_target",
        "forward_abs_return_24h_research_target",
        "forward_realized_vol_24h_research_target",
        "target_available",
        "prediction_generated",
        "trading_signal_generated",
        "recommendation_generated",
        "operational_decision_allowed",
        "canonical_write",
        "safe_apply_allowed",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i in range(rows):
            if i < 54:
                split = "TRAIN_RESEARCH_ONLY"
            elif i < 72:
                split = "VALIDATION_RESEARCH_ONLY"
            else:
                split = "HOLDOUT_RESEARCH_ONLY"
            target = ((i % 7) - 3) / 1000.0
            w.writerow(
                {
                    "timestamp": f"2026-01-{1 + (i // 24):02d}T{i % 24:02d}:00:00Z",
                    "coin": coin,
                    "split": split,
                    "source": "QRDS_OFFLINE_EXPERIMENT_HARNESS_RESEARCH_ONLY",
                    "research_only": "true",
                    "target_horizon_hours": 24,
                    "return_1h": 0.001,
                    "log_return_1h": 0.001,
                    "rolling_vol_24h_ann": 0.5 + (i % 3) * 0.1,
                    "rolling_vol_168h_ann": 0.6,
                    "rolling_vol_720h_ann": 0.7,
                    "momentum_sum_24h": 0.02,
                    "momentum_sum_168h": 0.05,
                    "drawdown_from_peak": 0.0,
                    "dispersion_bps": 5,
                    "dispersion_bps_mean_24h": 5,
                    "dispersion_bps_mean_168h": 5,
                    "return_24h_min": -0.01,
                    "return_24h_max": 0.01,
                    "source_count": 3,
                    "volatility_regime_24h": "VOL24_MEDIUM",
                    "volatility_regime_168h": "VOL168_MEDIUM",
                    "dispersion_regime_24h": "DISP24_MEDIUM",
                    "momentum_diagnostic_24h": "MOMENTUM_POSITIVE_RESEARCH_DIAGNOSTIC",
                    "momentum_diagnostic_168h": "MOMENTUM_POSITIVE_RESEARCH_DIAGNOSTIC",
                    "feature_maturity": "MATURE_RESEARCH_FEATURE_ROW",
                    "forward_return_24h_research_target": target,
                    "forward_abs_return_24h_research_target": abs(target),
                    "forward_realized_vol_24h_research_target": 0.4 + abs(target),
                    "target_available": "true",
                    "prediction_generated": "false",
                    "trading_signal_generated": "false",
                    "recommendation_generated": "false",
                    "operational_decision_allowed": "false",
                    "canonical_write": "false",
                    "safe_apply_allowed": "false",
                }
            )


def test_phase20_baseline_metrics_null_models_builds(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write_phase19_index(root)
    for coin in ["BTC", "ETH", "SOL"]:
        _write_harness(
            root / "crypto_decision_lab/artifacts/phase19_offline_experiment_harness_pack/harness" / f"{coin.lower()}_offline_experiment_harness_1h.csv",
            coin,
            rows=90,
        )

    result = build_phase20_baseline_metrics_null_models_harness_pack(tmp_path / "out", root, min_rows_per_coin=80)
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE20_BASELINE_METRICS_NULL_MODELS_READY_RESEARCH_ONLY"
    assert payload["baseline_metrics_ready"] is True
    assert payload["harness_rows_total"] == 270
    assert payload["baseline_metric_rows_total"] > 0
    assert payload["baseline_families_count"] >= 10
    assert payload["model_training_run"] is False
    assert payload["model_prediction_rows_generated"] == 0
    assert payload["target_columns_are_signals"] is False
    assert payload["canonical_data_writes"] == 0
    assert payload["promotion_allowed"] is False
    assert payload["safe_apply_allowed"] is False
    assert Path(result["html_path"]).exists()
    assert Path(result["combined_metrics_path"]).exists()


def test_phase20_baseline_metrics_has_no_operational_flags(tmp_path: Path) -> None:
    result = build_phase20_baseline_metrics_null_models_harness_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]
    for key in [
        "api_key_present",
        "authenticated_connection_used",
        "orders_generated",
        "real_orders_generated",
        "real_capital_used",
        "trading_signal_generated",
        "executable_signal_generated",
        "recommendation_generated",
        "allocation_generated",
        "portfolio_decision_generated",
        "operational_decision_allowed",
    ]:
        assert payload[key] is False
