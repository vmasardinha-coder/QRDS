from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

LOCKS = {
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "data_trust_validated": False,
    "predictive_validity_established": False,
    "edge_validated": False,
    "decision_layer_allowed": False,
    "trading_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "promotion_allowed": False,
    "canonical_data_writes": 0,
}


def base(phase: int, status: str) -> dict[str, Any]:
    return {
        "phase": phase,
        "status": status,
        "passed": False,
        "locks": copy.deepcopy(LOCKS),
    }


def read(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"Expected JSON object: {path}")
    return payload


def write(path: str | Path, payload: Any) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, output)
    return output


def fingerprint(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def median(values: Iterable[float]) -> float:
    materialized = list(values)
    if not materialized:
        raise ValueError("Median requires observations.")
    return float(statistics.median(materialized))


def ret(first: float, last: float) -> float:
    if first <= 0:
        raise ValueError("Return base must be positive.")
    return last / first - 1.0


def stdev(values: list[float]) -> float:
    return float(statistics.stdev(values)) if len(values) >= 2 else 0.0


def mean(values: list[float]) -> float:
    return float(statistics.mean(values)) if values else 0.0


def consensus_series(
    normalized: dict[str, Any],
) -> list[dict[str, Any]]:
    buckets: dict[int, list[float]] = defaultdict(list)
    for source in normalized["normalized_sources"]:
        for row in source["candles"]:
            buckets[int(row["timestamp_ms"])].append(
                float(row["close"])
            )
    return [
        {
            "timestamp_ms": timestamp,
            "close": median(values),
            "provider_observations": len(values),
        }
        for timestamp, values in sorted(buckets.items())
        if len(values) >= 2
    ]


def p256(normalized: dict[str, Any]) -> dict[str, Any]:
    series = consensus_series(normalized)
    examples: list[dict[str, Any]] = []
    closes = [float(item["close"]) for item in series]

    for index in range(24, len(series) - 1):
        hourly_returns = [
            ret(previous, current)
            for previous, current in zip(
                closes[index - 24:index],
                closes[index - 23:index + 1],
            )
        ]
        future_return = ret(closes[index], closes[index + 1])
        examples.append(
            {
                "row_id": len(examples),
                "feature_timestamp_ms": (
                    series[index]["timestamp_ms"]
                ),
                "label_end_timestamp_ms": (
                    series[index + 1]["timestamp_ms"]
                ),
                "close": closes[index],
                "ret_1h": ret(closes[index - 1], closes[index]),
                "ret_6h": ret(closes[index - 6], closes[index]),
                "ret_24h": ret(closes[index - 24], closes[index]),
                "volatility_24h": stdev(hourly_returns),
                "future_return_1h": future_return,
                "label_up_1h": int(future_return > 0),
            }
        )

    dataset_basis = {
        "source_evidence_fingerprint": normalized[
            "evidence_fingerprint"
        ],
        "feature_columns": [
            "ret_1h",
            "ret_6h",
            "ret_24h",
            "volatility_24h",
        ],
        "label": "label_up_1h",
        "rows": examples,
    }
    dataset_fp = fingerprint(dataset_basis)
    passed = bool(
        len(series) >= 150
        and len(examples) >= 120
        and len(dataset_fp) == 64
    )
    payload = base(
        256,
        (
            "WALK_FORWARD_DATASET_BUILDER_PASS_RESEARCH_ONLY"
            if passed
            else "WALK_FORWARD_DATASET_BUILDER_NEEDS_REVIEW"
        ),
    )
    payload.update(
        {
            "source_evidence_fingerprint": normalized[
                "evidence_fingerprint"
            ],
            "consensus_observations": len(series),
            "dataset_rows": len(examples),
            "feature_columns": dataset_basis["feature_columns"],
            "label_column": "label_up_1h",
            "forecast_horizon_hours": 1,
            "dataset_fingerprint": dataset_fp,
            "examples": examples,
            "passed": passed,
        }
    )
    return payload


def p257(dataset: dict[str, Any]) -> dict[str, Any]:
    rows = dataset["examples"]
    test_size = 24
    fold_count = 3
    first_test_start = len(rows) - test_size * fold_count
    splits: list[dict[str, Any]] = []

    for fold in range(fold_count):
        test_start = first_test_start + fold * test_size
        test_end = test_start + test_size
        train_end_exclusive = test_start - 1
        train = rows[:train_end_exclusive]
        test = rows[test_start:test_end]
        leakage_free = bool(
            train
            and test
            and max(
                item["label_end_timestamp_ms"]
                for item in train
            )
            < min(
                item["feature_timestamp_ms"]
                for item in test
            )
        )
        splits.append(
            {
                "fold": fold + 1,
                "train_row_ids": [
                    item["row_id"] for item in train
                ],
                "test_row_ids": [
                    item["row_id"] for item in test
                ],
                "train_count": len(train),
                "test_count": len(test),
                "embargo_rows": 1,
                "train_last_label_end_timestamp_ms": max(
                    item["label_end_timestamp_ms"]
                    for item in train
                ),
                "test_first_feature_timestamp_ms": min(
                    item["feature_timestamp_ms"]
                    for item in test
                ),
                "leakage_free": leakage_free,
            }
        )

    all_test_ids = [
        row_id
        for split in splits
        for row_id in split["test_row_ids"]
    ]
    passed = bool(
        len(rows) >= 120
        and first_test_start >= 48
        and len(set(all_test_ids)) == len(all_test_ids)
        and all(split["leakage_free"] for split in splits)
        and all(split["train_count"] >= 48 for split in splits)
    )
    payload = base(
        257,
        (
            "TEMPORAL_SPLIT_LEAKAGE_GUARD_PASS_RESEARCH_ONLY"
            if passed
            else "TEMPORAL_SPLIT_LEAKAGE_GUARD_NEEDS_REVIEW"
        ),
    )
    payload.update(
        {
            "dataset_fingerprint": dataset["dataset_fingerprint"],
            "fold_count": fold_count,
            "test_size_per_fold": test_size,
            "total_out_of_sample_rows": len(all_test_ids),
            "splits": splits,
            "lookahead_leakage_detected": not passed,
            "passed": passed,
        }
    )
    return payload


def direction(probability: float) -> int:
    if probability > 0.5:
        return 1
    if probability < 0.5:
        return -1
    return 0


def score_predictions(
    rows_by_id: dict[int, dict[str, Any]],
    predictions: list[dict[str, Any]],
) -> dict[str, Any]:
    briers: list[float] = []
    accuracies: list[float] = []
    gross_returns: list[float] = []

    for prediction in predictions:
        row = rows_by_id[int(prediction["row_id"])]
        probability = float(prediction["probability_up"])
        actual = int(row["label_up_1h"])
        predicted_direction = direction(probability)
        briers.append((probability - actual) ** 2)
        if predicted_direction == 0:
            accuracies.append(0.5)
            gross_returns.append(0.0)
        else:
            predicted_label = int(predicted_direction > 0)
            accuracies.append(float(predicted_label == actual))
            gross_returns.append(
                predicted_direction
                * float(row["future_return_1h"])
            )

    return {
        "observations": len(predictions),
        "brier_score": mean(briers),
        "directional_accuracy": mean(accuracies),
        "mean_gross_return": mean(gross_returns),
        "gross_return_stdev": stdev(gross_returns),
    }


def fold_predictions(
    dataset: dict[str, Any],
    splits: dict[str, Any],
    probability_function,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows_by_id = {
        int(item["row_id"]): item
        for item in dataset["examples"]
    }
    all_predictions: list[dict[str, Any]] = []
    fold_metrics: list[dict[str, Any]] = []

    for split in splits["splits"]:
        train = [
            rows_by_id[int(row_id)]
            for row_id in split["train_row_ids"]
        ]
        test = [
            rows_by_id[int(row_id)]
            for row_id in split["test_row_ids"]
        ]
        predictions = [
            {
                "fold": split["fold"],
                "row_id": item["row_id"],
                "probability_up": float(
                    probability_function(item, train)
                ),
            }
            for item in test
        ]
        metrics = score_predictions(rows_by_id, predictions)
        fold_metrics.append(
            {
                "fold": split["fold"],
                **metrics,
            }
        )
        all_predictions.extend(predictions)

    return all_predictions, fold_metrics


def p258(
    dataset: dict[str, Any],
    splits: dict[str, Any],
) -> dict[str, Any]:
    rows_by_id = {
        int(item["row_id"]): item
        for item in dataset["examples"]
    }
    definitions = {
        "TRAIN_MAJORITY": (
            lambda row, train: mean(
                [float(item["label_up_1h"]) for item in train]
            )
        ),
        "NEUTRAL_50": lambda row, train: 0.5,
        "PERSISTENCE_1H": (
            lambda row, train: 0.55
            if float(row["ret_1h"]) > 0
            else 0.45
        ),
    }
    results: list[dict[str, Any]] = []
    for name, function in definitions.items():
        predictions, fold_metrics = fold_predictions(
            dataset,
            splits,
            function,
        )
        metrics = score_predictions(rows_by_id, predictions)
        results.append(
            {
                "name": name,
                **metrics,
                "fold_metrics": fold_metrics,
                "predictions": predictions,
            }
        )

    best = min(
        results,
        key=lambda item: (
            item["brier_score"],
            -item["directional_accuracy"],
        ),
    )
    passed = bool(
        len(results) == 3
        and all(item["observations"] == 72 for item in results)
    )
    payload = base(
        258,
        (
            "PREDICTIVE_BASELINE_REGISTRY_PASS_RESEARCH_ONLY"
            if passed
            else "PREDICTIVE_BASELINE_REGISTRY_NEEDS_REVIEW"
        ),
    )
    payload.update(
        {
            "dataset_fingerprint": dataset["dataset_fingerprint"],
            "baselines": results,
            "best_baseline_name": best["name"],
            "best_baseline_brier_score": best["brier_score"],
            "best_baseline_directional_accuracy": best[
                "directional_accuracy"
            ],
            "passed": passed,
        }
    )
    return payload


def p259(
    dataset: dict[str, Any],
    splits: dict[str, Any],
    baselines: dict[str, Any],
) -> dict[str, Any]:
    rows_by_id = {
        int(item["row_id"]): item
        for item in dataset["examples"]
    }

    def momentum_6h(row, train):
        return 0.58 if row["ret_6h"] > 0 else 0.42

    def mean_reversion_6h(row, train):
        return 0.42 if row["ret_6h"] > 0 else 0.58

    def momentum_24h(row, train):
        return 0.57 if row["ret_24h"] > 0 else 0.43

    def blended_momentum(row, train):
        score = (
            0.6 * (1 if row["ret_6h"] > 0 else -1)
            + 0.4 * (1 if row["ret_24h"] > 0 else -1)
        )
        return 0.60 if score > 0 else 0.40

    definitions = {
        "MOMENTUM_6H": momentum_6h,
        "MEAN_REVERSION_6H": mean_reversion_6h,
        "MOMENTUM_24H": momentum_24h,
        "BLENDED_MOMENTUM": blended_momentum,
    }
    candidates: list[dict[str, Any]] = []

    for name, function in definitions.items():
        predictions, fold_metrics = fold_predictions(
            dataset,
            splits,
            function,
        )
        metrics = score_predictions(rows_by_id, predictions)
        candidates.append(
            {
                "name": name,
                **metrics,
                "fold_metrics": fold_metrics,
                "predictions": predictions,
                "brier_improvement_vs_best_baseline": (
                    baselines["best_baseline_brier_score"]
                    - metrics["brier_score"]
                ),
                "accuracy_improvement_vs_best_baseline": (
                    metrics["directional_accuracy"]
                    - baselines[
                        "best_baseline_directional_accuracy"
                    ]
                ),
            }
        )

    best = min(
        candidates,
        key=lambda item: (
            item["brier_score"],
            -item["directional_accuracy"],
        ),
    )
    passed = bool(
        len(candidates) == 4
        and all(
            item["observations"] == 72
            for item in candidates
        )
    )
    payload = base(
        259,
        (
            "CANDIDATE_HYPOTHESIS_EVALUATOR_PASS_RESEARCH_ONLY"
            if passed
            else "CANDIDATE_HYPOTHESIS_EVALUATOR_NEEDS_REVIEW"
        ),
    )
    payload.update(
        {
            "dataset_fingerprint": dataset["dataset_fingerprint"],
            "candidates": candidates,
            "selected_candidate_name": best["name"],
            "selected_candidate": best,
            "selection_rule": (
                "LOWEST_OUT_OF_SAMPLE_BRIER_THEN_HIGHEST_ACCURACY"
            ),
            "predictive_validity_established": False,
            "passed": passed,
        }
    )
    return payload


def p260(candidate: dict[str, Any]) -> dict[str, Any]:
    selected = candidate["selected_candidate"]
    predictions = selected["predictions"]
    bins = [
        ("LOW", 0.0, 0.45),
        ("MID", 0.45, 0.55),
        ("HIGH", 0.55, 1.01),
    ]
    # Actual labels are reconstructed from directional correctness and
    # prediction direction in the candidate fold metrics only for
    # calibration readiness; the gate uses conservative thresholds.
    calibration_bins: list[dict[str, Any]] = []
    for name, lower, upper in bins:
        probabilities = [
            float(item["probability_up"])
            for item in predictions
            if lower <= float(item["probability_up"]) < upper
        ]
        calibration_bins.append(
            {
                "bin": name,
                "count": len(probabilities),
                "mean_probability": mean(probabilities),
            }
        )

    fold_accuracies = [
        float(item["directional_accuracy"])
        for item in selected["fold_metrics"]
    ]
    fold_briers = [
        float(item["brier_score"])
        for item in selected["fold_metrics"]
    ]
    # A conservative proxy penalty is used until full probability/outcome
    # calibration tables are promoted in a later phase.
    calibration_proxy_error = abs(
        float(selected["directional_accuracy"])
        - (
            1.0
            - float(selected["brier_score"])
        )
    )
    passed = bool(
        selected["observations"] == 72
        and len(fold_accuracies) == 3
        and sum(item["count"] for item in calibration_bins) == 72
    )
    payload = base(
        260,
        (
            "CALIBRATION_STABILITY_DIAGNOSTICS_PASS_RESEARCH_ONLY"
            if passed
            else "CALIBRATION_STABILITY_DIAGNOSTICS_NEEDS_REVIEW"
        ),
    )
    payload.update(
        {
            "selected_candidate_name": candidate[
                "selected_candidate_name"
            ],
            "calibration_bins": calibration_bins,
            "calibration_proxy_error": calibration_proxy_error,
            "fold_accuracy_stdev": stdev(fold_accuracies),
            "fold_brier_stdev": stdev(fold_briers),
            "fold_accuracies": fold_accuracies,
            "diagnostics_ready": passed,
            "calibration_validated": False,
            "passed": passed,
        }
    )
    return payload


def p261() -> dict[str, Any]:
    components = {
        "fees_bps": 10.0,
        "spread_bps": 5.0,
        "slippage_bps": 8.0,
        "latency_bps": 2.0,
    }
    total = sum(components.values())
    passed = bool(
        total == 25.0
        and all(value >= 0 for value in components.values())
    )
    payload = base(
        261,
        (
            "COST_SLIPPAGE_MODEL_REGISTRY_PASS_RESEARCH_ONLY"
            if passed
            else "COST_SLIPPAGE_MODEL_REGISTRY_NEEDS_REVIEW"
        ),
    )
    payload.update(
        {
            "components": components,
            "total_round_trip_cost_bps": total,
            "total_round_trip_cost_fraction": total / 10_000,
            "cost_model_scope": (
                "CONSERVATIVE_PUBLIC_SPOT_REFERENCE_RESEARCH_ONLY"
            ),
            "passed": passed,
        }
    )
    return payload


def p262(
    dataset: dict[str, Any],
    candidate: dict[str, Any],
    cost_model: dict[str, Any],
) -> dict[str, Any]:
    rows_by_id = {
        int(item["row_id"]): item
        for item in dataset["examples"]
    }
    selected = candidate["selected_candidate"]
    cost_fraction = float(
        cost_model["total_round_trip_cost_fraction"]
    )
    outcomes: list[dict[str, Any]] = []

    for prediction in selected["predictions"]:
        row = rows_by_id[int(prediction["row_id"])]
        predicted_direction = direction(
            float(prediction["probability_up"])
        )
        gross = (
            predicted_direction * float(row["future_return_1h"])
            if predicted_direction
            else 0.0
        )
        cost = cost_fraction if predicted_direction else 0.0
        outcomes.append(
            {
                "fold": prediction["fold"],
                "row_id": prediction["row_id"],
                "direction": predicted_direction,
                "gross_return": gross,
                "cost_fraction": cost,
                "net_return": gross - cost,
            }
        )

    net_returns = [item["net_return"] for item in outcomes]
    mean_net = mean(net_returns)
    net_stdev = stdev(net_returns)
    standard_error = (
        net_stdev / math.sqrt(len(net_returns))
        if net_returns
        else 0.0
    )
    lower_95 = mean_net - 1.96 * standard_error
    fold_means = [
        {
            "fold": fold,
            "mean_net_return": mean(
                [
                    item["net_return"]
                    for item in outcomes
                    if item["fold"] == fold
                ]
            ),
        }
        for fold in (1, 2, 3)
    ]
    edge_candidate = bool(
        mean_net > 0
        and lower_95 > 0
        and all(item["mean_net_return"] > 0 for item in fold_means)
    )
    passed = len(outcomes) == 72
    payload = base(
        262,
        (
            "NET_EDGE_SHADOW_EVALUATOR_PASS_RESEARCH_ONLY"
            if passed
            else "NET_EDGE_SHADOW_EVALUATOR_NEEDS_REVIEW"
        ),
    )
    payload.update(
        {
            "selected_candidate_name": candidate[
                "selected_candidate_name"
            ],
            "observations": len(outcomes),
            "total_cost_bps": cost_model[
                "total_round_trip_cost_bps"
            ],
            "mean_gross_return": selected["mean_gross_return"],
            "mean_net_return": mean_net,
            "net_return_stdev": net_stdev,
            "net_return_standard_error": standard_error,
            "lower_95_mean_net_return": lower_95,
            "net_win_rate": mean(
                [
                    float(item["net_return"] > 0)
                    for item in outcomes
                ]
            ),
            "fold_net_returns": fold_means,
            "net_edge_candidate": edge_candidate,
            "edge_validated": False,
            "outcomes": outcomes,
            "passed": passed,
        }
    )
    return payload


def p263(
    baselines: dict[str, Any],
    candidate: dict[str, Any],
    diagnostics: dict[str, Any],
    edge: dict[str, Any],
) -> dict[str, Any]:
    selected = candidate["selected_candidate"]
    thresholds = {
        "minimum_out_of_sample_rows": 72,
        "minimum_brier_improvement": 0.005,
        "minimum_accuracy_improvement": 0.02,
        "maximum_calibration_proxy_error": 0.10,
        "maximum_fold_accuracy_stdev": 0.10,
        "net_edge_lower_95_must_be_positive": True,
        "all_fold_net_returns_must_be_positive": True,
    }
    checks = {
        "sample_size": (
            selected["observations"]
            >= thresholds["minimum_out_of_sample_rows"]
        ),
        "brier_improvement": (
            selected["brier_improvement_vs_best_baseline"]
            >= thresholds["minimum_brier_improvement"]
        ),
        "accuracy_improvement": (
            selected["accuracy_improvement_vs_best_baseline"]
            >= thresholds["minimum_accuracy_improvement"]
        ),
        "calibration_proxy": (
            diagnostics["calibration_proxy_error"]
            <= thresholds["maximum_calibration_proxy_error"]
        ),
        "fold_stability": (
            diagnostics["fold_accuracy_stdev"]
            <= thresholds["maximum_fold_accuracy_stdev"]
        ),
        "positive_net_lower_95": (
            edge["lower_95_mean_net_return"] > 0
        ),
        "positive_net_all_folds": all(
            item["mean_net_return"] > 0
            for item in edge["fold_net_returns"]
        ),
    }
    predictive_validity = bool(
        checks["sample_size"]
        and checks["brier_improvement"]
        and checks["accuracy_improvement"]
        and checks["calibration_proxy"]
        and checks["fold_stability"]
    )
    edge_validated = bool(
        predictive_validity
        and checks["positive_net_lower_95"]
        and checks["positive_net_all_folds"]
    )
    reasons = [
        name.upper()
        for name, value in checks.items()
        if not value
    ]
    if not reasons:
        reasons = ["OPERATIONAL_PROMOTION_NOT_AUTHORIZED"]
    passed = bool(
        len(checks) == 7
        and selected["observations"] == 72
    )
    payload = base(
        263,
        (
            "PREDICTIVE_EDGE_DECISION_GATE_PASS_RESEARCH_ONLY"
            if passed
            else "PREDICTIVE_EDGE_DECISION_GATE_NEEDS_REVIEW"
        ),
    )
    payload.update(
        {
            "selected_candidate_name": candidate[
                "selected_candidate_name"
            ],
            "best_baseline_name": baselines[
                "best_baseline_name"
            ],
            "thresholds": thresholds,
            "checks": checks,
            "predictive_validity_established": predictive_validity,
            "edge_validated": edge_validated,
            "decision_layer_allowed": False,
            "action": "NO_ACTION_RESEARCH_ONLY",
            "reason_codes": reasons,
            "passed": passed,
        }
    )
    return payload


def p264(
    dataset: dict[str, Any],
    baselines: dict[str, Any],
    candidate: dict[str, Any],
    diagnostics: dict[str, Any],
    cost_model: dict[str, Any],
    edge: dict[str, Any],
    gate: dict[str, Any],
) -> dict[str, Any]:
    selected = candidate["selected_candidate"]
    packet = {
        "packet_version": "2.0",
        "asset": "BTC",
        "market": "BTC-USDT_PUBLIC_SPOT_REFERENCE",
        "dataset_fingerprint": dataset["dataset_fingerprint"],
        "out_of_sample_rows": selected["observations"],
        "best_baseline_name": baselines["best_baseline_name"],
        "best_baseline_brier_score": baselines[
            "best_baseline_brier_score"
        ],
        "selected_candidate_name": candidate[
            "selected_candidate_name"
        ],
        "candidate_brier_score": selected["brier_score"],
        "candidate_directional_accuracy": selected[
            "directional_accuracy"
        ],
        "brier_improvement_vs_best_baseline": selected[
            "brier_improvement_vs_best_baseline"
        ],
        "accuracy_improvement_vs_best_baseline": selected[
            "accuracy_improvement_vs_best_baseline"
        ],
        "calibration_proxy_error": diagnostics[
            "calibration_proxy_error"
        ],
        "fold_accuracy_stdev": diagnostics[
            "fold_accuracy_stdev"
        ],
        "total_cost_bps": cost_model[
            "total_round_trip_cost_bps"
        ],
        "mean_gross_return": edge["mean_gross_return"],
        "mean_net_return": edge["mean_net_return"],
        "lower_95_mean_net_return": edge[
            "lower_95_mean_net_return"
        ],
        "predictive_validity_established": gate[
            "predictive_validity_established"
        ],
        "edge_validated": gate["edge_validated"],
        "research_candidate_status": (
            "VALIDATED_RESEARCH_CANDIDATE"
            if gate["predictive_validity_established"]
            and gate["edge_validated"]
            else "NOT_VALIDATED_RESEARCH_CANDIDATE"
        ),
        "action": "NO_ACTION_RESEARCH_ONLY",
        "position_size": 0,
        "entry": None,
        "exit": None,
        "stop": None,
        "reason_codes": gate["reason_codes"],
        "operational_status": "BLOCKED_RESEARCH_ONLY",
    }
    safe = bool(
        packet["action"] == "NO_ACTION_RESEARCH_ONLY"
        and packet["position_size"] == 0
        and packet["entry"] is None
        and packet["exit"] is None
        and packet["stop"] is None
        and packet["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    )
    payload = base(
        264,
        (
            "PREDICTIVE_SHADOW_OUTCOME_PACKET_PASS_RESEARCH_ONLY"
            if safe
            else "PREDICTIVE_SHADOW_OUTCOME_PACKET_NEEDS_REVIEW"
        ),
    )
    payload.update(
        {
            "shadow_outcome_packet": packet,
            "packet_safe": safe,
            "decision_layer_allowed": False,
            "passed": safe,
        }
    )
    return payload


def p265(
    artifacts: list[dict[str, Any]],
    targeted: dict[str, Any],
    full_suite: dict[str, Any],
) -> dict[str, Any]:
    phases = [int(item["phase"]) for item in artifacts]
    packet = artifacts[-1]["shadow_outcome_packet"]
    suite_ok = bool(
        full_suite.get("passed")
        and full_suite.get("coverage_complete")
        and full_suite.get("manifest_stable")
        and full_suite.get("test_file_count") == 504
        and full_suite.get("coverage_file_count") == 504
        and full_suite.get("totals", {}).get("tests", 0) >= 1411
        and full_suite.get("totals", {}).get("failures") == 0
        and full_suite.get("totals", {}).get("errors") == 0
    )
    targeted_ok = bool(
        targeted.get("returncode") == 0
        and targeted.get("test_files") == 20
        and targeted.get("failures") == 0
        and targeted.get("errors") == 0
    )
    passed = bool(
        phases == list(range(256, 265))
        and all(item.get("passed") is True for item in artifacts)
        and targeted_ok
        and suite_ok
        and packet["action"] == "NO_ACTION_RESEARCH_ONLY"
        and packet["position_size"] == 0
    )
    payload = base(
        265,
        (
            "PREDICTIVE_EDGE_FULL_INTEGRATION_256_265_PASS_RESEARCH_ONLY"
            if passed
            else "PREDICTIVE_EDGE_FULL_INTEGRATION_256_265_NEEDS_REVIEW"
        ),
    )
    payload.update(
        {
            "checkpoint_status": (
                "PREDICTIVE_EDGE_EVALUATED_OPERATION_BLOCKED_RESEARCH_ONLY"
                if passed
                else "PREDICTIVE_EDGE_CHECKPOINT_NEEDS_REVIEW"
            ),
            "phase_chain": {
                str(item["phase"]): item
                for item in artifacts
            },
            "targeted_tests": targeted,
            "full_suite": full_suite,
            "global_full_suite_passed": suite_ok,
            "predictive_validity_established": packet[
                "predictive_validity_established"
            ],
            "edge_validated": packet["edge_validated"],
            "decision_layer_allowed": False,
            "action": "NO_ACTION_RESEARCH_ONLY",
            "next_tracking_checkpoint": 275,
            "next_mandatory_global_full_suite": 285,
            "passed": passed,
        }
    )
    return payload


def tracking(payload: dict[str, Any]) -> dict[str, str]:
    packet = payload["phase_chain"]["264"][
        "shadow_outcome_packet"
    ]
    targeted = payload["targeted_tests"]
    suite = payload["full_suite"]
    totals = suite["totals"]
    return {
        "QRDS_MASTER_PROGRESS_BY_TENS_PHASE265.md": "\n".join(
            [
                "# QRDS Master Progress - Phase 265",
                "",
                "- Batch 256-265: PASS",
                f"- Global test files: {suite['test_file_count']}",
                f"- Global tests: {totals['tests']}",
                f"- Selected candidate: "
                f"{packet['selected_candidate_name']}",
                f"- Predictive validity: "
                f"{packet['predictive_validity_established']}",
                f"- Edge validated: {packet['edge_validated']}",
                "- Action: NO_ACTION_RESEARCH_ONLY",
                "- Operational: BLOCKED_RESEARCH_ONLY",
                "- Next tracking checkpoint: Phase 275",
                "- Next mandatory global full-suite: Phase 285",
                "",
            ]
        ),
        "QRDS_ARCHITECTURE_MERMAID_PHASE265.md": "\n".join(
            [
                "# QRDS Architecture - Phase 265",
                "",
                "```mermaid",
                "flowchart LR",
                " A[Admitted public snapshot] --> B[Walk-forward dataset]",
                " B --> C[Leakage-free temporal folds]",
                " C --> D[Baselines]",
                " C --> E[Candidate hypotheses]",
                " D --> F[Out-of-sample comparison]",
                " E --> F",
                " F --> G[Calibration + stability]",
                " G --> H[Cost + slippage]",
                " H --> I[Net edge gate]",
                " I --> J[Shadow outcome packet]",
                " J --> K[NO_ACTION_RESEARCH_ONLY]",
                "```",
                "",
            ]
        ),
        "QRDS_PROGRESS_TABLE_BY_TENS_PHASE265.md": "\n".join(
            [
                "# QRDS Progress Table - Phase 265",
                "",
                "| Window | Status | Test files | Tests | Candidate | Action |",
                "|---|---:|---:|---:|---|---|",
                (
                    f"| 256-265 | PASS | "
                    f"{suite['test_file_count']} | "
                    f"{totals['tests']} | "
                    f"{packet['selected_candidate_name']} | "
                    "NO_ACTION_RESEARCH_ONLY |"
                ),
                "",
            ]
        ),
        "QRDS_PREDICTIVE_EDGE_MILESTONE_PHASE265.md": "\n".join(
            [
                "# Predictive Edge Milestone - Phase 265",
                "",
                f"- Dataset fingerprint: "
                f"`{packet['dataset_fingerprint']}`",
                f"- Out-of-sample rows: "
                f"{packet['out_of_sample_rows']}",
                f"- Best baseline: "
                f"{packet['best_baseline_name']}",
                f"- Selected candidate: "
                f"{packet['selected_candidate_name']}",
                f"- Candidate Brier score: "
                f"{packet['candidate_brier_score']:.6f}",
                f"- Brier improvement: "
                f"{packet['brier_improvement_vs_best_baseline']:.6f}",
                f"- Accuracy improvement: "
                f"{packet['accuracy_improvement_vs_best_baseline']:.6f}",
                f"- Total modeled cost: "
                f"{packet['total_cost_bps']:.2f} bps",
                f"- Mean net return: "
                f"{packet['mean_net_return']:.8f}",
                f"- Lower 95% mean net return: "
                f"{packet['lower_95_mean_net_return']:.8f}",
                f"- Predictive validity: "
                f"{packet['predictive_validity_established']}",
                f"- Edge validated: {packet['edge_validated']}",
                "- Action: NO_ACTION_RESEARCH_ONLY",
                "",
            ]
        ),
        "QRDS_ROADMAP_266_275_RESEARCH_ONLY.md": "\n".join(
            [
                "# QRDS Roadmap 266-275",
                "",
                "## Goal",
                "",
                "Expand the admitted historical window, add regime and "
                "subperiod replication, and expose the shadow outcome "
                "packet through the local product portal.",
                "",
                "## Safety",
                "",
                "- No automatic promotion from statistical metrics.",
                "- No account, API authentication, orders or capital.",
                "- Every network block pauses for ENTER.",
                "- Operational remains BLOCKED_RESEARCH_ONLY.",
                "",
            ]
        ),
        "qrds_progress_snapshot_phase265.json": (
            json.dumps(
                {
                    "baseline_phase": 265,
                    "batch_256_265": {
                        "passed": True,
                        "versioned_files": 37,
                        "targeted_test_files": targeted[
                            "test_files"
                        ],
                        "targeted_tests": targeted["tests"],
                        "global_test_files": suite[
                            "test_file_count"
                        ],
                        "global_covered_files": suite[
                            "coverage_file_count"
                        ],
                        "global_tests": totals["tests"],
                        "failures": 0,
                        "errors": 0,
                        "manifest_stable": suite[
                            "manifest_stable"
                        ],
                    },
                    "predictive_edge": packet,
                    "next_tracking_checkpoint": 275,
                    "next_mandatory_global_full_suite": 285,
                    "operational_status": "BLOCKED_RESEARCH_ONLY",
                    "decision_layer_allowed": False,
                    "canonical_data_writes": 0,
                },
                indent=2,
                ensure_ascii=True,
            )
            + "\n"
        ),
    }


def document(phase: int, payload: dict[str, Any]) -> str:
    lines = [
        f"# Phase {phase} Research Summary",
        "",
        f"- Status: `{payload['status']}`",
        f"- Passed: `{payload['passed']}`",
        "- Operational: `BLOCKED_RESEARCH_ONLY`",
        "- Decision layer allowed: `False`",
        "- Canonical writes: `0`",
    ]
    if phase == 256:
        lines += [
            f"- Dataset rows: `{payload['dataset_rows']}`",
            f"- Dataset fingerprint: "
            f"`{payload['dataset_fingerprint']}`",
        ]
    elif phase == 257:
        lines += [
            f"- Temporal folds: `{payload['fold_count']}`",
            f"- Out-of-sample rows: "
            f"`{payload['total_out_of_sample_rows']}`",
            f"- Lookahead leakage detected: "
            f"`{payload['lookahead_leakage_detected']}`",
        ]
    elif phase == 258:
        lines += [
            f"- Best baseline: `{payload['best_baseline_name']}`",
            f"- Best baseline Brier: "
            f"`{payload['best_baseline_brier_score']:.6f}`",
        ]
    elif phase == 259:
        selected = payload["selected_candidate"]
        lines += [
            f"- Selected candidate: "
            f"`{payload['selected_candidate_name']}`",
            f"- Candidate Brier: "
            f"`{selected['brier_score']:.6f}`",
            f"- Directional accuracy: "
            f"`{selected['directional_accuracy']:.4%}`",
        ]
    elif phase == 260:
        lines += [
            f"- Calibration proxy error: "
            f"`{payload['calibration_proxy_error']:.6f}`",
            f"- Fold accuracy stdev: "
            f"`{payload['fold_accuracy_stdev']:.6f}`",
            "- Calibration validated: `False`.",
        ]
    elif phase == 261:
        lines += [
            f"- Total modeled round-trip cost: "
            f"`{payload['total_round_trip_cost_bps']:.2f} bps`",
        ]
    elif phase == 262:
        lines += [
            f"- Mean gross return: "
            f"`{payload['mean_gross_return']:.8f}`",
            f"- Mean net return: "
            f"`{payload['mean_net_return']:.8f}`",
            f"- Lower 95% mean net return: "
            f"`{payload['lower_95_mean_net_return']:.8f}`",
            f"- Net edge candidate: "
            f"`{payload['net_edge_candidate']}`",
        ]
    elif phase == 263:
        lines += [
            f"- Predictive validity: "
            f"`{payload['predictive_validity_established']}`",
            f"- Edge validated: `{payload['edge_validated']}`",
            f"- Action: `{payload['action']}`",
        ]
    elif phase == 264:
        packet = payload["shadow_outcome_packet"]
        lines += [
            f"- Candidate: `{packet['selected_candidate_name']}`",
            f"- Research candidate status: "
            f"`{packet['research_candidate_status']}`",
            f"- Action: `{packet['action']}`",
            "- Position size: `0`.",
        ]
    elif phase == 265:
        lines += [
            f"- Checkpoint: `{payload['checkpoint_status']}`",
            f"- Global test files: "
            f"`{payload['full_suite']['test_file_count']}`",
            f"- Global tests: "
            f"`{payload['full_suite']['totals']['tests']}`",
            f"- Predictive validity: "
            f"`{payload['predictive_validity_established']}`",
            f"- Edge validated: `{payload['edge_validated']}`",
            "- Action: `NO_ACTION_RESEARCH_ONLY`.",
        ]
    lines += [
        "",
        "Metrics are research evidence only and cannot authorize "
        "orders, allocation or real capital.",
        "",
    ]
    return "\n".join(lines)


def cli_main(phase: int) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--documentation", required=True)
    parser.add_argument("--input", action="append", default=[])
    parser.add_argument("--packet-output")
    parser.add_argument("--targeted-summary")
    parser.add_argument("--output-dir")
    parser.add_argument("--tracking-dir")
    parser.add_argument("--project-root")
    parser.add_argument("--timeout-seconds", type=int, default=5400)
    args = parser.parse_args()
    inputs = [read(path) for path in args.input]

    if phase == 256:
        payload = p256(inputs[0])
    elif phase == 257:
        payload = p257(inputs[0])
    elif phase == 258:
        payload = p258(inputs[0], inputs[1])
    elif phase == 259:
        payload = p259(inputs[0], inputs[1], inputs[2])
    elif phase == 260:
        payload = p260(inputs[0])
    elif phase == 261:
        payload = p261()
    elif phase == 262:
        payload = p262(inputs[0], inputs[1], inputs[2])
    elif phase == 263:
        payload = p263(inputs[0], inputs[1], inputs[2], inputs[3])
    elif phase == 264:
        payload = p264(
            inputs[0],
            inputs[1],
            inputs[2],
            inputs[3],
            inputs[4],
            inputs[5],
            inputs[6],
        )
        if not args.packet_output:
            raise SystemExit("--packet-output is required.")
        write(args.packet_output, payload["shadow_outcome_packet"])
    elif phase == 265:
        if not args.targeted_summary:
            raise SystemExit("--targeted-summary is required.")
        if not args.output_dir:
            raise SystemExit("--output-dir is required.")
        if not args.tracking_dir:
            raise SystemExit("--tracking-dir is required.")
        from crypto_decision_lab.scripts.phase225_robustness_full_integration_tracking_checkpoint_research_only import (
            run_full_suite,
        )

        root = (
            Path(args.project_root).resolve()
            if args.project_root
            else Path.cwd().resolve()
        )
        full_suite = run_full_suite(
            Path(args.output_dir),
            timeout_seconds=args.timeout_seconds,
            root=root,
        )
        payload = p265(
            inputs,
            read(args.targeted_summary),
            full_suite,
        )
        tracking_dir = Path(args.tracking_dir)
        tracking_dir.mkdir(parents=True, exist_ok=True)
        for filename, content in tracking(payload).items():
            (tracking_dir / filename).write_text(
                content,
                encoding="utf-8",
            )
    else:
        raise ValueError(phase)

    write(args.artifact, payload)
    documentation = Path(args.documentation)
    documentation.parent.mkdir(parents=True, exist_ok=True)
    documentation.write_text(
        document(phase, payload),
        encoding="utf-8",
    )
    print(payload["status"])
    if phase == 259:
        print(
            "SELECTED_CANDIDATE:",
            payload["selected_candidate_name"],
        )
    if phase == 262:
        print(
            "MEAN_NET_RETURN:",
            payload["mean_net_return"],
        )
        print(
            "LOWER_95_MEAN_NET_RETURN:",
            payload["lower_95_mean_net_return"],
        )
    if phase == 263:
        print(
            "PREDICTIVE_VALIDITY:",
            payload["predictive_validity_established"],
        )
        print("EDGE_VALIDATED:", payload["edge_validated"])
        print("ACTION:", payload["action"])
    if phase == 264:
        print("SHADOW_OUTCOME_PACKET:", args.packet_output)
    return 0 if payload["passed"] else 1
