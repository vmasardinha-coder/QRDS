import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from tools import gate_btc_v16b_signal_stage as stage
from tools.gate_btc_v16b_prospective_seal import validate_signal_row


def _frame(n=25):
    rows = []
    for i in range(n):
        rows.append({
            "signal_date": pd.Timestamp("2026-08-13"),
            "symbol": f"A{i:02d}",
            "v16_ok": True,
            "v16_score": float(n - i) / 100.0,
        })
    return pd.DataFrame(rows)


def _meta(tmp_path: Path):
    p = tmp_path / "universe.json"
    p.write_text(json.dumps({
        "snapshot_id": "CMC_TOP150_20260813_PRIOR",
        "available_at_utc": "2026-08-13T20:00:00Z",
    }), encoding="utf-8")
    return p


def _patch(monkeypatch, n=25):
    frame = _frame(n)
    monkeypatch.setattr(stage, "load_panel", lambda p: frame.copy())
    monkeypatch.setattr(stage, "score_through", lambda p, d: frame.copy())
    monkeypatch.setattr(stage, "sha256_file", lambda p: "a" * 64 if "panel" in str(p) else "b" * 64)
    monkeypatch.setattr(stage, "model_state_fingerprint", lambda p, d: {
        "model_state_hash": "c" * 64,
        "definition": "test",
    })


def test_builder_freezes_full_ranking_without_friday_inputs(tmp_path, monkeypatch):
    _patch(monkeypatch, 25)
    panel = tmp_path / "panel.csv"
    panel.write_text("fixture", encoding="utf-8")
    out = stage.build_signal_input(panel, _meta(tmp_path), pd.Timestamp("2026-08-13"), "d" * 40)

    assert out["status"] == "OK"
    assert out["liquidity_qualified_count"] == 25
    assert len(out["eligible_scores"]) == 25
    assert len(out["score_ranking_desc"]) == 25
    assert out["preliminary_longs_10"] == [f"A{i:02d}" for i in range(10)]
    assert out["source_coverage"]["friday_shortability_inspected"] is False
    assert out["source_coverage"]["external_delta_inspected"] is False
    assert "shorts_10" not in out
    assert "shortability" not in out["input_data_hashes"]

    sealed = validate_signal_row(out, now=datetime(2026, 8, 14, 1, tzinfo=timezone.utc))
    assert sealed["event_type"] == "V16B_SIGNAL_SEAL"


def test_builder_fails_closed_below_20_scored_assets(tmp_path, monkeypatch):
    _patch(monkeypatch, 19)
    panel = tmp_path / "panel.csv"
    panel.write_text("fixture", encoding="utf-8")
    out = stage.build_signal_input(panel, _meta(tmp_path), pd.Timestamp("2026-08-13"), "d" * 40)
    assert out["status"] == "BLOCKED"
    assert out["eligible_scores"] == {}
    assert out["score_ranking_desc"] == []
    assert out["preliminary_longs_10"] == []


def test_builder_rejects_non_commit_identifier(tmp_path):
    panel = tmp_path / "panel.csv"
    panel.write_text("fixture", encoding="utf-8")
    with pytest.raises(ValueError, match="40-hex"):
        stage.build_signal_input(panel, _meta(tmp_path), pd.Timestamp("2026-08-13"), "not-a-commit")
