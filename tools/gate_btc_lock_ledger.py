"""Frozen LOCK25/50 prospective ledger tied to the eligible live QOS signals."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from tools.gate_btc_measurement_common import (
    STRATEGIES, VARIANTS, atomic_json, canonical_sha, file_sha, iso_day,
    load_json, payload_sha, read_csv, require, snapshot_paths,
    validate_contract, write_immutable,
)


def _weights(rows: list[dict[str, str]]) -> dict[str, float]:
    result = {str(row["asset"]): float(row["weight"]) for row in rows}
    require(result, "empty composition")
    require(abs(sum(result.values()) - 1.0) < 1e-8, "composition weights do not sum to one")
    require(all(value >= 0 for value in result.values()), "negative composition weight")
    return dict(sorted(result.items()))


def _signal(rows: list[dict[str, str]], strategy: str) -> dict[str, Any]:
    selected = [row for row in rows if row.get("strategy") == strategy]
    require(selected, f"missing signal for {strategy}")
    fields = {key: {str(row.get(key, "")) for row in selected}
              for key in ("data_as_of", "signal_period", "execution_eligible_from", "regime")}
    require(all(len(values) == 1 for values in fields.values()), f"ambiguous signal metadata for {strategy}")
    value = {
        "strategy": strategy,
        "data_as_of": next(iter(fields["data_as_of"])),
        "signal_period": next(iter(fields["signal_period"])),
        "execution_eligible_from": next(iter(fields["execution_eligible_from"])),
        "regime": next(iter(fields["regime"])),
        "weights": _weights(selected),
    }
    value["signal_sha256"] = payload_sha(value)
    return value


def _monthly_active(rows: list[dict[str, str]], strategy: str, base_date: str) -> dict[str, Any]:
    eligible = [row for row in rows if row.get("strategy") == strategy and row.get("execution_date", "") <= base_date]
    require(eligible, f"missing pre-cycle allocation for {strategy}")
    execution = max(row["execution_date"] for row in eligible)
    selected = [row for row in eligible if row["execution_date"] == execution]
    signal_dates = {row["signal_date"] for row in selected}
    regimes = {row["regime"] for row in selected}
    require(len(signal_dates) == 1 and len(regimes) == 1, f"ambiguous pre-cycle allocation for {strategy}")
    value = {
        "strategy": strategy,
        "data_as_of": next(iter(signal_dates)),
        "signal_period": str(next(iter(signal_dates)))[:7],
        "execution_eligible_from": execution,
        "regime": next(iter(regimes)),
        "weights": _weights(selected),
    }
    value["signal_sha256"] = payload_sha(value)
    return value


def _equity(rows: list[dict[str, str]], strategy: str, close: str) -> float:
    selected = [row for row in rows if row.get("strategy") == strategy and row.get("date") == close]
    require(len(selected) == 1, f"expected one base equity row for {strategy} on {close}")
    value = float(selected[0]["equity_brl"])
    require(value > 0, f"invalid base equity for {strategy}")
    return value


def initialize_lock(args) -> int:
    """Create the immutable contract anchor; source details are added separately."""
    contract = load_json(args.contract)
    validate_contract(contract)
    first_close = iso_day(args.first_eligible_close, "first eligible close").isoformat()
    anchor = {
        "schema": "gate_btc.lock25_50_ledger_anchor.v1",
        "status": "READY_WAITING_FIRST_ELIGIBLE_CLOSE",
        "cycle_id": args.cycle_id,
        "first_eligible_close": first_close,
        "strategies": list(STRATEGIES),
        "variants": list(VARIANTS),
        "config_sha256": file_sha(args.contract),
        "research_only": True, "shadow_only": True, "not_approved": True,
        "orders_generated": 0, "real_capital_used": 0,
        "promotion_allowed": False,
        "reset_rule": "EXPLICIT_USER_DECISION_ONLY",
    }
    anchor["anchor_sha256"] = canonical_sha(anchor, "anchor_sha256")
    duplicate = write_immutable(args.ledger_dir / "ANCHOR.json", anchor, "anchor_sha256")
    _write_status(args.ledger_dir, anchor, load_json(args.ledger_dir / "SOURCE_ANCHOR.json") if (args.ledger_dir / "SOURCE_ANCHOR.json").exists() else None)
    print(json.dumps({"result": "DUPLICATE_IDENTICAL" if duplicate else "INITIALIZED", **anchor}, indent=2))
    return 0


def initialize_source_anchor(args) -> int:
    """Freeze the pre-cycle portfolio, eligible signal, base equity and V2A cost inputs."""
    contract = load_json(args.contract)
    validate_contract(contract)
    anchor = load_json(args.ledger_dir / "ANCHOR.json")
    require(anchor.get("anchor_sha256") == canonical_sha(anchor, "anchor_sha256"), "invalid contract anchor hash")
    require(anchor.get("cycle_id") == args.cycle_id, "cycle differs from contract anchor")
    require(anchor.get("config_sha256") == file_sha(args.contract), "contract differs from anchor")
    base_date = iso_day(args.base_date, "base date").isoformat()
    require((iso_day(anchor["first_eligible_close"], "first eligible close") - timedelta(days=1)).isoformat() == base_date,
            "base date must immediately precede first eligible close")

    config = load_json(args.v2a_config)
    require(int(config.get("execution_lag_daily_bars", -1)) == 1, "V2A execution lag changed")
    require(bool(config.get("exclude_partial_current_month_from_backtest")) is True, "partial month guard changed")
    current, monthly, equity = read_csv(args.current_portfolios), read_csv(args.monthly_allocations), read_csv(args.equity_curves)
    portfolios: dict[str, Any] = {}
    for strategy in STRATEGIES:
        initial_signal = _signal(current, strategy)
        require(initial_signal["data_as_of"] == base_date, f"{strategy} signal is not from base date")
        require(initial_signal["execution_eligible_from"] == anchor["first_eligible_close"],
                f"{strategy} signal eligibility differs from frozen cycle")
        portfolios[strategy] = {
            "base_equity": _equity(equity, strategy, base_date),
            "pre_cycle_active_signal": _monthly_active(monthly, strategy, base_date),
            "initial_eligible_signal": initial_signal,
        }

    source = {
        "schema": "gate_btc.lock25_50_source_anchor.v1",
        "status": "FROZEN_READY_FOR_FIRST_ELIGIBLE_CLOSE",
        "cycle_id": args.cycle_id,
        "base_date": base_date,
        "first_eligible_close": anchor["first_eligible_close"],
        "contract_anchor_sha256": anchor["anchor_sha256"],
        "config_sha256": anchor["config_sha256"],
        "v2a_parameters": {
            "execution_lag_daily_bars": 1,
            "stable_return_annual": float(config["stable_return_annual"]),
            "fee_bps_per_rebalance_trade": float(config["fee_bps_per_rebalance_trade"]),
            "slippage_bps_per_rebalance_trade": float(config["slippage_bps_per_rebalance_trade"]),
            "funding_bps": 0.0,
            "protected_virtual_cash_return": 0.0,
        },
        "valuation_policy": {
            "mode": "EXACT_ACTIVE_HOLDING_CLOSE_SIDECAR",
            "source_priority": ["canonical_v2a_master_exact", "cdd", "binance", "okx"],
            "selection_engine_feed": False,
            "selection_membership_change_allowed": False,
            "exact_prior_and_current_close_required": True,
            "forward_fill_allowed": False,
            "synthetic_return_allowed": False,
        },
        "portfolios": portfolios,
        "source_artifacts": {
            args.current_portfolios.name: file_sha(args.current_portfolios),
            args.monthly_allocations.name: file_sha(args.monthly_allocations),
            args.equity_curves.name: file_sha(args.equity_curves),
            args.v2a_config.name: file_sha(args.v2a_config),
        },
        "research_only": True, "shadow_only": True, "not_approved": True,
        "orders_generated": 0, "real_capital_used": 0, "promotion_allowed": False,
    }
    source_run_id = getattr(args, "source_run_id", None)
    source_artifact_sha256 = getattr(args, "source_artifact_sha256", None)
    if source_run_id is not None or source_artifact_sha256 is not None:
        source["source_daily_research"] = {
            "run_id": int(source_run_id) if source_run_id is not None else None,
            "artifact_sha256": source_artifact_sha256,
        }
    source["source_anchor_sha256"] = canonical_sha(source, "source_anchor_sha256")
    duplicate = write_immutable(args.ledger_dir / "SOURCE_ANCHOR.json", source, "source_anchor_sha256")
    _write_status(args.ledger_dir, anchor, source)
    print(json.dumps({"result": "DUPLICATE_IDENTICAL" if duplicate else "SOURCE_ANCHORED", **source}, indent=2))
    return 0


def _write_status(ledger_dir: Path, anchor: dict[str, Any], source: dict[str, Any] | None = None,
                  latest: dict[str, Any] | None = None) -> None:
    if latest is None:
        paths = snapshot_paths(ledger_dir)
        latest = load_json(paths[-1]) if paths else None
    status = "ACTIVE" if latest else ("READY_WAITING_FIRST_ELIGIBLE_CLOSE" if source else "READY_WAITING_SOURCE_ANCHOR")
    history_path = ledger_dir / "SERIES_HISTORY.json"
    history = load_json(history_path) if history_path.exists() else None
    payload = {
        "schema": "gate_btc.lock25_50_ledger_status.v2",
        "status": status,
        "cycle_id": anchor["cycle_id"],
        "first_eligible_close": anchor["first_eligible_close"],
        "valid_snapshot_count": latest.get("sequence", 0) if latest else 0,
        "latest_snapshot_id": latest.get("snapshot_id") if latest else None,
        "latest_snapshot_sha256": latest.get("snapshot_sha256") if latest else None,
        "track_count": 6, "strategies": list(STRATEGIES), "variants": list(VARIANTS),
        "config_sha256": anchor["config_sha256"],
        "source_anchor_sha256": source.get("source_anchor_sha256") if source else None,
        "execution_timing": "SIGNAL_AT_CONFIRMED_DAILY_CLOSE_EXECUTE_NEXT_ELIGIBLE_DAILY_BAR",
        "research_only": True, "shadow_only": True, "not_approved": True,
        "orders_generated": 0, "real_capital_used": 0, "promotion_allowed": False,
    }
    if history is not None:
        require(
            history.get("series_history_sha256") == canonical_sha(history, "series_history_sha256"),
            "invalid LOCK series history hash",
        )
        payload["series_history_sha256"] = history["series_history_sha256"]
        payload["interrupted_series_count"] = len(history.get("interrupted_series", []))
        payload["retroactive_fill_prohibited_dates"] = history.get("retroactive_fill_prohibited_dates", [])
        payload["reanchor_authorized_at_utc"] = history.get("reanchor_authorized_at_utc")
    atomic_json(ledger_dir / "STATUS.json", payload)


def _prices(
    master_path: Path,
    assets: set[str],
    prior: date,
    current: date,
    valuation_sidecar: Path | None = None,
) -> dict[str, float]:
    risk_assets = {asset for asset in assets if asset != "CASH"}
    if valuation_sidecar is not None:
        from tools.gate_btc_lock_valuation_sidecar import validate_sidecar

        payload = load_json(valuation_sidecar)
        return validate_sidecar(
            payload,
            snapshot_id=current.isoformat(),
            prior_date=prior.isoformat(),
            required_assets=risk_assets,
        )

    lower = prior - timedelta(days=5)
    observations: dict[str, list[tuple[date, float]]] = {asset: [] for asset in risk_assets}
    for row in read_csv(master_path):
        symbol = row.get("symbol")
        if symbol not in observations:
            continue
        day = iso_day(row["date"], "master date")
        if lower <= day <= current:
            observations[symbol].append((day, float(row["close_usd"])))
    result: dict[str, float] = {}
    for asset, values in observations.items():
        values.sort()
        for label, target in (("prior", prior), ("current", current)):
            eligible = [(day, value) for day, value in values if day <= target]
            require(eligible, f"missing {label} price for {asset}")
            day, value = eligible[-1]
            require((target - day).days <= 5, f"stale {label} price for {asset}: {day}")
            result[f"{asset}:{label}"] = value
    return result


def _portfolio_return(weights: dict[str, float], prices: dict[str, float], stable_daily: float) -> tuple[float, dict[str, float]]:
    contributions: dict[str, float] = {}
    for asset, weight in weights.items():
        asset_return = stable_daily if asset == "CASH" else prices[f"{asset}:current"] / prices[f"{asset}:prior"] - 1.0
        contributions[asset] = weight * asset_return
    return sum(contributions.values()), dict(sorted(contributions.items()))


def _turnover(old: dict[str, float], new: dict[str, float]) -> float:
    return sum(abs(new.get(asset, 0.0) - old.get(asset, 0.0)) for asset in set(old) | set(new))


def _row_sha(row: dict[str, Any]) -> str:
    clean = dict(row)
    clean.pop("row_sha256", None)
    return payload_sha(clean)


def _process_row(contract: dict[str, Any], source: dict[str, Any], strategy: str, variant: str,
                 close: str, portfolio_return: float, contributions: dict[str, float],
                 active: dict[str, Any], prior_active: dict[str, Any], next_signal: dict[str, Any],
                 previous: dict[str, Any] | None) -> dict[str, Any]:
    base = float(source["portfolios"][strategy]["base_equity"])
    changed = active["signal_sha256"] != prior_active["signal_sha256"]
    params = source["v2a_parameters"]
    cost_rate = (float(params["fee_bps_per_rebalance_trade"]) + float(params["slippage_bps_per_rebalance_trade"])) / 10_000
    traded = _turnover(prior_active["weights"], active["weights"]) if changed else 0.0
    cost_fraction = traded * cost_rate

    if previous is None:
        risk, cash, hwm, armed = base, 0.0, base, False
        prior_pending_lock, prior_pending_reentry, previous_sha = None, False, None
    else:
        require(previous.get("row_sha256") == _row_sha(previous), f"invalid previous row hash {strategy}/{variant}")
        risk, cash = float(previous["risk_equity_after"]), float(previous["protected_cash_after"])
        hwm, armed = float(previous["high_water_mark"]), bool(previous.get("armed", False))
        prior_pending_lock = previous.get("pending_protected_cash_target")
        prior_pending_reentry = bool(previous.get("reentry_execution_pending", False))
        previous_sha = previous["row_sha256"]
    require(not (prior_pending_lock is not None and prior_pending_reentry),
            f"ambiguous simultaneous LOCK and reentry execution {strategy}/{variant}")
    protected_cash_before = cash

    lock_execution_applied = False
    reentry_execution_applied = False
    if prior_pending_reentry:
        risk += cash
        cash = 0.0
        reentry_execution_applied = True
    elif prior_pending_lock is not None:
        transfer = min(max(float(prior_pending_lock) - cash, 0.0), risk)
        risk -= transfer
        cash += transfer
        lock_execution_applied = transfer > 0

    equity_before_cost = risk + cash
    strategy_cost_amount = risk * cost_fraction
    risk = max(0.0, risk - strategy_cost_amount)
    risk *= 1.0 + portfolio_return
    total = risk + cash
    hwm = max(hwm, total)

    if variant == "NO_LOCK_CONTROL":
        arm_multiple, protected_share, retracement = None, 0.0, None
        armed = False
        lock_signal = False
        pending_target = None
    else:
        cfg = contract["variants"][variant]
        arm_multiple = float(cfg["arming_level_multiple"])
        protected_share = float(cfg["protected_share_of_accumulated_profit"])
        retracement = float(cfg["retracement_trigger_pct"])
        armed = armed or hwm >= base * arm_multiple
        target = protected_share * max(hwm - base, 0.0)
        drawdown = total / hwm - 1.0
        lock_signal = armed and drawdown <= -retracement and target > cash + 1e-12
        pending_target = target if lock_signal else None

    reentry_signal = cash > 0 and next_signal["signal_sha256"] != active["signal_sha256"]
    require(not (pending_target is not None and reentry_signal),
            f"ambiguous simultaneous LOCK and reentry signal {strategy}/{variant}")
    row = {
        "date": close, "cycle_id": source["cycle_id"], "portfolio": strategy, "variant": variant,
        "source_signal_data_as_of": active["data_as_of"],
        "source_signal_period": active["signal_period"],
        "source_signal_sha256": active["signal_sha256"],
        "next_signal_data_as_of": next_signal["data_as_of"],
        "next_signal_execution_eligible_from": next_signal["execution_eligible_from"],
        "next_signal_sha256": next_signal["signal_sha256"],
        "portfolio_return": portfolio_return, "return_contributions": contributions,
        "signal_changed_at_open": changed, "traded_notional": traded,
        "strategy_cost_fraction": cost_fraction, "strategy_cost_amount": strategy_cost_amount,
        "funding_amount": 0.0, "protected_cash_return": 0.0,
        "equity_before_cost": equity_before_cost,
        "net_equity_before_lock": total, "net_equity_after_lock": total,
        "cycle_base_equity": base, "high_water_mark": hwm,
        "drawdown_from_hwm": total / hwm - 1.0,
        "armed_level": base * arm_multiple if arm_multiple is not None else None,
        "armed": armed, "lock_triggered": lock_signal,
        "lock_execution_pending": pending_target is not None,
        "pending_protected_cash_target": pending_target,
        "lock_execution_applied": lock_execution_applied,
        "protected_share": protected_share, "retracement_trigger_pct": retracement,
        "protected_cash_before": protected_cash_before,
        "protected_cash_after": cash, "risk_equity_after": risk,
        "reentry_signal": reentry_signal,
        "reentry_execution_pending": reentry_signal,
        "reentry_execution_applied": reentry_execution_applied,
        "config_sha256": source["config_sha256"],
        "source_anchor_sha256": source["source_anchor_sha256"],
        "previous_row_sha256": previous_sha,
        "research_only": True, "shadow_only": True, "not_approved": True,
        "orders_generated": 0, "real_capital_used": 0,
    }
    row["row_sha256"] = _row_sha(row)
    return row


def append_lock(args) -> int:
    contract = load_json(args.contract)
    validate_contract(contract)
    anchor = load_json(args.ledger_dir / "ANCHOR.json")
    source = load_json(args.ledger_dir / "SOURCE_ANCHOR.json")
    require(anchor.get("anchor_sha256") == canonical_sha(anchor, "anchor_sha256"), "invalid contract anchor")
    require(source.get("source_anchor_sha256") == canonical_sha(source, "source_anchor_sha256"), "invalid source anchor")
    require(source.get("contract_anchor_sha256") == anchor["anchor_sha256"], "source/contract anchor mismatch")
    require(source.get("config_sha256") == file_sha(args.contract), "contract differs from source anchor")
    require(source.get("cycle_id") == args.cycle_id == anchor.get("cycle_id"), "cycle mismatch")

    close_day = iso_day(args.snapshot_id, "snapshot id")
    close = close_day.isoformat()
    target = args.ledger_dir / "snapshots" / f"{close}.json"
    all_paths = snapshot_paths(args.ledger_dir)
    require(not [path for path in all_paths if path.name > target.name], "LOCK backfill behind newer evidence prohibited")
    prior_paths = [path for path in all_paths if path.name < target.name]
    previous_snapshot = load_json(prior_paths[-1]) if prior_paths else None
    expected = (iso_day(previous_snapshot["snapshot_id"], "previous snapshot") + timedelta(days=1)) if previous_snapshot else iso_day(source["first_eligible_close"], "first eligible close")
    require(close_day == expected, f"LOCK requires consecutive close {expected.isoformat()}, got {close}")
    if previous_snapshot:
        require(previous_snapshot.get("snapshot_sha256") == canonical_sha(previous_snapshot, "snapshot_sha256"), "invalid previous snapshot hash")

    current_rows = read_csv(args.current_portfolios)
    current_signals = {strategy: _signal(current_rows, strategy) for strategy in STRATEGIES}
    require(all(signal["data_as_of"] == close for signal in current_signals.values()), "current signal data_as_of must equal snapshot close")
    require(all(signal["execution_eligible_from"] == (close_day + timedelta(days=1)).isoformat() for signal in current_signals.values()),
            "current signal must execute on next daily bar")

    if previous_snapshot:
        active_signals = previous_snapshot["next_signals"]
        prior_signals = previous_snapshot["active_signals"]
        prior_rows = {(row["portfolio"], row["variant"]): row for row in previous_snapshot["rows"]}
        prior_day = iso_day(previous_snapshot["snapshot_id"], "previous snapshot")
    else:
        active_signals = {strategy: source["portfolios"][strategy]["initial_eligible_signal"] for strategy in STRATEGIES}
        prior_signals = {strategy: source["portfolios"][strategy]["pre_cycle_active_signal"] for strategy in STRATEGIES}
        prior_rows = {}
        prior_day = iso_day(source["base_date"], "base date")
    require(all(signal["execution_eligible_from"] <= close for signal in active_signals.values()), "active signal not yet eligible")

    assets = {asset for signal in active_signals.values() for asset in signal["weights"]}
    valuation_sidecar = getattr(args, "valuation_sidecar", None)
    if source.get("valuation_policy", {}).get("mode") == "EXACT_ACTIVE_HOLDING_CLOSE_SIDECAR":
        require(valuation_sidecar is not None, "exact active-holding valuation sidecar required")
    price_map = _prices(args.master_daily, assets, prior_day, close_day, valuation_sidecar)
    stable_daily = (1.0 + float(source["v2a_parameters"]["stable_return_annual"])) ** (1.0 / 365.0) - 1.0
    rows = []
    for strategy in STRATEGIES:
        portfolio_return, contributions = _portfolio_return(active_signals[strategy]["weights"], price_map, stable_daily)
        for variant in VARIANTS:
            rows.append(_process_row(
                contract, source, strategy, variant, close, portfolio_return, contributions,
                active_signals[strategy], prior_signals[strategy], current_signals[strategy],
                prior_rows.get((strategy, variant)),
            ))

    snapshot = {
        "schema": "gate_btc.lock25_50_prospective_snapshot.v2",
        "snapshot_id": close,
        "sequence": int(previous_snapshot.get("sequence", 0)) + 1 if previous_snapshot else 1,
        "cycle_id": args.cycle_id,
        "previous_snapshot_sha256": previous_snapshot.get("snapshot_sha256") if previous_snapshot else None,
        "genesis": previous_snapshot is None,
        "config_sha256": source["config_sha256"],
        "source_anchor_sha256": source["source_anchor_sha256"],
        "active_signals": active_signals, "next_signals": current_signals,
        "source_artifacts": {
            args.master_daily.name: file_sha(args.master_daily),
            args.current_portfolios.name: file_sha(args.current_portfolios),
            **(
                {valuation_sidecar.name: file_sha(valuation_sidecar)}
                if valuation_sidecar is not None
                else {}
            ),
        },
        "valuation_evidence": (
            {
                "mode": "EXACT_ACTIVE_HOLDING_CLOSE_SIDECAR",
                "sidecar_sha256": load_json(valuation_sidecar)["sidecar_sha256"],
                "engine_feed": False,
            }
            if valuation_sidecar is not None
            else {"mode": "LEGACY_CANONICAL_MASTER", "engine_feed": False}
        ),
        "rows": rows,
        "research_only": True, "shadow_only": True, "not_approved": True,
        "orders_generated": 0, "real_capital_used": 0, "promotion_allowed": False,
    }
    snapshot["snapshot_sha256"] = canonical_sha(snapshot, "snapshot_sha256")
    duplicate = write_immutable(target, snapshot, "snapshot_sha256")
    _write_status(args.ledger_dir, anchor, source, snapshot)
    print(json.dumps({"result": "DUPLICATE_IDENTICAL" if duplicate else "APPENDED", **snapshot}, indent=2))
    return 0
