import csv
import json
from pathlib import Path

from crypto_decision_lab.reports.phase24_volatility_residual_diagnostics_baseline_robustness_pack import build_phase24_volatility_residual_diagnostics_baseline_robustness_pack


def _write_inputs(root: Path) -> None:
    p = root / "crypto_decision_lab/artifacts/phase23_volatility_first_research_benchmark_pack/phase23_volatility_first_research_benchmark_pack_index.json"
    metrics_path = root / "crypto_decision_lab/artifacts/phase23_volatility_first_research_benchmark_pack/volatility_models/all_volatility_first_metrics.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"gate_answer": "READY", "volatility_first_benchmark_ready": True, "combined_vol_model_metrics_path": str(metrics_path)}), encoding="utf-8")

    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["coin", "model_id", "split", "target", "mae", "best_phase20_vol_baseline_mae", "mae_improvement_vs_best_phase20_vol_baseline", "beats_best_phase20_vol_baseline"]
    with metrics_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for coin in ["BTC", "ETH", "SOL"]:
            for model in ["M1", "M2", "M3", "M4", "M5"]:
                for split in ["TRAIN_RESEARCH_ONLY", "VALIDATION_RESEARCH_ONLY", "HOLDOUT_RESEARCH_ONLY"]:
                    beat = coin == "BTC" and model == "M1" and split == "HOLDOUT_RESEARCH_ONLY"
                    w.writerow({"coin": coin, "model_id": model, "split": split, "target": "forward_realized_vol_24h_research_target", "mae": 0.9 if beat else 1.1, "best_phase20_vol_baseline_mae": 1.0, "mae_improvement_vs_best_phase20_vol_baseline": 0.1 if beat else -0.1, "beats_best_phase20_vol_baseline": str(beat)})

    for coin in ["BTC", "ETH", "SOL"]:
        h = root / "crypto_decision_lab/artifacts/phase19_offline_experiment_harness_pack/harness" / f"{coin.lower()}_offline_experiment_harness_1h.csv"
        h.parent.mkdir(parents=True, exist_ok=True)
        with h.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["coin", "split", "forward_realized_vol_24h_research_target"])
            w.writeheader()
            for i in range(10):
                w.writerow({"coin": coin, "split": "HOLDOUT_RESEARCH_ONLY", "forward_realized_vol_24h_research_target": 0.5 + i/100})


def test_phase24_volatility_residual_diagnostics_builds(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write_inputs(root)
    result = build_phase24_volatility_residual_diagnostics_baseline_robustness_pack(tmp_path / "out", root)
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE24_VOLATILITY_RESIDUAL_DIAGNOSTICS_BASELINE_ROBUSTNESS_READY_RESEARCH_ONLY"
    assert payload["vol_residual_diagnostics_ready"] is True
    assert payload["complex_model_allowed_by_triage"] is False
    assert payload["diagnostic_labels_are_signals"] is False
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()


def test_phase24_no_operational_flags(tmp_path: Path) -> None:
    result = build_phase24_volatility_residual_diagnostics_baseline_robustness_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]
    for key in ["api_key_present", "authenticated_connection_used", "orders_generated", "real_orders_generated", "real_capital_used", "trading_signal_generated", "executable_signal_generated", "recommendation_generated", "allocation_generated", "portfolio_decision_generated", "operational_decision_allowed"]:
        assert payload[key] is False
