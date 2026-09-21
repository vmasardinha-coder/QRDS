#!/usr/bin/env python3
"""Execute the preregistered Grammar 007 Focus/Pearson historical cases.

Scientific decisions are external and immutable. This module only performs the
mechanical target delivery, joins sealed dates, discovery-fitted z-scores,
Pearson effects, validation gate, and conditionally gated holdout read.
"""
from __future__ import annotations

import argparse
import base64
import json
import math
import statistics
import urllib.request
from datetime import date
from pathlib import Path
from typing import Callable

FAMILY = "XAGRAMMAR_728DC88D691B"
IPCA = "IPCA_CURRENT_YEAR_MEDIAN_REVISION"
SELIC = "SELIC_CURRENT_YEAR_END_MEDIAN_REVISION"
EXPECTED_CASES = [
    "G007_FOCUS_50_50_V1",
    "G007_FOCUS_IPCA_ONLY_V1",
    "G007_FOCUS_SELIC_ONLY_V1",
]


class ScientificIneligible(RuntimeError):
    """Expected fail-closed scientific ineligibility, never infrastructure red."""


def parse_ptbr_number(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value.replace(".", "").replace(",", "."))


def fetch_b3_ibov_year(year: int, route: dict) -> dict[str, float]:
    payload = dict(route["machine_payload"])
    payload["year"] = str(year)
    token = base64.b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()
    url = route["official_machine_surface_template"].format(base64_json=token)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 QRDS-Research/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as response:
        body = response.read()
    parsed = json.loads(body.decode("utf-8"))
    rows = parsed.get("results")
    if not isinstance(rows, list) or len(rows) != 31:
        raise RuntimeError(f"B3_INDEX_RESPONSE_CONTRACT_MISMATCH_{year}")
    out: dict[str, float] = {}
    for row in rows:
        day = int(row["day"])
        for month in range(1, 13):
            raw = row.get(f"rateValue{month}")
            value = parse_ptbr_number(raw)
            if value is None:
                continue
            try:
                d = date(year, month, day).isoformat()
            except ValueError:
                continue
            out[d] = value
    if len(out) < 100:
        raise RuntimeError(f"B3_INDEX_YEAR_TOO_SPARSE_{year}_{len(out)}")
    return out


def sample_pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 3:
        raise ScientificIneligible("PEARSON_INSUFFICIENT_PAIRED_OBSERVATIONS_FAIL_CLOSED")
    mx, my = statistics.mean(xs), statistics.mean(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    sx2 = sum(v * v for v in dx)
    sy2 = sum(v * v for v in dy)
    if sx2 == 0:
        raise ScientificIneligible("PEARSON_FEATURE_ZERO_VARIANCE_FAIL_CLOSED")
    if sy2 == 0:
        raise ScientificIneligible("PEARSON_TARGET_ZERO_VARIANCE_FAIL_CLOSED")
    return sum(a * b for a, b in zip(dx, dy)) / math.sqrt(sx2 * sy2)


def discovery_z_params(rows: list[dict], discovery_dates: set[str]) -> dict[str, dict[str, float]]:
    chosen = [r for r in rows if r["target_session_date"] in discovery_dates]
    if not chosen:
        raise RuntimeError("NO_DISCOVERY_FEATURE_ROWS")
    out = {}
    for component in (IPCA, SELIC):
        vals = [float(r[component]) for r in chosen]
        sd = statistics.stdev(vals)
        out[component] = {"mean": statistics.mean(vals), "sample_sd": sd, "n": len(vals)}
    return out


def scalar_feature(row: dict, case: dict, params: dict[str, dict[str, float]]) -> float:
    total = 0.0
    for name, key in (("IPCA", IPCA), ("SELIC", SELIC)):
        weight = float(case["weights"][name])
        if weight == 0.0:
            continue
        sd = params[key]["sample_sd"]
        if sd == 0:
            raise ScientificIneligible(f"ZSCORE_{name}_DISCOVERY_ZERO_VARIANCE_FAIL_CLOSED")
        z = (float(row[key]) - params[key]["mean"]) / sd
        total += weight * z
    return total


def target_returns_for_dates(target_dates: list[str], yearly_levels: dict[int, dict[str, float]]) -> dict[str, float]:
    levels = {}
    for year_map in yearly_levels.values():
        levels.update(year_map)
    ordered = sorted(levels)
    index = {d: i for i, d in enumerate(ordered)}
    out = {}
    for d in target_dates:
        if d not in index or index[d] == 0:
            raise RuntimeError(f"TARGET_DATE_OR_PREVIOUS_CLOSE_MISSING_{d}")
        prev = ordered[index[d] - 1]
        out[d] = levels[d] / levels[prev] - 1.0
    return out


def effect_for_partition(rows_by_date: dict[str, dict], dates: list[str], case: dict, params: dict, returns: dict[str, float]) -> tuple[float, int]:
    xs, ys = [], []
    for d in dates:
        row = rows_by_date.get(d)
        if row is None:
            raise RuntimeError(f"FROZEN_FEATURE_ROW_MISSING_{d}")
        if d not in returns:
            raise RuntimeError(f"FROZEN_TARGET_RETURN_MISSING_{d}")
        xs.append(scalar_feature(row, case, params))
        ys.append(returns[d])
    return sample_pearson(xs, ys), len(xs)


def same_sign(a: float, b: float) -> bool:
    return a != 0 and b != 0 and math.copysign(1.0, a) == math.copysign(1.0, b)


def not_started_partition() -> dict:
    return {"started": False, "pearson_r": None, "n": 0, "pass": False}


def execute(features: dict, partitions: dict, cases_auth: dict, stat_auth: dict, route: dict,
            fetch_year: Callable[[int, dict], dict[str, float]] = fetch_b3_ibov_year) -> dict:
    assert cases_auth["status"] == "FROZEN_BEFORE_FIRST_TARGET_READ"
    assert stat_auth["status"] == "FROZEN_BEFORE_FIRST_TARGET_READ"
    assert stat_auth["effect_statistic"]["name"] == "PEARSON_PRODUCT_MOMENT_CORRELATION"
    assert partitions["partitions_frozen"] is True and partitions["embargo_sessions"] == 60
    assert route["status"] == "MECHANICAL_SOURCE_ROUTE_CORRECTED_TARGET_IDENTITY_UNCHANGED"
    assert route["scientific_changes"] == {
        "target_identity_changed": False, "feature_changed": False, "partition_changed": False,
        "pearson_changed": False, "case_weights_changed": False, "validation_rule_changed": False,
        "holdout_rule_changed": False,
    }
    cases = sorted(cases_auth["cases"], key=lambda x: x["execution_order"])
    assert [x["case_id"] for x in cases] == EXPECTED_CASES

    rows = features["families"][FAMILY]["rows"]
    rows_by_date = {r["target_session_date"]: r for r in rows}
    pd = partitions["candidate_partition_dates"]
    discovery_dates = list(pd["discovery"])
    validation_dates = list(pd["validation"])
    holdout_dates = list(pd["holdout"])
    params = discovery_z_params(rows, set(discovery_dates))

    pre_holdout_levels = {2024: fetch_year(2024, route), 2025: fetch_year(2025, route)}
    pre_returns = target_returns_for_dates(discovery_dates + validation_dates, pre_holdout_levels)

    results = []
    any_2026_fetch = False
    for case in cases:
        base = {
            "case_id": case["case_id"],
            "execution_order": case["execution_order"],
            "discovery": not_started_partition(),
            "validation": not_started_partition(),
            "holdout": {"started": False, "target_year_2026_fetched_for_this_case": False, "pearson_r": None, "n": 0, "pass": None},
            "ineligibility_reason": None,
            "terminal_status": None,
        }
        try:
            rd, nd = effect_for_partition(rows_by_date, discovery_dates, case, params, pre_returns)
        except ScientificIneligible as exc:
            base["discovery"].update({"started": True, "n": len(discovery_dates), "ineligible": True})
            base["ineligibility_reason"] = str(exc)
            base["terminal_status"] = "REJECTED_DISCOVERY_NO_RETUNE"
            results.append(base)
            continue
        base["discovery"] = {"started": True, "pearson_r": rd, "n": nd, "pass": True}

        try:
            rv, nv = effect_for_partition(rows_by_date, validation_dates, case, params, pre_returns)
        except ScientificIneligible as exc:
            base["validation"].update({"started": True, "n": len(validation_dates), "ineligible": True})
            base["ineligibility_reason"] = str(exc)
            base["terminal_status"] = "REJECTED_VALIDATION_NO_RETUNE"
            results.append(base)
            continue

        validation_pass = same_sign(rd, rv) and abs(rv) >= 0.50 * abs(rd)
        base["validation"] = {"started": True, "pearson_r": rv, "n": nv, "same_sign": same_sign(rd, rv), "magnitude_floor": 0.50 * abs(rd), "pass": validation_pass}
        base["terminal_status"] = "REJECTED_VALIDATION_NO_RETUNE"
        if not validation_pass:
            results.append(base)
            continue

        holdout_levels = {2026: fetch_year(2026, route)}
        any_2026_fetch = True
        holdout_returns = target_returns_for_dates(holdout_dates, holdout_levels)
        try:
            rh, nh = effect_for_partition(rows_by_date, holdout_dates, case, params, holdout_returns)
        except ScientificIneligible as exc:
            base["holdout"] = {"started": True, "target_year_2026_fetched_for_this_case": True, "pearson_r": None, "n": len(holdout_dates), "pass": False, "ineligible": True}
            base["ineligibility_reason"] = str(exc)
            base["terminal_status"] = "REJECTED_HOLDOUT_NO_RETUNE"
            results.append(base)
            continue

        hp = same_sign(rd, rh) and abs(rh) >= 0.50 * abs(rd)
        base["holdout"] = {"started": True, "target_year_2026_fetched_for_this_case": True, "pearson_r": rh, "n": nh, "same_sign": same_sign(rd, rh), "magnitude_floor": 0.50 * abs(rd), "pass": hp}
        base["terminal_status"] = "SURVIVOR_TO_SEPARATE_BLINDED_PROSPECTIVE_ZERO_RETROACTIVE_CREDIT" if hp else "REJECTED_HOLDOUT_NO_RETUNE"
        results.append(base)

    survivors = [r["case_id"] for r in results if r["terminal_status"].startswith("SURVIVOR_")]
    status = "HISTORICAL_EVALUATION_COMPLETE_SURVIVOR_EXISTS" if survivors else "HISTORICAL_EVALUATION_COMPLETE_NO_SURVIVOR"
    return {
        "schema": "qrds.factory.grammar_007.pearson_historical_eval.v1",
        "status": status,
        "target": cases_auth["target"],
        "target_source": {"provider": route["provider"], "route_status": route["status"], "pre_holdout_years_fetched": [2024, 2025], "holdout_year_2026_ever_fetched": any_2026_fetch, "raw_provider_payload_persisted": False},
        "partition_contract": partitions["partition_contract"],
        "embargo_sessions": partitions["embargo_sessions"],
        "standardization": {"method": "ZSCORE", "fit_partition": "DISCOVERY_ONLY", "parameters": params, "validation_holdout_refit": False},
        "effect_statistic": "PEARSON_PRODUCT_MOMENT_CORRELATION",
        "zero_variance_policy": "INELIGIBLE_FAIL_CLOSED_ZERO_CREDIT_NOT_INFRASTRUCTURE_ERROR",
        "cases": results,
        "survivors": survivors,
        "scientific_credit": 0,
        "historical_backfill_credit": 0,
        "prospective_credit": 0,
        "next_gate": "SEPARATE_BLINDED_PROSPECTIVE_ZERO_RETROACTIVE_CREDIT" if survivors else "FACTORY_007_CLOSE_NO_SURVIVOR",
        "safety": {
            "RESEARCH_ONLY": True, "SHADOW_ONLY": True, "NOT_APPROVED": True,
            "ENGINE_FEED": False, "ORDERS": 0, "REAL_CAPITAL": 0,
            "NO_RETUNE": True, "NO_BACKFILL": True, "NO_COUNTER_RESET": True,
            "FAIL_CLOSED": True,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", type=Path, required=True)
    ap.add_argument("--partitions", type=Path, required=True)
    ap.add_argument("--cases", type=Path, required=True)
    ap.add_argument("--stat-auth", type=Path, required=True)
    ap.add_argument("--source-route", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    load = lambda p: json.loads(p.read_text(encoding="utf-8"))
    result = execute(load(a.features), load(a.partitions), load(a.cases), load(a.stat_auth), load(a.source_route))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "cases": [{"case_id": x["case_id"], "validation_pass": x["validation"]["pass"], "holdout_started": x["holdout"]["started"], "terminal_status": x["terminal_status"], "ineligibility_reason": x["ineligibility_reason"]} for x in result["cases"]], "survivors": result["survivors"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
