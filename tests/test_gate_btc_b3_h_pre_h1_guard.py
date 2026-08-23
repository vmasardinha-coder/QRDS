from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd

SCRIPT = Path(__file__).parents[1] / "tools" / "gate_btc_b3_h_pre_h1_guard.py"
BASE = {
    "root": "WIN",
    "symbol": "WINQ26",
    "open": 100000.0,
    "high": 100100.0,
    "low": 99900.0,
    "close": 100050.0,
    "volume": 10.0,
    "trades": 2,
}


def run_guard(path: Path):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(path)],
        text=True,
        capture_output=True,
        check=False,
    )


def test_accepts_strictly_pre_cutoff_structural_data(tmp_path):
    row = dict(BASE, timestamp="2026-08-07T09:00:00-03:00", date="2026-08-07")
    p = tmp_path / "m5.csv"
    pd.DataFrame([row]).to_csv(p, index=False)
    r = run_guard(p)
    assert r.returncode == 0, r.stderr
    assert '"status": "PASS"' in r.stdout
    assert '"h1_economics_read": false' in r.stdout


def test_rejects_cutoff_or_later_data(tmp_path):
    row = dict(BASE, timestamp="2026-08-10T09:00:00-03:00", date="2026-08-10")
    p = tmp_path / "m5.csv"
    pd.DataFrame([row]).to_csv(p, index=False)
    r = run_guard(p)
    assert r.returncode != 0
    assert "H1_CUTOFF_VIOLATION" in r.stderr


def test_rejects_economic_columns(tmp_path):
    row = dict(BASE, timestamp="2026-08-07T09:00:00-03:00", date="2026-08-07", pnl=123.0)
    p = tmp_path / "m5.csv"
    pd.DataFrame([row]).to_csv(p, index=False)
    r = run_guard(p)
    assert r.returncode != 0
    assert "FORBIDDEN_ECONOMIC_COLUMNS" in r.stderr
