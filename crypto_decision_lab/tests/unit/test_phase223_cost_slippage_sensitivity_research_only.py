from pathlib import Path

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import write_json
from crypto_decision_lab.scripts.phase223_cost_slippage_sensitivity_research_only import (
    build_phase223,
)


def test_phase223_cost_burden_is_monotonic_and_has_no_pnl(tmp_path: Path):
    p222 = tmp_path / "p222.json"
    write_json(p222, {"calibration_diagnostic_passed": True})

    result = build_phase223(
        p222,
        tmp_path / "phase223.json",
        tmp_path / "phase223.md",
        root=tmp_path,
    )
    burdens = [
        item["cumulative_notional_cost_fraction"]
        for item in result["scenarios"]
    ]
    assert result["cost_slippage_sensitivity_passed"] is True
    assert burdens == sorted(burdens)
    assert result["pnl_or_trade_simulation_performed"] is False
