from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import statistics
from bisect import bisect_right
from pathlib import Path
from typing import Any, Iterable, Sequence

from crypto_decision_lab.scripts.phase326_335_preregistration_common import (
    LOCKS,
    MAX_HYPOTHESIS_BUDGET,
    PROPOSED_NEW_FAMILY_ID,
    REQUIRED_PORTAL_HEADINGS,
    ROOT,
    TARGET_ID,
    base_payload,
    canonical_hash,
    fingerprint,
    money_brl,
    read_json,
    render_simple_portal,
    require_portal_headings,
    validate_phase,
    write_json,
    write_summary,
    write_text,
)
from crypto_decision_lab.scripts.phase316_325_negative_evidence_common import (
    dataset_path,
    finite_float,
    parse_junit,
    quantile,
    read_csv_gz_rows,
)
from crypto_decision_lab.scripts.phase301_305_evidence_v2_common import sha256_file

BASELINE_PHASE335_HEAD = "9c2f7899cf8dc38880268c44d22d4d3a2f063e82"
HOUR_MS = 60 * 60 * 1000
OUTER_FOLD_COUNT = 8
MINIMUM_TRAIN_HOURS = 365 * 24
OUTER_HOURS = 90 * 24
EMBARGO_HOURS = 24
OPERATING_THRESHOLDS = {"CONSERVATIVE": 0.60, "STRICT": 0.75}

FEATURE_BUNDLES: dict[str, tuple[str, ...]] = {
    "EXCHANGE_DISAGREEMENT_ONLY": (
        "spread_bps",
        "max_abs_deviation_bps",
        "provider_shortfall",
    ),
    "DERIVATIVES_DATA_QUALITY_ONLY": (
        "funding_missing_count",
        "funding_age_hours",
        "open_interest_missing",
        "open_interest_age_hours",
        "data_quality_risk_score",
    ),
    "COMBINED_DISAGREEMENT_AND_QUALITY": (
        "spread_bps",
        "max_abs_deviation_bps",
        "provider_shortfall",
        "funding_missing_count",
        "funding_age_hours",
        "open_interest_missing",
        "open_interest_age_hours",
        "data_quality_risk_score",
    ),
}

FEATURE_MATRIX_FIELDS = (
    "open_time_ms",
    "open_time_utc",
    "provider_count",
    "provider_shortfall",
    "median_close",
    "spread_bps",
    "max_abs_deviation_bps",
    "funding_source_count",
    "funding_missing_count",
    "funding_age_hours",
    "funding_dispersion_bps",
    "open_interest_missing",
    "open_interest_age_hours",
    "data_quality_risk_score",
    "realized_vol_24h",
    "return_24h",
)

TARGET_MATRIX_FIELDS = (
    "open_time_ms",
    "future_time_ms",
    "eligible_exchange_count",
    "future_sign_disagreement",
    "future_return_dispersion_bps",
)

PREDICTION_FIELDS = (
    "template_id",
    "fold",
    "open_time_ms",
    "label",
    "probability",
    "train_prevalence",
    "operating_threshold",
    "provider_count",
    "missingness_bucket",
    "volatility_regime",
)


def write_csv_gz(path: Path, rows: Sequence[dict[str, Any]], fieldnames: Sequence[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def read_csv_gz(path: Path) -> list[dict[str, str]]:
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def as_float(value: Any, default: float | None = None) -> float | None:
    result = finite_float(value)
    return default if result is None else result


def iso_from_ms(value: int) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def asof_value(
    timestamps: Sequence[int],
    values: Sequence[float],
    target: int,
) -> tuple[float | None, int | None]:
    if not timestamps:
        return None, None
    index = bisect_right(timestamps, target) - 1
    if index < 0:
        return None, None
    return float(values[index]), int(timestamps[index])


def sigmoid(value: float) -> float:
    if value >= 0:
        exp_value = math.exp(-min(value, 60.0))
        return 1.0 / (1.0 + exp_value)
    exp_value = math.exp(max(value, -60.0))
    return exp_value / (1.0 + exp_value)


def logit(probability: float) -> float:
    p = min(max(probability, 1e-6), 1.0 - 1e-6)
    return math.log(p / (1.0 - p))


def standardization_fit(rows: Sequence[dict[str, float]], feature_names: Sequence[str]) -> dict[str, tuple[float, float]]:
    output: dict[str, tuple[float, float]] = {}
    for name in feature_names:
        values = [float(row[name]) for row in rows]
        mean = statistics.fmean(values) if values else 0.0
        std = statistics.pstdev(values) if len(values) >= 2 else 1.0
        if not math.isfinite(std) or std <= 1e-12:
            std = 1.0
        output[name] = (mean, std)
    return output


def standardize(row: dict[str, float], names: Sequence[str], fitted: dict[str, tuple[float, float]]) -> list[float]:
    return [(float(row[name]) - fitted[name][0]) / fitted[name][1] for name in names]


def fit_logistic_regression(
    rows: Sequence[dict[str, float]],
    labels: Sequence[int],
    feature_names: Sequence[str],
    *,
    iterations: int = 30,
    learning_rate: float = 0.08,
    l2: float = 0.01,
) -> dict[str, Any]:
    fitted = standardization_fit(rows, feature_names)
    vectors = [standardize(row, feature_names, fitted) for row in rows]
    prevalence = statistics.fmean(labels) if labels else 0.5
    weights = [0.0] * len(feature_names)
    intercept = logit(prevalence)
    count = max(1, len(vectors))
    for _ in range(iterations):
        gradient = [0.0] * len(weights)
        intercept_gradient = 0.0
        for vector, label in zip(vectors, labels):
            score = intercept + sum(weight * value for weight, value in zip(weights, vector))
            error = sigmoid(score) - int(label)
            intercept_gradient += error
            for index, value in enumerate(vector):
                gradient[index] += error * value
        intercept -= learning_rate * intercept_gradient / count
        for index in range(len(weights)):
            weights[index] -= learning_rate * (gradient[index] / count + l2 * weights[index])
    return {
        "kind": "LOGISTIC_REGRESSION",
        "feature_names": list(feature_names),
        "standardization": {name: list(values) for name, values in fitted.items()},
        "weights": weights,
        "intercept": intercept,
    }


def fit_threshold_rule(
    rows: Sequence[dict[str, float]],
    labels: Sequence[int],
    feature_names: Sequence[str],
) -> dict[str, Any]:
    fitted = standardization_fit(rows, feature_names)
    prevalence = statistics.fmean(labels) if labels else 0.5
    return {
        "kind": "THRESHOLD_RULE",
        "feature_names": list(feature_names),
        "standardization": {name: list(values) for name, values in fitted.items()},
        "intercept": logit(prevalence),
    }


def predict_probability(model: dict[str, Any], row: dict[str, float]) -> float:
    fitted = {
        name: (float(values[0]), float(values[1]))
        for name, values in model["standardization"].items()
    }
    names = list(model["feature_names"])
    vector = standardize(row, names, fitted)
    if model["kind"] == "LOGISTIC_REGRESSION":
        score = float(model["intercept"]) + sum(
            float(weight) * value
            for weight, value in zip(model["weights"], vector)
        )
        return sigmoid(score)
    risk_score = statistics.fmean(vector) if vector else 0.0
    return sigmoid(float(model["intercept"]) + risk_score)


def brier_score(labels: Sequence[int], probabilities: Sequence[float]) -> float:
    if not labels:
        return 1.0
    return statistics.fmean((float(probability) - int(label)) ** 2 for label, probability in zip(labels, probabilities))


def average_precision(labels: Sequence[int], probabilities: Sequence[float]) -> float:
    positives = sum(int(value) for value in labels)
    if positives <= 0:
        return 0.0
    ranked = sorted(zip(probabilities, labels), key=lambda item: (-float(item[0]), -int(item[1])))
    true_positives = 0
    total = 0.0
    for index, (_, label) in enumerate(ranked, start=1):
        if int(label) == 1:
            true_positives += 1
            total += true_positives / index
    return total / positives


def expected_calibration_error(labels: Sequence[int], probabilities: Sequence[float], bins: int = 10) -> float:
    if not labels:
        return 1.0
    total = len(labels)
    error = 0.0
    for index in range(bins):
        left = index / bins
        right = (index + 1) / bins
        selected = [
            position
            for position, probability in enumerate(probabilities)
            if (left <= probability < right) or (index == bins - 1 and probability == 1.0)
        ]
        if not selected:
            continue
        observed = statistics.fmean(int(labels[position]) for position in selected)
        predicted = statistics.fmean(float(probabilities[position]) for position in selected)
        error += len(selected) / total * abs(observed - predicted)
    return error


def classification_metrics(
    labels: Sequence[int],
    probabilities: Sequence[float],
    null_probabilities: Sequence[float] | None = None,
) -> dict[str, Any]:
    if not labels:
        return {
            "sample_count": 0,
            "prevalence": 0.0,
            "brier": 1.0,
            "null_brier": 1.0,
            "brier_skill": 0.0,
            "pr_auc": 0.0,
            "pr_auc_improvement": 0.0,
            "expected_calibration_error": 1.0,
        }
    prevalence = statistics.fmean(int(value) for value in labels)
    null = list(null_probabilities) if null_probabilities is not None else [prevalence] * len(labels)
    model_brier = brier_score(labels, probabilities)
    null_brier = brier_score(labels, null)
    skill = 1.0 - model_brier / null_brier if null_brier > 0 else 0.0
    pr_auc = average_precision(labels, probabilities)
    return {
        "sample_count": len(labels),
        "prevalence": prevalence,
        "brier": model_brier,
        "null_brier": null_brier,
        "brier_skill": skill,
        "pr_auc": pr_auc,
        "pr_auc_improvement": pr_auc - prevalence,
        "expected_calibration_error": expected_calibration_error(labels, probabilities),
    }


def one_sided_positive_pvalue(values: Sequence[float]) -> float:
    sample = [float(value) for value in values if math.isfinite(float(value))]
    if not sample:
        return 1.0
    mean = statistics.fmean(sample)
    if len(sample) < 2:
        return 0.5 if mean > 0 else 1.0
    std = statistics.stdev(sample)
    if std <= 1e-15:
        return 0.0 if mean > 0 else 1.0
    z_score = mean / (std / math.sqrt(len(sample)))
    return 0.5 * math.erfc(z_score / math.sqrt(2.0))


def holm_bonferroni(pvalues: dict[str, float], alpha: float = 0.05) -> dict[str, Any]:
    ordered = sorted((float(value), key) for key, value in pvalues.items())
    rejected: list[str] = []
    adjusted: dict[str, float] = {}
    running = 0.0
    count = len(ordered)
    stop = False
    for rank, (pvalue, key) in enumerate(ordered, start=1):
        running = max(running, min(1.0, (count - rank + 1) * pvalue))
        adjusted[key] = running
        threshold = alpha / (count - rank + 1)
        if not stop and pvalue <= threshold:
            rejected.append(key)
        else:
            stop = True
    return {
        "method": "HOLM_BONFERRONI",
        "alpha": alpha,
        "adjusted_pvalues": adjusted,
        "rejected_ids": rejected,
    }


def walk_forward_folds(
    length: int,
    *,
    minimum_train_hours: int = MINIMUM_TRAIN_HOURS,
    outer_hours: int = OUTER_HOURS,
    embargo_hours: int = EMBARGO_HOURS,
    max_folds: int = OUTER_FOLD_COUNT,
) -> list[dict[str, int]]:
    folds: list[dict[str, int]] = []
    outer_start = minimum_train_hours + embargo_hours
    while outer_start + outer_hours <= length:
        train_end = outer_start - embargo_hours - 1
        train_start = max(0, train_end - minimum_train_hours + 1)
        folds.append(
            {
                "train_start": train_start,
                "train_end": train_end,
                "outer_start": outer_start,
                "outer_end": outer_start + outer_hours - 1,
                "embargo_hours": embargo_hours,
            }
        )
        outer_start += outer_hours
    return folds[-max_folds:]


def target_label(raw: dict[str, float | int], dispersion_threshold_bps: float) -> int:
    return int(
        int(raw["future_sign_disagreement"]) == 1
        or float(raw["future_return_dispersion_bps"]) > dispersion_threshold_bps
    )


def safe_numeric_feature_row(row: dict[str, str]) -> dict[str, float]:
    output: dict[str, float] = {}
    for names in FEATURE_BUNDLES.values():
        for name in names:
            value = as_float(row.get(name), 0.0)
            output[name] = float(value or 0.0)
    output["realized_vol_24h"] = float(as_float(row.get("realized_vol_24h"), 0.0) or 0.0)
    output["provider_count"] = float(as_float(row.get("provider_count"), 0.0) or 0.0)
    output["data_quality_risk_score"] = float(as_float(row.get("data_quality_risk_score"), 0.0) or 0.0)
    return output


def template_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item["template_id"]): dict(item) for item in payload.get("active_templates", [])}


def ensure_locks(payload: dict[str, Any]) -> None:
    locks = payload["locks"]
    assert locks["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert locks["action_status"] == "NO_ACTION_RESEARCH_ONLY"
    assert locks["decision_layer_allowed"] is False
    assert locks["canonical_data_writes"] == 0
    assert locks["position_size"] == 0
    assert locks["capital_used"] == 0
    assert locks["real_orders_created"] == 0


__all__ = [
    "BASELINE_PHASE335_HEAD",
    "EMBARGO_HOURS",
    "FEATURE_BUNDLES",
    "FEATURE_MATRIX_FIELDS",
    "HOUR_MS",
    "LOCKS",
    "MAX_HYPOTHESIS_BUDGET",
    "OPERATING_THRESHOLDS",
    "OUTER_FOLD_COUNT",
    "PREDICTION_FIELDS",
    "PROPOSED_NEW_FAMILY_ID",
    "REQUIRED_PORTAL_HEADINGS",
    "ROOT",
    "TARGET_ID",
    "TARGET_MATRIX_FIELDS",
    "as_float",
    "asof_value",
    "average_precision",
    "base_payload",
    "brier_score",
    "canonical_hash",
    "classification_metrics",
    "dataset_path",
    "ensure_locks",
    "expected_calibration_error",
    "fingerprint",
    "fit_logistic_regression",
    "fit_threshold_rule",
    "holm_bonferroni",
    "iso_from_ms",
    "money_brl",
    "one_sided_positive_pvalue",
    "parse_junit",
    "predict_probability",
    "quantile",
    "read_csv_gz",
    "read_csv_gz_rows",
    "read_json",
    "render_simple_portal",
    "require_portal_headings",
    "safe_numeric_feature_row",
    "sha256_file",
    "target_label",
    "template_map",
    "validate_phase",
    "walk_forward_folds",
    "write_csv_gz",
    "write_json",
    "write_summary",
    "write_text",
]
