import csv
import json
from pathlib import Path

from crypto_decision_lab.reports.phase26_regime_segmented_volatility_edge_audit_pack import build_phase26_regime_segmented_volatility_edge_audit_pack


def _write_inputs(root: Path) -> None:
    p = root / "crypto_decision_lab/artifacts/phase25_volatility_feature_baseline_strengthening_pack/phase25_volatility_feature_baseline_strengthening_pack_index.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"gate_answer": "READY", "vol_feature_baseline_strengthening_ready": True}), encoding="utf-8")

    fields = ["timestamp","coin","split","source","rolling_vol_24h_ann","rolling_vol_168h_ann","rolling_vol_720h_ann","return_24h_min","return_24h_max","volatility_regime_24h","dispersion_regime_24h","momentum_diagnostic_24h","forward_realized_vol_24h_research_target"]
    for coin in ["BTC", "ETH", "SOL"]:
        h = root / "crypto_decision_lab/artifacts/phase19_offline_experiment_harness_pack/harness" / f"{coin.lower()}_offline_experiment_harness_1h.csv"
        h.parent.mkdir(parents=True, exist_ok=True)
        with h.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for i in range(140):
                split = "TRAIN_RESEARCH_ONLY" if i < 84 else "VALIDATION_RESEARCH_ONLY" if i < 112 else "HOLDOUT_RESEARCH_ONLY"
                vol = 0.4 + (i % 10) / 100.0
                w.writerow({"timestamp": f"2026-01-01T{i:02d}:00:00Z", "coin": coin, "split": split, "source": "QRDS_OFFLINE_EXPERIMENT_HARNESS_RESEARCH_ONLY", "rolling_vol_24h_ann": vol, "rolling_vol_168h_ann": vol + 0.02, "rolling_vol_720h_ann": vol + 0.04, "return_24h_min": -0.01, "return_24h_max": 0.01, "volatility_regime_24h": "VOL24_MEDIUM", "dispersion_regime_24h": "DISP24_MEDIUM", "momentum_diagnostic_24h": "MOMENTUM_NEUTRAL", "forward_realized_vol_24h_research_target": vol + 0.01})


def test_phase26_regime_edge_audit_builds(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write_inputs(root)
    result = build_phase26_regime_segmented_volatility_edge_audit_pack(tmp_path / "out", root, min_rows_per_coin=100)
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE26_REGIME_SEGMENTED_VOLATILITY_EDGE_AUDIT_READY_RESEARCH_ONLY"
    assert payload["regime_segmented_edge_audit_ready"] is True
    assert payload["phase25_strengthening_ready"] is True
    assert payload["edge_operationally_validated"] is False
    assert payload["decision_layer_allowed"] is False
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()
    assert Path(result["regime_audit_path"]).exists()


def test_phase26_no_operational_flags(tmp_path: Path) -> None:
    result = build_phase26_regime_segmented_volatility_edge_audit_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]
    for key in ["api_key_present", "authenticated_connection_used", "orders_generated", "real_orders_generated", "real_capital_used", "trading_signal_generated", "executable_signal_generated", "recommendation_generated", "allocation_generated", "portfolio_decision_generated", "operational_decision_allowed"]:
        assert payload[key] is False
