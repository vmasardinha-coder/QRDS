import csv
import json
from pathlib import Path

from crypto_decision_lab.reports.phase34_latest_observation_regime_snapshot_pack import build_phase34_latest_observation_regime_snapshot_pack


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _write_inputs(root: Path) -> None:
    p33 = root / "crypto_decision_lab/artifacts/phase33_freshness_drilldown_status_panels_pack/phase33_freshness_drilldown_status_panels_pack_index.json"
    p33.parent.mkdir(parents=True, exist_ok=True)
    p33.write_text(json.dumps({"gate_answer": "PHASE33_FRESHNESS_DRILLDOWN_STATUS_PANELS_READY_RESEARCH_ONLY", "freshness_drilldown_panels_ready": True, "edge_validated": False, "shadow_decision_allowed": False, "decision_layer_allowed": False}), encoding="utf-8")

    fields = ["timestamp", "coin", "close", "rolling_vol_24h_ann", "rolling_vol_168h_ann", "source_dispersion_bps", "return_24h", "volatility_regime_24h", "dispersion_regime_24h", "momentum_diagnostic_24h", "forward_realized_vol_24h_research_target"]
    for coin in ["BTC", "ETH", "SOL"]:
        path = root / "crypto_decision_lab/artifacts/phase18_research_feature_regime_diagnostics_pack/features" / f"{coin.lower()}_research_features_regime_1h.csv"
        _write_csv(path, [
            {"timestamp": "2026-01-01T00:00:00Z", "coin": coin, "close": "100", "rolling_vol_24h_ann": "0.4", "rolling_vol_168h_ann": "0.5", "source_dispersion_bps": "4", "return_24h": "0.01", "volatility_regime_24h": "VOL_MID", "dispersion_regime_24h": "DISP_LOW", "momentum_diagnostic_24h": "MOM_POS", "forward_realized_vol_24h_research_target": "0.42"},
            {"timestamp": "2026-01-02T00:00:00Z", "coin": coin, "close": "101", "rolling_vol_24h_ann": "0.41", "rolling_vol_168h_ann": "0.51", "source_dispersion_bps": "5", "return_24h": "0.02", "volatility_regime_24h": "VOL_HIGH", "dispersion_regime_24h": "DISP_LOW", "momentum_diagnostic_24h": "MOM_POS", "forward_realized_vol_24h_research_target": "0.43"},
        ], fields)


def test_phase34_latest_observation_regime_snapshot_builds(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write_inputs(root)
    result = build_phase34_latest_observation_regime_snapshot_pack(tmp_path / "out", root)
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE34_LATEST_OBSERVATION_REGIME_SNAPSHOT_READY_RESEARCH_ONLY"
    assert payload["latest_observation_regime_snapshot_ready"] is True
    assert payload["latest_observation_rows"] == 3
    assert payload["regime_snapshot_rows"] == 3
    assert payload["source_status_rows"] == 3
    assert payload["edge_validated"] is False
    assert payload["decision_layer_allowed"] is False
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()


def test_phase34_no_operational_flags(tmp_path: Path) -> None:
    result = build_phase34_latest_observation_regime_snapshot_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]
    for key in ["api_key_present", "authenticated_connection_used", "orders_generated", "real_orders_generated", "real_capital_used", "trading_signal_generated", "executable_signal_generated", "recommendation_generated", "allocation_generated", "portfolio_decision_generated", "operational_decision_allowed"]:
        assert payload[key] is False
