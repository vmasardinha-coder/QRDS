import csv
import json
from pathlib import Path

from crypto_decision_lab.reports.phase22_model_performance_triage_research_gate_pack import build_phase22_model_performance_triage_research_gate_pack


def _write_phase21_index(root: Path) -> None:
    p = root / "crypto_decision_lab/artifacts/phase21_baseline_audit_interpretable_model_benchmark_pack/phase21_baseline_audit_interpretable_model_benchmark_pack_index.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(
            {
                "gate_answer": "READY",
                "interpretable_model_benchmark_ready": True,
                "combined_model_metrics_path": str(root / "crypto_decision_lab/artifacts/phase21_baseline_audit_interpretable_model_benchmark_pack/model_metrics/all_interpretable_model_metrics.csv"),
            }
        ),
        encoding="utf-8",
    )


def _write_phase21_metrics(root: Path) -> None:
    path = root / "crypto_decision_lab/artifacts/phase21_baseline_audit_interpretable_model_benchmark_pack/model_metrics/all_interpretable_model_metrics.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "coin",
        "model_id",
        "target",
        "split",
        "mae",
        "best_phase20_baseline_mae",
        "mae_improvement_vs_best_baseline",
        "beats_best_phase20_baseline",
    ]
    targets = [
        "forward_return_24h_research_target",
        "forward_abs_return_24h_research_target",
        "forward_realized_vol_24h_research_target",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for coin in ["BTC", "ETH", "SOL"]:
            for target in targets:
                for i in range(5):
                    for split in ["TRAIN_RESEARCH_ONLY", "VALIDATION_RESEARCH_ONLY", "HOLDOUT_RESEARCH_ONLY"]:
                        beat = target != "forward_return_24h_research_target" and split == "HOLDOUT_RESEARCH_ONLY"
                        w.writerow(
                            {
                                "coin": coin,
                                "model_id": f"M{i}",
                                "target": target,
                                "split": split,
                                "mae": 0.9 if beat else 1.1,
                                "best_phase20_baseline_mae": 1.0,
                                "mae_improvement_vs_best_baseline": 0.1 if beat else -0.1,
                                "beats_best_phase20_baseline": str(beat),
                            }
                        )


def test_phase22_model_performance_triage_builds(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write_phase21_index(root)
    _write_phase21_metrics(root)

    result = build_phase22_model_performance_triage_research_gate_pack(tmp_path / "out", root)
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE22_MODEL_PERFORMANCE_TRIAGE_RESEARCH_GATE_READY_RESEARCH_ONLY"
    assert payload["model_performance_triage_ready"] is True
    assert payload["phase21_model_benchmark_ready"] is True
    assert payload["return_model_research_gate"] == "BLOCK_RETURN_MODEL_ADVANCEMENT_RESEARCH_ONLY"
    assert payload["research_path_forward"] == "VOLATILITY_FIRST_RESEARCH_PATH"
    assert payload["triage_labels_are_signals"] is False
    assert payload["canonical_data_writes"] == 0
    assert payload["promotion_allowed"] is False
    assert payload["safe_apply_allowed"] is False
    assert Path(result["html_path"]).exists()


def test_phase22_model_performance_triage_has_no_operational_flags(tmp_path: Path) -> None:
    result = build_phase22_model_performance_triage_research_gate_pack(tmp_path / "out", tmp_path / "repo")
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
