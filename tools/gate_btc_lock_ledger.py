"""Frozen LOCK25/50 prospective ledger implementation."""
from __future__ import annotations

import json
from typing import Any

from tools.gate_btc_measurement_common import (
    STRATEGIES, VARIANTS, atomic_json, canonical_sha, file_sha, iso_day,
    load_json, payload_sha, read_csv, require, snapshot_paths,
    validate_contract, write_immutable,
)


def initialize_lock(args) -> int:
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
    paths = snapshot_paths(args.ledger_dir)
    latest = load_json(paths[-1]) if paths else None
    atomic_json(args.ledger_dir / "STATUS.json", {
        "schema": "gate_btc.lock25_50_ledger_status.v1",
        "status": "ACTIVE" if latest else "READY_WAITING_FIRST_ELIGIBLE_CLOSE",
        "cycle_id": args.cycle_id,
        "first_eligible_close": first_close,
        "valid_snapshot_count": latest.get("sequence", 0) if latest else 0,
        "latest_snapshot_id": latest.get("snapshot_id") if latest else None,
        "track_count": 6,
        "strategies": list(STRATEGIES), "variants": list(VARIANTS),
        "config_sha256": anchor["config_sha256"],
        "research_only": True, "shadow_only": True, "not_approved": True,
        "orders_generated": 0, "real_capital_used": 0,
        "promotion_allowed": False,
    })
    print(json.dumps({"result": "DUPLICATE_IDENTICAL" if duplicate else "INITIALIZED", **anchor}, indent=2))
    return 0


def composition(rows: list[dict[str, str]], strategy: str, close: str) -> dict[str, Any]:
    selected = [row for row in rows if row.get("strategy") == strategy]
    require(selected, f"missing current portfolio: {strategy}")
    eligible = {row.get("execution_eligible_from", "") for row in selected}
    periods = {row.get("signal_period", "") for row in selected}
    require(len(eligible) == 1 and len(periods) == 1, f"ambiguous signal metadata: {strategy}")
    eligible_close = next(iter(eligible))
    require(iso_day(close, "snapshot close") >= iso_day(eligible_close, "execution eligibility"),
            f"{strategy} not eligible until {eligible_close}")
    assets = sorted((row.get("asset", ""), round(float(row.get("weight", 0)), 12)) for row in selected)
    require(abs(sum(weight for _, weight in assets) - 1.0) < 1e-8, f"weights do not sum to one: {strategy}")
    value = {
        "strategy": strategy,
        "signal_period": next(iter(periods)),
        "execution_eligible_from": eligible_close,
        "assets": assets,
    }
    value["composition_sha256"] = payload_sha(value)
    return value


def source_equity(rows: list[dict[str, str]], strategy: str, close: str) -> float:
    selected = [row for row in rows if row.get("strategy") == strategy and row.get("date") == close]
    require(len(selected) == 1, f"expected one equity row: {strategy} {close}")
    value = float(selected[0]["equity_brl"])
    require(value > 0, f"nonpositive equity: {strategy} {close}")
    return value


def row_sha(row: dict[str, Any]) -> str:
    clean = dict(row)
    clean.pop("row_sha256", None)
    return payload_sha(clean)


def build_row(contract, config_sha, cycle_id, close, strategy, variant, equity, comp, previous):
    if previous is None:
        base, daily_return, cash_before, risk_before = equity, 0.0, 0.0, equity
        prior_hwm, prior_armed, previous_sha, reentry = equity, False, None, False
    else:
        require(previous.get("row_sha256") == row_sha(previous), f"invalid prior row hash: {strategy}/{variant}")
        prior_source = float(previous["source_net_equity"])
        require(prior_source > 0, "invalid prior source equity")
        daily_return = equity / prior_source - 1.0
        base = float(previous["cycle_base_equity"])
        cash_before = float(previous["protected_cash_after"])
        risk_before = float(previous["risk_equity_after"])
        prior_hwm = float(previous["high_water_mark"])
        prior_armed = bool(previous.get("armed", False))
        previous_sha = previous["row_sha256"]
        reentry = previous.get("composition_sha256") != comp["composition_sha256"]
        if reentry and cash_before > 0:
            risk_before += cash_before
            cash_before = 0.0

    risk_after_return = risk_before * (1.0 + daily_return)
    total_before = risk_after_return + cash_before
    hwm = max(prior_hwm, total_before)
    if variant == "NO_LOCK_CONTROL":
        arm_multiple, share, retracement = None, 0.0, None
        armed, triggered, cash_after, risk_after = False, False, 0.0, total_before
    else:
        cfg = contract["variants"][variant]
        arm_multiple = float(cfg["arming_level_multiple"])
        share = float(cfg["protected_share_of_accumulated_profit"])
        retracement = float(cfg["retracement_trigger_pct"])
        armed = prior_armed or hwm >= base * arm_multiple
        triggered = armed and total_before / hwm - 1.0 <= -retracement
        cash_after, risk_after = cash_before, risk_after_return
        if triggered:
            target_cash = share * max(hwm - base, 0.0)
            transfer = min(max(target_cash - cash_before, 0.0), risk_after)
            cash_after += transfer
            risk_after -= transfer

    total_after = risk_after + cash_after
    row = {
        "date": close, "cycle_id": cycle_id, "portfolio": strategy, "variant": variant,
        "source_net_equity": equity, "source_daily_return": daily_return,
        "net_equity_before_lock": total_before, "net_equity_after_lock": total_after,
        "cycle_base_equity": base, "high_water_mark": hwm,
        "drawdown_from_hwm": total_after / hwm - 1.0,
        "armed_level": base * arm_multiple if arm_multiple is not None else None,
        "armed": armed, "lock_triggered": triggered,
        "protected_share": share, "retracement_trigger_pct": retracement,
        "protected_cash_before": cash_before, "protected_cash_after": cash_after,
        "risk_equity_after": risk_after, "reentry_signal": reentry,
        "signal_period": comp["signal_period"],
        "execution_eligible_from": comp["execution_eligible_from"],
        "composition_sha256": comp["composition_sha256"],
        "config_sha256": config_sha, "previous_row_sha256": previous_sha,
        "research_only": True, "shadow_only": True, "not_approved": True,
        "orders_generated": 0, "real_capital_used": 0,
    }
    row["row_sha256"] = row_sha(row)
    return row


def append_lock(args) -> int:
    contract = load_json(args.contract)
    validate_contract(contract)
    anchor_path = args.ledger_dir / "ANCHOR.json"
    require(anchor_path.exists(), "LOCK anchor missing")
    anchor = load_json(anchor_path)
    require(anchor.get("anchor_sha256") == canonical_sha(anchor, "anchor_sha256"), "invalid LOCK anchor hash")
    require(anchor.get("config_sha256") == file_sha(args.contract), "contract differs from frozen anchor")
    require(anchor.get("cycle_id") == args.cycle_id, "cycle_id differs from anchor")

    close = iso_day(args.snapshot_id, "snapshot_id").isoformat()
    require(iso_day(close, "snapshot_id") >= iso_day(anchor["first_eligible_close"], "first eligible close"),
            f"LOCK cannot start before {anchor['first_eligible_close']}")
    target = args.ledger_dir / "snapshots" / f"{close}.json"
    paths = snapshot_paths(args.ledger_dir)
    earlier = [path for path in paths if path.name < target.name]
    require(not [path for path in paths if path.name > target.name],
            "LOCK backfill behind newer immutable evidence prohibited")
    previous_snapshot = load_json(earlier[-1]) if earlier else None
    if previous_snapshot:
        require(previous_snapshot.get("snapshot_sha256") == canonical_sha(previous_snapshot, "snapshot_sha256"),
                "invalid previous LOCK snapshot hash")
    previous_rows = {(row["portfolio"], row["variant"]): row
                     for row in previous_snapshot.get("rows", [])} if previous_snapshot else {}

    equity_rows, portfolio_rows = read_csv(args.equity_curves), read_csv(args.current_portfolios)
    config_sha, rows = file_sha(args.contract), []
    for strategy in STRATEGIES:
        comp = composition(portfolio_rows, strategy, close)
        equity = source_equity(equity_rows, strategy, close)
        for variant in VARIANTS:
            rows.append(build_row(contract, config_sha, args.cycle_id, close, strategy, variant,
                                  equity, comp, previous_rows.get((strategy, variant))))

    snapshot = {
        "schema": "gate_btc.lock25_50_prospective_snapshot.v1",
        "snapshot_id": close,
        "sequence": int(previous_snapshot.get("sequence", 0)) + 1 if previous_snapshot else 1,
        "cycle_id": args.cycle_id,
        "previous_snapshot_sha256": previous_snapshot.get("snapshot_sha256") if previous_snapshot else None,
        "genesis": previous_snapshot is None,
        "config_sha256": config_sha,
        "source_artifacts": {
            args.equity_curves.name: file_sha(args.equity_curves),
            args.current_portfolios.name: file_sha(args.current_portfolios),
        },
        "rows": rows,
        "research_only": True, "shadow_only": True, "not_approved": True,
        "orders_generated": 0, "real_capital_used": 0, "promotion_allowed": False,
    }
    snapshot["snapshot_sha256"] = canonical_sha(snapshot, "snapshot_sha256")
    duplicate = write_immutable(target, snapshot, "snapshot_sha256")
    atomic_json(args.ledger_dir / "STATUS.json", {
        "schema": "gate_btc.lock25_50_ledger_status.v1", "status": "ACTIVE",
        "cycle_id": args.cycle_id, "first_eligible_close": anchor["first_eligible_close"],
        "valid_snapshot_count": snapshot["sequence"], "latest_snapshot_id": close,
        "latest_snapshot_sha256": snapshot["snapshot_sha256"], "track_count": 6,
        "strategies": list(STRATEGIES), "variants": list(VARIANTS),
        "config_sha256": config_sha,
        "research_only": True, "shadow_only": True, "not_approved": True,
        "orders_generated": 0, "real_capital_used": 0, "promotion_allowed": False,
    })
    print(json.dumps({"result": "DUPLICATE_IDENTICAL" if duplicate else "APPENDED", **snapshot}, indent=2))
    return 0
