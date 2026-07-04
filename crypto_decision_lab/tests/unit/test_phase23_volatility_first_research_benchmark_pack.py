import csv
import json
from pathlib import Path

from crypto_decision_lab.reports.phase23_volatility_first_research_benchmark_pack import build_phase23_volatility_first_research_benchmark_pack


def _write_inputs(root: Path) -> None:
    p = root / "crypto_decision_lab/artifacts/phase22_model_performance_triage_research_gate_pack/phase22_model_performance_triage_research_gate_pack_index.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"gate_answer": "READY", "model_performance_triage_ready": True, "research_path_forward": "VOLATILITY_FIRST_RESEARCH_PATH"}), encoding="utf-8")

    m = root / "crypto_decision_lab/artifacts/phase20_baseline_metrics_null_models_harness_pack/metrics/all_baseline_null_model_metrics.csv"
    m.parent.mkdir(parents=True, exist_ok=True)
    with m.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["coin", "target", "baseline_id", "split", "mae"])
        w.writeheader()
        for coin in ["BTC", "ETH", "SOL"]:
            for split in ["TRAIN_RESEARCH_ONLY", "VALIDATION_RESEARCH_ONLY", "HOLDOUT_RESEARCH_ONLY"]:
                w.writerow({"coin": coin, "target": "forward_realized_vol_24h_research_target", "baseline_id": "TRAIN_MEAN_REALIZED_VOL", "split": split, "mae": 0.2})

    fields = ["timestamp", "coin", "split", "source", "rolling_vol_24h_ann", "rolling_vol_168h_ann", "rolling_vol_720h_ann", "return_24h_min", "return_24h_max", "forward_realized_vol_24h_research_target"]
    for coin in ["BTC", "ETH", "SOL"]:
        h = root / "crypto_decision_lab/artifacts/phase19_offline_experiment_harness_pack/harness" / f"{coin.lower()}_offline_experiment_harness_1h.csv"
        h.parent.mkdir(parents=True, exist_ok=True)
        with h.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for i in range(90):
                split = "TRAIN_RESEARCH_ONLY" if i < 54 else "VALIDATION_RESEARCH_ONLY" if i < 72 else "HOLDOUT_RESEARCH_ONLY"
                vol = 0.4 + (i % 10) / 100.0
                w.writerow({"timestamp": f"2026-01-01T{i:02d}:00:00Z", "coin": coin, "split": split, "source": "QRDS_OFFLINE_EXPERIMENT_HARNESS_RESEARCH_ONLY", "rolling_vol_24h_ann": vol, "rolling_vol_168h_ann": vol + 0.05, "rolling_vol_720h_ann": vol + 0.1, "return_24h_min": -0.01, "return_24h_max": 0.01, "forward_realized_vol_24h_research_target": vol + 0.01})


def test_phase23_volatility_first_builds(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write_inputs(root)
    result = build_phase23_volatility_first_research_benchmark_pack(tmp_path / "out", root, min_rows_per_coin=80)
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE23_VOLATILITY_FIRST_RESEARCH_BENCHMARK_READY_RESEARCH_ONLY"
    assert payload["volatility_first_benchmark_ready"] is True
    assert payload["phase22_research_path_forward"] == "VOLATILITY_FIRST_RESEARCH_PATH"
    assert payload["model_prediction_rows_generated"] == 0
    assert payload["models_are_trading_signals"] is False
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()
    assert Path(result["combined_vol_model_metrics_path"]).exists()


def test_phase23_no_operational_flags(tmp_path: Path) -> None:
    result = build_phase23_volatility_first_research_benchmark_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]
    for key in ["api_key_present", "authenticated_connection_used", "orders_generated", "real_orders_generated", "real_capital_used", "trading_signal_generated", "executable_signal_generated", "recommendation_generated", "allocation_generated", "portfolio_decision_generated", "operational_decision_allowed"]:
        assert payload[key] is False
