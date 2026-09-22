from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOD_PATH = ROOT / "tools" / "qrds_b3_manual_contingency_close.py"
PS_PATH = ROOT / "tools" / "qrds_local_shadow_task_repair.ps1"


def load_module():
    spec = importlib.util.spec_from_file_location("qrds_manual_close", MOD_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_pnl_costs_are_measurement_only():
    mod = load_module()
    got = mod.pnl(100.0, 101.0, 1)
    assert round(got["gross_bps"], 9) == 100.0
    assert round(got["reference_net_bps"], 9) == 98.0
    assert round(got["stress_net_bps"], 9) == 97.0


def test_manual_close_is_noncanonical_read_only():
    text = MOD_PATH.read_text(encoding="utf-8")
    assert "MANUAL_CONTINGENCY_NON_CANONICAL" in text
    assert '"scientific_ledger_mutated": False' in text
    assert '"canonical_credit": 0' in text
    assert '"ORDERS": 0' in text
    assert '"REAL_CAPITAL": 0' in text
    assert "write_event" not in text


def test_task_repair_enforces_runtime_hardening():
    text = PS_PATH.read_text(encoding="utf-8")
    assert 'ExecutionHours = 72' in text
    assert 'MultipleInstances = "IgnoreNew"' in text
    assert 'AllowStartIfOnBatteries = $true' in text
    assert 'DontStopIfGoingOnBatteries = $true' in text
    assert 'Hidden = $true' in text
    assert 'UseUnifiedSchedulingEngine' in text
    assert 'ORDERS = 0' in text
    assert 'REAL_CAPITAL = 0' in text
