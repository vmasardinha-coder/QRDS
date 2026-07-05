import csv
import json
from pathlib import Path

from crypto_decision_lab.reports.phase35_recent_history_sparkline_panels_pack import build_phase35_recent_history_sparkline_panels_pack

def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)

def _write_inputs(root: Path) -> None:
    p34 = root / "crypto_decision_lab/artifacts/phase34_latest_observation_regime_snapshot_pack/phase34_latest_observation_regime_snapshot_pack_index.json"
    p34.parent.mkdir(parents=True, exist_ok=True)
    p34.write_text(json.dumps({"gate_answer": "PHASE34_LATEST_OBSERVATION_REGIME_SNAPSHOT_READY_RESEARCH_ONLY", "latest_observation_regime_snapshot_ready": True, "edge_validated": False, "shadow_decision_allowed": False, "decision_layer_allowed": False}), encoding="utf-8")
    fields = ["timestamp", "coin", "close", "rolling_vol_24h_ann", "rolling_vol_168h_ann", "source_dispersion_bps", "return_24h", "volatility_regime_24h", "dispersion_regime_24h", "momentum_diagnostic_24h"]
    for coin in ["BTC", "ETH", "SOL"]:
        path = root / "crypto_decision_lab/artifacts/phase18_research_feature_regime_diagnostics_pack/features" / f"{coin.lower()}_research_features_regime_1h.csv"
        rows = []
        for i in range(40):
            rows.append({"timestamp": f"2026-01-{(i % 28) + 1:02d}T{i % 24:02d}:00:00Z", "coin": coin, "close": str(100 + i), "rolling_vol_24h_ann": str(0.4 + i / 1000), "rolling_vol_168h_ann": str(0.5 + i / 1000), "source_dispersion_bps": str(4 + i / 10), "return_24h": "0.01", "volatility_regime_24h": "VOL_HIGH" if i > 20 else "VOL_MID", "dispersion_regime_24h": "DISP_LOW", "momentum_diagnostic_24h": "MOM_POS"})
        _write_csv(path, rows, fields)

def test_phase35_recent_history_sparkline_builds(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write_inputs(root)
    result = build_phase35_recent_history_sparkline_panels_pack(tmp_path / "out", root)
    payload = result["payload"]
    assert payload["gate_answer"] == "PHASE35_RECENT_HISTORY_SPARKLINE_PANELS_READY_RESEARCH_ONLY"
    assert payload["recent_history_sparkline_panels_ready"] is True
    assert payload["recent_history_rows"] >= 90
    assert payload["sparkline_rows"] >= 9
    assert payload["coin_coverage"] == 3
    assert payload["edge_validated"] is False
    assert payload["decision_layer_allowed"] is False
    assert payload["canonical_data_writes"] == 0
    assert Path(result["html_path"]).exists()

def test_phase35_no_operational_flags(tmp_path: Path) -> None:
    result = build_phase35_recent_history_sparkline_panels_pack(tmp_path / "out", tmp_path / "repo")
    payload = result["payload"]
    for key in ["api_key_present", "authenticated_connection_used", "orders_generated", "real_orders_generated", "real_capital_used", "trading_signal_generated", "executable_signal_generated", "recommendation_generated", "allocation_generated", "portfolio_decision_generated", "operational_decision_allowed"]:
        assert payload[key] is False
