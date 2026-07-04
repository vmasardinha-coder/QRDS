import csv
import json
from pathlib import Path

from crypto_decision_lab.reports.phase25_volatility_feature_baseline_strengthening_pack import build_phase25_volatility_feature_baseline_strengthening_pack


def _write_inputs(root: Path) -> None:
    p = root / "crypto_decision_lab/artifacts/phase24_volatility_residual_diagnostics_baseline_robustness_pack/phase24_volatility_residual_diagnostics_baseline_robustness_pack_index.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"gate_answer": "READY", "vol_residual_diagnostics_ready": True, "diagnostic_path_forward": "STRENGTHEN_VOLATILITY_BASELINES_AND_FEATURES_RESEARCH_ONLY"}), encoding="utf-8")

    p20 = root / "crypto_decision_lab/artifacts/phase20_baseline_metrics_null_models_harness_pack/metrics/all_baseline_null_model_metrics.csv"
    p20.parent.mkdir(parents=True, exist_ok=True)
    with p20.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["coin", "target", "baseline_id", "split", "mae"])
        w.writeheader()
        for coin in ["BTC", "ETH", "SOL"]:
            for split in ["TRAIN_RESEARCH_ONLY", "VALIDATION_RESEARCH_ONLY", "HOLDOUT_RESEARCH_ONLY"]:
                w.writerow({"coin": coin, "target": "forward_realized_vol_24h_research_target", "baseline_id": "B20", "split": split, "mae": 0.2})

    p23 = root / "crypto_decision_lab/artifacts/phase23_volatility_first_research_benchmark_pack/volatility_models/all_volatility_first_metrics.csv"
    p23.parent.mkdir(parents=True, exist_ok=True)
    with p23.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["coin", "model_id", "split", "mae"])
        w.writeheader()
        for coin in ["BTC", "ETH", "SOL"]:
            for split in ["TRAIN_RESEARCH_ONLY", "VALIDATION_RESEARCH_ONLY", "HOLDOUT_RESEARCH_ONLY"]:
                w.writerow({"coin": coin, "model_id": "M23", "split": split, "mae": 0.18})

    fields = ["timestamp","coin","split","source","rolling_vol_24h_ann","rolling_vol_168h_ann","rolling_vol_720h_ann","return_24h_min","return_24h_max","volatility_regime_24h","dispersion_regime_24h","momentum_diagnostic_24h","forward_realized_vol_24h_research_target"]
    for coin in ["BTC", "ETH", "SOL"]:
        h = root / "crypto_decision_lab/artifacts/phase19_offline_experiment_harness_pack/harness" / f"{coin.lower()}_offline_experiment_harness_1h.csv"
        h.parent.mkdir(parents=True, exist_ok=True)
        with h.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for i in range(90):
                split = "TRAIN_RESEARCH_ONLY" if i < 54 else "VALIDATION_RESEARCH_ONLY" if i < 72 else "HOLDOUT_RESEARCH_ONLY"
                vol = 0.4 + (i % 10) / 100.0
                w.writerow({"timestamp": f"2026-01-01T{i:02d}:00:00Z", "coin": coin, "split": split, "source": "QRDS_OFFLINE_EXPERIMENT_HARNESS_RESEARCH_ONLY", "rolling_vol_24h_ann": vol, "rolling_vol_168h_ann": vol + 0.02, "rolling_vol_720h_ann": vol + 0.04, "return_24h_min": -0.01, "return_24h_max": 0.01, "volatility_regime_24h": "VOL24_MEDIUM", "dispersion_regime_24h": "DISP24_MEDIUM", "momentum_diagnostic_24h": "MOMENTUM_NEUTRAL", "forward_realized_vol_24h_research_target": vol + 0.01})


def test_phase25_strengthening_builds(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write_inputs(root)
    result = build_phase25_volatility_feature_baseline_strengthening_pack(tmp_path / "out", root, min_rows_per_coin=80)
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE25_VOLATILITY_FEATURE_BASELINE_STRENGTHENING_READY_RESEARCH_ONLY"
    assert payload["vol_feature_baseline_strengthening_ready"] is True
    assert payload["model_training_run"] is False
    assert payload["model_prediction_rows_generated"] == 0
    assert payload["baselines_are_trading_signals"] is False
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()
    assert Path(result["combined_strengthened_baselines_path"]).exists()


def test_phase25_no_operational_flags(tmp_path: Path) -> None:
    result = build_phase25_volatility_feature_baseline_strengthening_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]
    for key in ["api_key_present", "authenticated_connection_used", "orders_generated", "real_orders_generated", "real_capital_used", "trading_signal_generated", "executable_signal_generated", "recommendation_generated", "allocation_generated", "portfolio_decision_generated", "operational_decision_allowed"]:
        assert payload[key] is False
