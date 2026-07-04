import csv
import json
from pathlib import Path

from crypto_decision_lab.reports.phase28_regime_taxonomy_compression_failure_analysis_pack import build_phase28_regime_taxonomy_compression_failure_analysis_pack


def _write_inputs(root: Path) -> None:
    p = root / "crypto_decision_lab/artifacts/phase27_edge_candidate_stability_anti_overfit_pack/phase27_edge_candidate_stability_anti_overfit_pack_index.json"
    sp = root / "crypto_decision_lab/artifacts/phase27_edge_candidate_stability_anti_overfit_pack/edge_candidate_stability.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"gate_answer": "READY", "edge_candidate_stability_ready": True, "candidate_count": 1, "stable_edge_candidate_count": 0, "stability_path": str(sp)}), encoding="utf-8")
    fields = ["coin","regime_key","candidate_baseline_id","global_baseline_id","holdout_rows","early_rows","late_rows","full_improvement_pct","early_improvement_pct","late_improvement_pct","rows_pass","stable_edge_research_candidate"]
    with sp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerow({"coin": "BTC", "regime_key": "VOL24_HIGH|DISP24_LOW|MOMENTUM_POSITIVE", "candidate_baseline_id": "C", "global_baseline_id": "G", "holdout_rows": 120, "early_rows": 60, "late_rows": 60, "full_improvement_pct": 0.06, "early_improvement_pct": 0.03, "late_improvement_pct": -0.02, "rows_pass": "true", "stable_edge_research_candidate": "false"})

    h = root / "crypto_decision_lab/artifacts/phase19_offline_experiment_harness_pack/harness/btc_offline_experiment_harness_1h.csv"
    h.parent.mkdir(parents=True, exist_ok=True)
    fields_h = ["coin","split","source","volatility_regime_24h","dispersion_regime_24h","momentum_diagnostic_24h","forward_realized_vol_24h_research_target"]
    with h.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields_h)
        w.writeheader()
        for i in range(10):
            w.writerow({"coin": "BTC", "split": "HOLDOUT_RESEARCH_ONLY", "source": "QRDS_OFFLINE_EXPERIMENT_HARNESS_RESEARCH_ONLY", "volatility_regime_24h": "VOL24_HIGH", "dispersion_regime_24h": "DISP24_LOW", "momentum_diagnostic_24h": "MOMENTUM_POSITIVE", "forward_realized_vol_24h_research_target": 0.5})


def test_phase28_regime_compression_builds(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write_inputs(root)
    result = build_phase28_regime_taxonomy_compression_failure_analysis_pack(tmp_path / "out", root)
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE28_REGIME_TAXONOMY_COMPRESSION_FAILURE_ANALYSIS_READY_RESEARCH_ONLY"
    assert payload["regime_taxonomy_compression_ready"] is True
    assert payload["stable_edge_candidate_count"] == 0
    assert payload["decision_layer_allowed"] is False
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()
    assert Path(result["compression_map_path"]).exists()


def test_phase28_no_operational_flags(tmp_path: Path) -> None:
    result = build_phase28_regime_taxonomy_compression_failure_analysis_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]
    for key in ["api_key_present", "authenticated_connection_used", "orders_generated", "real_orders_generated", "real_capital_used", "trading_signal_generated", "executable_signal_generated", "recommendation_generated", "allocation_generated", "portfolio_decision_generated", "operational_decision_allowed"]:
        assert payload[key] is False
