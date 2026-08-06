#!/usr/bin/env python3
"""Fail-closed scaffold for the GATE BTC Bull Replay.

This module validates the frozen contract, builds deterministic synthetic
fixtures, evaluates allocation grids, and emits a research-only manifest.
It deliberately does not load real market data or place orders.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

REQUIRED_BENCHMARKS = ("Victor_proxy", "BTC_puro", "BTC_ETH_70_30")
REQUIRED_PHASES = (
    "PRE_REVERSAL",
    "EARLY_BULL",
    "ACCELERATION",
    "MID_BULL",
    "LATE_BULL",
    "TOP_REVERSAL",
)


class ContractError(RuntimeError):
    """Raised when the frozen research contract is invalid."""


@dataclass(frozen=True)
class Metrics:
    total_return: float
    max_drawdown: float
    sharpe_rf0: float
    calmar: float
    upside_capture: float


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_contract(path: Path) -> Mapping[str, object]:
    contract = json.loads(path.read_text(encoding="utf-8"))
    if contract.get("research_only") is not True:
        raise ContractError("research_only must be true")
    if contract.get("operational_status") != "NOT_APPROVED":
        raise ContractError("operational_status must be NOT_APPROVED")
    if contract.get("orders_allowed") is not False:
        raise ContractError("orders_allowed must be false")
    if contract.get("real_capital_allowed") is not False:
        raise ContractError("real_capital_allowed must be false")
    if tuple(contract.get("benchmarks_required", ())) != REQUIRED_BENCHMARKS:
        raise ContractError("mandatory benchmark set changed")
    if tuple(contract.get("phases", ())) != REQUIRED_PHASES:
        raise ContractError("bull phase order changed")
    splits = contract.get("allocation_splits")
    if not isinstance(splits, list) or not splits:
        raise ContractError("allocation_splits missing")
    for split in splits:
        if not isinstance(split, list) or len(split) != 2 or sum(split) != 100:
            raise ContractError(f"invalid allocation split: {split!r}")
    guards = contract.get("methodology_guards", {})
    required_guards = (
        "lookahead_prohibited",
        "post_result_rule_changes_prohibited",
        "gateway_current_composition_retrospective_prohibited",
        "macroquant_methodology_must_remain_independent",
    )
    if any(guards.get(key) is not True for key in required_guards):
        raise ContractError("one or more methodology guards are disabled")
    return contract


def synthetic_returns() -> Dict[str, List[float]]:
    """Deterministic phase-aware fixtures for infrastructure validation only."""
    btc = [-0.012, 0.018, 0.031, 0.044, 0.027, -0.021, 0.036, 0.052, 0.019, -0.028, 0.014, -0.009]
    return {
        "BTC_puro": btc,
        "BTC_ETH_70_30": [x * 0.94 + 0.001 for x in btc],
        "Victor_proxy": [x * 0.86 + 0.002 for x in btc],
        "QOS_Moderada": [x * 0.78 + 0.003 for x in btc],
        "QOS_Ultra": [x * 0.69 + 0.0035 for x in btc],
        "Delta_LS_50_50": [0.004, 0.006, 0.008, 0.009, 0.004, -0.003, 0.006, 0.007, 0.003, -0.005, 0.002, -0.001],
        "Delta_LS_50_50_StopVol": [0.003, 0.005, 0.006, 0.007, 0.003, -0.002, 0.005, 0.006, 0.002, -0.003, 0.002, 0.0],
        "Delta_LS_70_30": [0.002, 0.008, 0.012, 0.014, 0.007, -0.006, 0.009, 0.013, 0.005, -0.008, 0.003, -0.002],
        "Delta_LS_70_30_StopVol": [0.002, 0.006, 0.009, 0.010, 0.005, -0.004, 0.007, 0.009, 0.004, -0.005, 0.003, -0.001],
    }


def equity_curve(returns: Sequence[float]) -> List[float]:
    equity = [1.0]
    for value in returns:
        equity.append(equity[-1] * (1.0 + value))
    return equity


def metrics(returns: Sequence[float], btc_returns: Sequence[float]) -> Metrics:
    if len(returns) != len(btc_returns) or len(returns) < 2:
        raise ValueError("returns must be aligned and contain at least two observations")
    curve = equity_curve(returns)
    peak = curve[0]
    max_dd = 0.0
    for value in curve:
        peak = max(peak, value)
        max_dd = min(max_dd, value / peak - 1.0)
    total = curve[-1] - 1.0
    mean = sum(returns) / len(returns)
    variance = sum((x - mean) ** 2 for x in returns) / (len(returns) - 1)
    volatility = math.sqrt(variance)
    sharpe = mean / volatility * math.sqrt(len(returns)) if volatility else 0.0
    calmar = total / abs(max_dd) if max_dd < 0 else 0.0
    positive_btc = sum(max(x, 0.0) for x in btc_returns)
    positive_strategy = sum(r for r, b in zip(returns, btc_returns) if b > 0)
    upside = positive_strategy / positive_btc if positive_btc else 0.0
    return Metrics(total, max_dd, sharpe, calmar, upside)


def combine(core: Sequence[float], dynamic: Sequence[float], core_weight: int) -> List[float]:
    if len(core) != len(dynamic):
        raise ValueError("unaligned series")
    wc = core_weight / 100.0
    wd = 1.0 - wc
    return [wc * c + wd * d for c, d in zip(core, dynamic)]


def run_synthetic(contract_path: Path, output_dir: Path) -> Mapping[str, object]:
    contract = load_contract(contract_path)
    series = synthetic_returns()
    missing = [name for name in REQUIRED_BENCHMARKS if name not in series]
    if missing:
        raise ContractError(f"missing mandatory benchmarks: {missing}")

    output_dir.mkdir(parents=True, exist_ok=True)
    rows: List[Mapping[str, object]] = []
    btc = series["BTC_puro"]
    cores = [name for name in contract["core_candidates"] if name in series]
    dynamics = [name for name in contract["dynamic_candidates"] if name in series]
    for core in cores:
        for dynamic in dynamics:
            for core_weight, dynamic_weight in contract["allocation_splits"]:
                mixed = combine(series[core], series[dynamic], int(core_weight))
                result = metrics(mixed, btc)
                rows.append({
                    "core": core,
                    "dynamic": dynamic,
                    "core_weight": core_weight,
                    "dynamic_weight": dynamic_weight,
                    "total_return": result.total_return,
                    "max_drawdown": result.max_drawdown,
                    "sharpe_rf0": result.sharpe_rf0,
                    "calmar": result.calmar,
                    "upside_capture": result.upside_capture,
                    "fixture_only": True,
                })

    csv_path = output_dir / "GATE_BTC_BULL_REPLAY_SYNTHETIC_METRICS.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "status": "PASS_SYNTHETIC_INFRASTRUCTURE_ONLY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "operational_status": "NOT_APPROVED",
        "orders_generated": 0,
        "real_capital_used": 0,
        "real_market_data_loaded": False,
        "holdout_opened": False,
        "contract_sha256": _sha256(contract_path),
        "metrics_sha256": _sha256(csv_path),
        "rows": len(rows),
        "benchmarks_present": list(REQUIRED_BENCHMARKS),
        "macroquant_included": False,
        "next_gate": "VALIDATE_REAL_DATA_AVAILABILITY_WITHOUT_RUNNING_VISIBLE_EVALUATION",
    }
    manifest_path = output_dir / "GATE_BTC_BULL_REPLAY_SYNTHETIC_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--synthetic-only", action="store_true")
    args = parser.parse_args()
    if not args.synthetic_only:
        raise SystemExit("fail-closed: only --synthetic-only is implemented")
    manifest = run_synthetic(args.contract, args.output_dir)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
