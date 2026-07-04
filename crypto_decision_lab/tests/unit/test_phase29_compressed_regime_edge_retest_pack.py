import csv
import json
from pathlib import Path

from crypto_decision_lab.reports.phase29_compressed_regime_edge_retest_pack import build_phase29_compressed_regime_edge_retest_pack


def _write_inputs(root: Path) -> None:
    p = root / "crypto_decision_lab/artifacts/phase28_regime_taxonomy_compression_failure_analysis_pack/phase28_regime_taxonomy_compression_failure_analysis_pack_index.json"
    cp = root / "crypto_decision_lab/artifacts/phase28_regime_taxonomy_compression_failure_analysis_pack/regime_compression_map.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"gate_answer": "READY", "regime_taxonomy_compression_ready": True, "compression_map_path": str(cp)}), encoding="utf-8")

    fields = ["coin","original_regime_key","coarse_regime_key","candidate_baseline_id","failure_reason"]
    with cp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerow({"coin": "BTC", "original_regime_key": "VOL24_HIGH|DISP24_LOW|MOMENTUM_POSITIVE", "coarse_regime_key": "VOL_COARSE_HIGH|DISP_COARSE_LOW|MOM_COARSE_POSITIVE", "candidate_baseline_id": "VOL_CURRENT_24H_PROXY", "failure_reason": "LATE_HOLDOUT_DECAY"})

    h = root / "crypto_decision_lab/artifacts/phase19_offline_experiment_harness_pack/harness/btc_offline_experiment_harness_1h.csv"
    h.parent.mkdir(parents=True, exist_ok=True)
    hfields = ["timestamp","coin","split","source","rolling_vol_24h_ann","rolling_vol_168h_ann","rolling_vol_720h_ann","return_24h_min","return_24h_max","volatility_regime_24h","dispersion_regime_24h","momentum_diagnostic_24h","forward_realized_vol_24h_research_target"]
    with h.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=hfields)
        w.writeheader()
        for i in range(260):
            split = "TRAIN_RESEARCH_ONLY" if i < 100 else "VALIDATION_RESEARCH_ONLY" if i < 130 else "HOLDOUT_RESEARCH_ONLY"
            vol = 0.4 + (i % 10) / 100.0
            w.writerow({"timestamp": f"2026-01-01T{i:03d}:00:00Z", "coin": "BTC", "split": split, "source": "QRDS_OFFLINE_EXPERIMENT_HARNESS_RESEARCH_ONLY", "rolling_vol_24h_ann": vol, "rolling_vol_168h_ann": vol + 0.02, "rolling_vol_720h_ann": vol + 0.04, "return_24h_min": -0.01, "return_24h_max": 0.01, "volatility_regime_24h": "VOL24_HIGH", "dispersion_regime_24h": "DISP24_LOW", "momentum_diagnostic_24h": "MOMENTUM_POSITIVE", "forward_realized_vol_24h_research_target": vol + 0.01})


def test_phase29_compressed_retest_builds(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write_inputs(root)
    result = build_phase29_compressed_regime_edge_retest_pack(tmp_path / "out", root)
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE29_COMPRESSED_REGIME_EDGE_RETEST_READY_RESEARCH_ONLY"
    assert payload["compressed_regime_retest_ready"] is True
    assert payload["phase28_compression_ready"] is True
    assert payload["compressed_retest_count"] == 1
    assert payload["edge_operationally_validated"] is False
    assert payload["decision_layer_allowed"] is False
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()
    assert Path(result["retest_path"]).exists()


def test_phase29_no_operational_flags(tmp_path: Path) -> None:
    result = build_phase29_compressed_regime_edge_retest_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]
    for key in ["api_key_present", "authenticated_connection_used", "orders_generated", "real_orders_generated", "real_capital_used", "trading_signal_generated", "executable_signal_generated", "recommendation_generated", "allocation_generated", "portfolio_decision_generated", "operational_decision_allowed"]:
        assert payload[key] is False
