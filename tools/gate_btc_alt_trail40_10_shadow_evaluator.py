#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
from datetime import date
from pathlib import Path

CANDIDATE = "ALT_TRAIL40_10_CLOSE_LAG1_V1"
STRATEGIES = ("QOS_Moderada", "QOS_Ultra")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def payload_sha(value, field):
    clean = dict(value)
    clean.pop(field, None)
    return hashlib.sha256(canonical_bytes(clean)).hexdigest()


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_contract(contract):
    require(contract["schema"] == "gate_btc.alt_trail40_10_shadow_contract.v1", "bad contract schema")
    require(contract["candidate_name"] == CANDIDATE, "candidate drift")
    d = contract["candidate_definition"]
    require(d["activation_gain"] == 0.40, "activation drift")
    require(d["trailing_buffer_fraction_of_running_close_high"] == 0.10, "buffer drift")
    require(d["same_bar_arm_and_exit"] is False, "same-bar drift")
    require(d["parameter_retuning_before_gate"] is False, "retuning drift")
    g = contract["prospective_gate"]
    require(g["evaluation_cohort"] == "ARMED_COMPLETED_JOURNEYS", "evaluation cohort drift")
    require(g["trim_top_positive_fraction"] == 0.05, "trim fraction drift")
    require(g["max_single_case_positive_benefit_share"] == 0.20, "dominance threshold drift")
    require(contract["research_only"] is True and contract["engine_feed"] is False, "safety drift")


def load_chain(contract_path, ledger_dir):
    contract = load_json(contract_path)
    validate_contract(contract)
    ledger_dir = Path(ledger_dir)
    anchor = load_json(ledger_dir / "ANCHOR.json")
    require(anchor["candidate_name"] == CANDIDATE, "anchor candidate drift")
    require(anchor["contract_sha256"] == file_sha(contract_path), "contract/anchor hash mismatch")
    paths = sorted((ledger_dir / "snapshots").glob("*.json"))
    rows = []
    previous_sha = None
    for path in paths:
        row = load_json(path)
        require(row["candidate_name"] == CANDIDATE, f"candidate drift {path.name}")
        require(row["contract_sha256"] == anchor["contract_sha256"], f"contract drift {path.name}")
        require(row["row_sha256"] == payload_sha(row, "row_sha256"), f"row hash invalid {path.name}")
        require(row.get("previous_row_sha256") == previous_sha, f"hash chain broken {path.name}")
        previous_sha = row["row_sha256"]
        rows.append(row)
    return contract, anchor, rows


def unique_cycles(rows, strategy):
    cycles = []
    last_signal = None
    for row in rows:
        require(strategy in row["signals"], f"missing strategy {strategy} {row['snapshot_date']}")
        sig = row["signals"][strategy]
        if sig["signal_date"] != last_signal:
            cycles.append({
                "strategy": strategy,
                "signal_date": sig["signal_date"],
                "execution_eligible_from": sig["execution_eligible_from"],
                "regime": sig["regime"],
                "picks": list(sig["picks"]),
            })
            last_signal = sig["signal_date"]
    return cycles


def price_rows(rows, asset, start_day, end_day=None):
    result = []
    for row in rows:
        day = date.fromisoformat(row["snapshot_date"])
        if day < start_day:
            continue
        if end_day is not None and day > end_day:
            continue
        if asset in row.get("selected_alt_closes", {}):
            result.append((day, float(row["selected_alt_closes"][asset])))
    return result


def first_price(rows, asset, start_day, strict=False):
    for day, price in price_rows(rows, asset, start_day):
        if (day > start_day) if strict else (day >= start_day):
            return day, price
    return None


def evaluate_trade(contract, rows, cycle, next_signal_date, asset):
    activation = float(contract["candidate_definition"]["activation_gain"])
    buffer_fraction = float(contract["candidate_definition"]["trailing_buffer_fraction_of_running_close_high"])
    entry_target = date.fromisoformat(cycle["execution_eligible_from"])
    entry = first_price(rows, asset, entry_target, strict=False)
    if entry is None:
        return {
            "strategy": cycle["strategy"], "signal_date": cycle["signal_date"], "regime": cycle["regime"],
            "asset": asset, "status": "WAITING_ENTRY", "armed": False, "completed": False,
        }
    entry_day, entry_price = entry
    require(entry_day == entry_target, f"entry date drift {cycle['strategy']} {asset}: {entry_day} != {entry_target}")

    baseline_exit = None
    boundary = date.fromisoformat(next_signal_date) if next_signal_date else None
    if boundary is not None:
        baseline_exit = first_price(rows, asset, boundary, strict=True)

    last_day = baseline_exit[0] if baseline_exit else date.fromisoformat(rows[-1]["snapshot_date"])
    path = price_rows(rows, asset, entry_day, last_day)
    require(path and path[0][0] == entry_day, f"missing entry path {cycle['strategy']} {asset}")

    # Once entered, every confirmed daily snapshot through the control exit must be present.
    expected_days = [date.fromisoformat(r["snapshot_date"]) for r in rows if entry_day <= date.fromisoformat(r["snapshot_date"]) <= last_day]
    got_days = [day for day, _ in path]
    require(got_days == expected_days, f"missing daily price in active path {cycle['strategy']} {asset}")

    running_high = entry_price
    armed = False
    arm_date = None
    trigger_date = None
    trigger_stop = None
    pre_exit_running_high = None
    candidate_exit_date = None
    candidate_exit_price = None
    exit_reason = None

    for day, price in path[1:]:
        if trigger_date is not None:
            candidate_exit_date = day
            candidate_exit_price = price
            exit_reason = "TRAIL_NEXT_BAR"
            break

        if baseline_exit is not None and day == baseline_exit[0]:
            candidate_exit_date = day
            candidate_exit_price = price
            exit_reason = "CONTROL_BOUNDARY"
            break

        if armed:
            active_stop = running_high * (1.0 - buffer_fraction)
            if price <= active_stop:
                trigger_date = day
                trigger_stop = active_stop
                pre_exit_running_high = running_high
                continue
            running_high = max(running_high, price)
        else:
            running_high = max(running_high, price)
            if price / entry_price - 1.0 >= activation:
                armed = True
                arm_date = day

    completed = baseline_exit is not None
    if completed and candidate_exit_date is None:
        # This only occurs when entry and control exit are the same row, which the contract forbids.
        require(baseline_exit[0] > entry_day, "non-positive control holding period")
        candidate_exit_date, candidate_exit_price = baseline_exit
        exit_reason = "CONTROL_BOUNDARY"

    if not completed:
        if trigger_date is not None and candidate_exit_date is None:
            state = "TRIGGERED_EXIT_PENDING"
        elif armed:
            state = "ACTIVE_ARMED"
        else:
            state = "ACTIVE_UNARMED"
        return {
            "strategy": cycle["strategy"], "signal_date": cycle["signal_date"], "regime": cycle["regime"],
            "asset": asset, "status": state, "entry_date": entry_day.isoformat(), "entry_price": entry_price,
            "armed": armed, "arm_date": arm_date.isoformat() if arm_date else None,
            "running_high": running_high, "trigger_date": trigger_date.isoformat() if trigger_date else None,
            "trigger_stop": trigger_stop, "completed": False,
        }

    baseline_exit_date, baseline_exit_price = baseline_exit
    baseline_return = baseline_exit_price / entry_price - 1.0
    candidate_return = candidate_exit_price / entry_price - 1.0
    advantage = candidate_return - baseline_return

    recovery = "NOT_APPLICABLE"
    if exit_reason == "TRAIL_NEXT_BAR" and candidate_exit_date < baseline_exit_date:
        future = price_rows(rows, asset, candidate_exit_date, baseline_exit_date)
        recovered = any(day > candidate_exit_date and price > float(pre_exit_running_high) for day, price in future)
        recovery = "RECOVERED_AFTER_TRAIL" if recovered else "NON_RECOVERED"

    outcome = "HELPED" if advantage > 0 else ("HURT" if advantage < 0 else "UNCHANGED")
    return {
        "strategy": cycle["strategy"], "signal_date": cycle["signal_date"], "regime": cycle["regime"],
        "asset": asset, "status": "COMPLETED", "entry_date": entry_day.isoformat(), "entry_price": entry_price,
        "armed": armed, "arm_date": arm_date.isoformat() if arm_date else None,
        "trigger_date": trigger_date.isoformat() if trigger_date else None,
        "trigger_stop": trigger_stop, "pre_exit_running_high": pre_exit_running_high,
        "candidate_exit_date": candidate_exit_date.isoformat(), "candidate_exit_price": candidate_exit_price,
        "candidate_exit_reason": exit_reason,
        "control_exit_date": baseline_exit_date.isoformat(), "control_exit_price": baseline_exit_price,
        "candidate_return": candidate_return, "control_return": baseline_return, "advantage": advantage,
        "outcome": outcome, "recovery": recovery, "completed": True,
    }


def bootstrap_ci(values, reps, seed):
    if len(values) < 2:
        return None, None, None
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(reps):
        means.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    low = means[int(0.025 * (reps - 1))]
    high = means[int(0.975 * (reps - 1))]
    p_positive = sum(x > 0 for x in means) / reps
    return low, high, p_positive


def build_evaluation(contract, rows, trades):
    completed = [t for t in trades if t.get("completed")]
    armed_completed = [t for t in completed if t.get("armed")]
    triggered_completed = [t for t in armed_completed if t.get("trigger_date")]
    values = [float(t["advantage"]) for t in armed_completed]
    gate = contract["prospective_gate"]
    latest_day = date.fromisoformat(rows[-1]["snapshot_date"]) if rows else None
    freeze_day = date.fromisoformat(gate["freeze_date"])
    calendar_days = (latest_day - freeze_day).days if latest_day else 0

    mean_adv = statistics.fmean(values) if values else None
    median_adv = statistics.median(values) if values else None
    low, high, p_positive = bootstrap_ci(values, int(gate["bootstrap_reps"]), int(gate["bootstrap_seed"]))
    positive = [x for x in values if x > 0]
    negative = [x for x in values if x < 0]
    positive_benefit = sum(positive)
    regret = -sum(negative)
    dominance = max(positive) / positive_benefit if positive_benefit > 0 else None

    trim_n = math.ceil(len(positive) * float(gate["trim_top_positive_fraction"])) if positive else 0
    trimmed = sorted(positive, reverse=True)[trim_n:] + negative + [x for x in values if x == 0]
    trimmed_mean = statistics.fmean(trimmed) if trimmed else None

    checks = {
        "execution_aware_mean_advantage_gt_0": mean_adv is not None and mean_adv > 0,
        "median_advantage_gt_0": median_adv is not None and median_adv > 0,
        "paired_bootstrap_95pct_ci_low_gt_0": low is not None and low > 0,
        "aggregate_benefit_gt_aggregate_regret": positive_benefit > regret,
        "mean_advantage_after_removing_top_5pct_positive_cases_gt_0": trimmed_mean is not None and trimmed_mean > 0,
        "no_single_case_dominates_total_positive_benefit": dominance is not None and dominance < float(gate["max_single_case_positive_benefit_share"]),
    }
    eligible = (
        len(armed_completed) >= int(gate["minimum_armed_completed_journeys"])
        and calendar_days >= int(gate["minimum_calendar_days_since_freeze"])
    )
    if not eligible:
        decision = "WAITING_PROSPECTIVE_GATE"
    elif all(checks[name] for name in gate["requirements_all"]):
        decision = "PROMOTION_CANDIDATE_RESEARCH_ONLY"
    else:
        decision = "NO_PROMOTION"

    result = {
        "schema": "gate_btc.alt_trail40_10_shadow_evaluation.v1",
        "candidate_name": CANDIDATE,
        "as_of": latest_day.isoformat() if latest_day else None,
        "evaluation_cohort": gate["evaluation_cohort"],
        "completed_journeys": len(completed),
        "armed_completed_journeys": len(armed_completed),
        "triggered_completed_journeys": len(triggered_completed),
        "calendar_days_since_freeze": calendar_days,
        "gate_minimum_armed_completed_journeys": int(gate["minimum_armed_completed_journeys"]),
        "gate_minimum_calendar_days": int(gate["minimum_calendar_days_since_freeze"]),
        "gate_eligible": eligible,
        "mean_advantage": mean_adv,
        "median_advantage": median_adv,
        "bootstrap_ci95_low": low,
        "bootstrap_ci95_high": high,
        "bootstrap_probability_positive": p_positive,
        "aggregate_positive_benefit": positive_benefit,
        "aggregate_regret": regret,
        "benefit_regret_ratio": positive_benefit / regret if regret > 0 else (None if positive_benefit == 0 else float("inf")),
        "trimmed_mean_advantage": trimmed_mean,
        "largest_positive_benefit_share": dominance,
        "checks": checks,
        "decision": decision,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
    }
    result["evaluation_sha256"] = payload_sha(result, "evaluation_sha256")
    return result


def evaluate(contract_path, ledger_dir):
    contract, anchor, rows = load_chain(contract_path, ledger_dir)
    if not rows:
        result = build_evaluation(contract, rows, [])
        write_json(Path(ledger_dir) / "EVALUATION.json", result)
        write_json(Path(ledger_dir) / "TRADES.json", [])
        return result

    trades = []
    for strategy in STRATEGIES:
        cycles = unique_cycles(rows, strategy)
        require(cycles, f"no cycles {strategy}")
        require(cycles[0]["signal_date"] == contract["first_eligible_signal_date"], f"first signal drift {strategy}")
        for i, cycle in enumerate(cycles):
            next_signal = cycles[i + 1]["signal_date"] if i + 1 < len(cycles) else None
            for pick in cycle["picks"]:
                trades.append(evaluate_trade(contract, rows, cycle, next_signal, pick["asset"]))

    result = build_evaluation(contract, rows, trades)
    write_json(Path(ledger_dir) / "TRADES.json", trades)
    write_json(Path(ledger_dir) / "EVALUATION.json", result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--ledger-dir", required=True)
    args = parser.parse_args()
    result = evaluate(args.contract, args.ledger_dir)
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
