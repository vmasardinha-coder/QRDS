#!/usr/bin/env python3
"""Survivorship-corrected alpha audit for GATE BTC.

Research-only sidecar. The audit consumes a separately validated point-in-time
weekly basket pack; it never changes V2A selection, source order, parameters,
or operational state.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

BASKETS = ("UNFILTERED_PIT", "SELECTED_MODERADA_PIT", "SELECTED_ULTRA_PIT")
REQUIRED_COLUMNS = {
    "week_end", "basket", "basket_return", "btc_return", "regime",
    "covered_eligible_assets", "total_eligible_assets",
}
USER_BASELINE = {
    "status": "UNVERIFIED_USER_EXPLORATORY_BASELINE",
    "frequency": "weekly",
    "UNFILTERED_CURRENT_SURVIVORS": {"alpha": 0.0031, "beta": 1.00, "r2": 0.61},
    "SELECTED_MODERADA_CURRENT_SURVIVORS": {"alpha": 0.0128, "beta": 1.08, "r2": 0.49},
    "SELECTED_ULTRA_CURRENT_SURVIVORS": {"alpha": 0.0088, "beta": 1.02, "r2": 0.54},
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def safety_payload() -> dict[str, Any]:
    return {
        "role": "SURVIVORSHIP_ALPHA_AUDIT_ONLY",
        "engine_feed": False,
        "feeds_frozen_engine": False,
        "strategy_inputs_changed": False,
        "source_substitution_performed": False,
        "methodology_changes": 0,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }


def blocked_report(reason: str = "validated point-in-time weekly basket pack not supplied") -> dict[str, Any]:
    return {
        "schema": "gate_btc.survivorship_corrected_alpha_audit.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED_INSUFFICIENT_VALIDATED_PIT_SERIES",
        "user_exploratory_baseline": USER_BASELINE,
        "primary_baskets": list(BASKETS),
        "regression": "r_basket_week = alpha + beta * r_BTC_week",
        "hac_newey_west_lag_weeks": 4,
        "blockers": [reason],
        "required_upstream_proof": [
            "point-in-time universe membership by week",
            "Moderada and Ultra selection recomputed point-in-time on the expanded universe",
            "validated terminal-loss handling for confirmed economic deaths",
            "no synthetic terminal loss for provisional/unresolved assets",
            "same valid weekly calendar for all three baskets",
        ],
        **safety_payload(),
    }


def validate_provenance(payload: dict[str, Any]) -> None:
    require(payload.get("schema") == "gate_btc.survivorship_alpha_input_provenance.v1", "unexpected alpha provenance schema")
    require(payload.get("point_in_time_universe") is True, "point-in-time universe proof missing")
    require(payload.get("point_in_time_selection_recomputed") is True, "selected baskets were not recomputed point-in-time")
    require(payload.get("current_survivor_only") is False, "current-survivor-only input is prohibited")
    require(payload.get("confirmed_terminal_loss_policy_validated") is True, "confirmed-death terminal-loss policy not validated")
    require(payload.get("provisional_terminal_returns_synthesized") is False, "synthetic provisional terminal returns are prohibited")
    require(payload.get("engine_feed") is False, "alpha audit must not feed the engine")
    require(payload.get("methodology_changes") == 0, "alpha audit provenance reports methodology change")
    require(payload.get("orders_generated") == 0 and payload.get("real_capital_used") == 0, "orders/capital boundary changed")


def read_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        require(REQUIRED_COLUMNS.issubset(set(reader.fieldnames or [])), "weekly alpha CSV missing required columns")
        rows = []
        for raw in reader:
            basket = str(raw["basket"]).strip()
            require(basket in BASKETS, f"unexpected basket: {basket}")
            week = date.fromisoformat(str(raw["week_end"]).strip()).isoformat()
            covered = int(raw["covered_eligible_assets"])
            total = int(raw["total_eligible_assets"])
            require(total > 0 and 0 <= covered <= total, f"invalid coverage on {week}")
            rows.append({
                "week_end": week,
                "basket": basket,
                "basket_return": float(raw["basket_return"]),
                "btc_return": float(raw["btc_return"]),
                "regime": str(raw["regime"]).strip().upper() or "UNSPECIFIED",
                "covered_eligible_assets": covered,
                "total_eligible_assets": total,
                "coverage_ratio": covered / total,
            })
    return rows


def validate_calendar(rows: list[dict[str, Any]]) -> list[str]:
    by_basket: dict[str, dict[str, dict[str, Any]]] = {basket: {} for basket in BASKETS}
    for row in rows:
        target = by_basket[row["basket"]]
        require(row["week_end"] not in target, f"duplicate basket/week: {row['basket']} {row['week_end']}")
        target[row["week_end"]] = row
    calendars = [set(by_basket[basket]) for basket in BASKETS]
    require(all(calendars), "all three PIT baskets require observations")
    require(calendars[0] == calendars[1] == calendars[2], "three baskets do not share the same weekly calendar")
    weeks = sorted(calendars[0])
    for week in weeks:
        reference = by_basket[BASKETS[0]][week]
        for basket in BASKETS[1:]:
            row = by_basket[basket][week]
            require(math.isclose(row["btc_return"], reference["btc_return"], rel_tol=0.0, abs_tol=1e-15), f"BTC return differs across baskets on {week}")
            require(row["regime"] == reference["regime"], f"regime differs across baskets on {week}")
            require(row["covered_eligible_assets"] == reference["covered_eligible_assets"], f"coverage differs across baskets on {week}")
            require(row["total_eligible_assets"] == reference["total_eligible_assets"], f"eligible denominator differs across baskets on {week}")
    return weeks


def matmul2(left: list[list[float]], right: list[list[float]]) -> list[list[float]]:
    return [[sum(left[i][k] * right[k][j] for k in range(2)) for j in range(2)] for i in range(2)]


def fit_regression(rows: list[dict[str, Any]], hac_lag: int = 4) -> dict[str, Any]:
    n = len(rows)
    require(n >= 3, "at least 3 weekly observations required")
    x = [float(row["btc_return"]) for row in rows]
    y = [float(row["basket_return"]) for row in rows]
    sx, sy = sum(x), sum(y)
    sxx = sum(v * v for v in x)
    sxy = sum(a * b for a, b in zip(x, y))
    det = n * sxx - sx * sx
    require(abs(det) > 1e-18, "BTC regressor is singular")
    alpha = (sy * sxx - sx * sxy) / det
    beta = (n * sxy - sx * sy) / det
    residuals = [yy - alpha - beta * xx for xx, yy in zip(x, y)]
    mean_y = sy / n
    rss = sum(u * u for u in residuals)
    tss = sum((yy - mean_y) ** 2 for yy in y)
    r2 = 1.0 - rss / tss if tss > 0 else None

    inv = [[sxx / det, -sx / det], [-sx / det, n / det]]
    meat = [[0.0, 0.0], [0.0, 0.0]]
    regressors = [(1.0, xx) for xx in x]
    for t in range(n):
        u = residuals[t]
        z = regressors[t]
        for i in range(2):
            for j in range(2):
                meat[i][j] += u * u * z[i] * z[j]
    effective_lag = min(max(int(hac_lag), 0), n - 1)
    for lag in range(1, effective_lag + 1):
        weight = 1.0 - lag / (effective_lag + 1.0)
        for t in range(lag, n):
            uprod = residuals[t] * residuals[t - lag]
            zt, zl = regressors[t], regressors[t - lag]
            for i in range(2):
                for j in range(2):
                    meat[i][j] += weight * uprod * (zt[i] * zl[j] + zl[i] * zt[j])
    covariance = matmul2(matmul2(inv, meat), inv)
    variance_alpha = max(covariance[0][0], 0.0)
    alpha_se = math.sqrt(variance_alpha)
    if alpha_se > 0:
        t_stat = alpha / alpha_se
        p_value = math.erfc(abs(t_stat) / math.sqrt(2.0))
        ci95 = [alpha - 1.96 * alpha_se, alpha + 1.96 * alpha_se]
    else:
        t_stat = None
        p_value = None
        ci95 = [alpha, alpha]
    return {
        "alpha_weekly": alpha,
        "beta": beta,
        "r2": r2,
        "weeks": n,
        "hac_newey_west_lag_weeks": effective_lag,
        "alpha_hac_se": alpha_se,
        "alpha_hac_t_stat": t_stat,
        "alpha_hac_p_value_asymptotic_normal": p_value,
        "alpha_hac_ci95": ci95,
        "alpha_statistically_positive_5pct": bool(p_value is not None and p_value < 0.05 and ci95[0] > 0),
    }


def basket_results(rows: list[dict[str, Any]], hac_lag: int) -> dict[str, Any]:
    by_basket = {basket: [row for row in rows if row["basket"] == basket] for basket in BASKETS}
    fits = {basket: fit_regression(by_basket[basket], hac_lag) for basket in BASKETS}
    base_alpha = fits["UNFILTERED_PIT"]["alpha_weekly"]
    fits["SELECTED_MODERADA_PIT"]["delta_alpha_vs_unfiltered_weekly"] = fits["SELECTED_MODERADA_PIT"]["alpha_weekly"] - base_alpha
    fits["SELECTED_ULTRA_PIT"]["delta_alpha_vs_unfiltered_weekly"] = fits["SELECTED_ULTRA_PIT"]["alpha_weekly"] - base_alpha
    fits["UNFILTERED_PIT"]["delta_alpha_vs_unfiltered_weekly"] = 0.0
    return fits


def decompositions(rows: list[dict[str, Any]], hac_lag: int) -> dict[str, Any]:
    reference = [row for row in rows if row["basket"] == "UNFILTERED_PIT"]
    regimes = sorted({row["regime"] for row in reference})
    years = sorted({row["week_end"][:4] for row in reference})
    output: dict[str, Any] = {"by_regime": {}, "by_calendar_year": {}}
    for label, values, key in (
        ("by_regime", regimes, lambda row, value: row["regime"] == value),
        ("by_calendar_year", years, lambda row, value: row["week_end"].startswith(value + "-")),
    ):
        for value in values:
            subset = [row for row in rows if key(row, value)]
            weeks = len([row for row in subset if row["basket"] == "UNFILTERED_PIT"])
            output[label][value] = basket_results(subset, hac_lag) if weeks >= 3 else {"status": "INSUFFICIENT_WEEKS", "weeks": weeks}
    return output


def run(rows: list[dict[str, Any]], provenance: dict[str, Any], hac_lag: int = 4) -> dict[str, Any]:
    validate_provenance(provenance)
    weeks = validate_calendar(rows)
    if len(weeks) < 3:
        return blocked_report("fewer than 3 common validated weekly observations")
    reference = [row for row in rows if row["basket"] == "UNFILTERED_PIT"]
    coverage = [row["coverage_ratio"] for row in reference]
    fits = basket_results(rows, hac_lag)
    remaining_censoring = bool(provenance.get("provisional_or_unresolved_censoring_remaining", True))
    full_coverage = min(coverage) >= 1.0 - 1e-15 and not remaining_censoring
    status = "PASS_FULL_COVERAGE_AUDIT" if full_coverage else "PARTIAL_COVERAGE_RESEARCH_ONLY"
    return {
        "schema": "gate_btc.survivorship_corrected_alpha_audit.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "regression": "r_basket_week = alpha + beta * r_BTC_week",
        "user_exploratory_baseline": USER_BASELINE,
        "coverage": {
            "common_weeks": len(weeks),
            "first_week": weeks[0],
            "last_week": weeks[-1],
            "min_ratio": min(coverage),
            "mean_ratio": sum(coverage) / len(coverage),
            "max_eligible_assets": max(row["total_eligible_assets"] for row in reference),
            "provisional_or_unresolved_censoring_remaining": remaining_censoring,
        },
        "results": fits,
        "decomposition": decompositions(rows, hac_lag),
        "interpretation_guard": "Selection alpha is considered structurally supported only if corrected selected alpha remains above UNFILTERED_PIT and is not confined to one regime/window; HAC inference is supplemental, not an operational gate.",
        "provenance": provenance,
        **safety_payload(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weekly-csv", type=Path)
    parser.add_argument("--provenance-json", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hac-lag", type=int, default=4)
    args = parser.parse_args()
    require(os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").strip().lower() in {"1", "true", "yes", "on"}, "GATE_BTC_RESEARCH_ONLY must remain true")
    if args.weekly_csv is None or args.provenance_json is None:
        payload = blocked_report()
    else:
        provenance = json.loads(args.provenance_json.read_text(encoding="utf-8-sig"))
        payload = run(read_rows(args.weekly_csv), provenance, max(0, int(args.hac_lag)))
    atomic_json(args.output, payload)
    print(json.dumps({
        "status": payload["status"],
        "engine_feed": False,
        "methodology_changes": 0,
        "orders_generated": 0,
        "real_capital_used": 0,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
