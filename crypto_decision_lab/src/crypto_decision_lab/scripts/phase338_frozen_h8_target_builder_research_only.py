from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase336_345_abstention_evaluation_common import (
    HOUR_MS,
    ROOT,
    TARGET_MATRIX_FIELDS,
    as_float,
    base_payload,
    dataset_path,
    fingerprint,
    read_csv_gz,
    read_csv_gz_rows,
    read_json,
    sha256_file,
    validate_phase,
    write_csv_gz,
    write_json,
    write_summary,
)


def build(
    phase301_path: Path,
    phase329_path: Path,
    phase337_path: Path,
    output_dir: Path,
    *,
    minimum_rows: int = 8000,
) -> dict[str, Any]:
    phase301 = read_json(phase301_path)
    phase329 = read_json(phase329_path)
    phase337 = read_json(phase337_path)
    for phase, item in ((301, phase301), (329, phase329), (337, phase337)):
        validate_phase(item, phase)
    if phase329.get("target_label_frozen") is not True:
        raise RuntimeError("Phase 329 target contract is not frozen.")
    target_contract = phase329.get("target_contract") or {}
    horizon = int(target_contract.get("forecast_horizon_hours", 0))
    if horizon != 8:
        raise RuntimeError(f"Frozen target horizon is {horizon}, expected 8.")

    feature_rows = read_csv_gz(ROOT / phase337["matrix_path"])
    allowed_timestamps = {int(row["open_time_ms"]) for row in feature_rows}
    candle_series: dict[str, dict[int, float]] = {}
    for name in sorted(phase301.get("datasets", {})):
        if not name.endswith("_candles"):
            continue
        values: dict[int, float] = {}
        for row in read_csv_gz_rows(dataset_path(phase301, name)):
            try:
                timestamp = int(row["open_time_ms"])
            except (KeyError, TypeError, ValueError):
                continue
            close = as_float(row.get("close"))
            if close is not None and close > 0:
                values[timestamp] = float(close)
        if values:
            candle_series[name] = values
    if len(candle_series) < 3:
        raise RuntimeError("At least three candle providers are required for the H8 target.")

    future_delta = horizon * HOUR_MS
    rows_out: list[dict[str, Any]] = []
    for timestamp in sorted(allowed_timestamps):
        future_time = timestamp + future_delta
        returns: list[float] = []
        for values in candle_series.values():
            current = values.get(timestamp)
            future = values.get(future_time)
            if current is not None and future is not None and current > 0:
                returns.append(future / current - 1.0)
        if len(returns) < 3:
            continue
        signs = {1 if value > 0 else -1 if value < 0 else 0 for value in returns}
        sign_disagreement = int(len(signs) > 1)
        dispersion_bps = (max(returns) - min(returns)) * 10000.0
        rows_out.append(
            {
                "open_time_ms": timestamp,
                "future_time_ms": future_time,
                "eligible_exchange_count": len(returns),
                "future_sign_disagreement": sign_disagreement,
                "future_return_dispersion_bps": dispersion_bps,
            }
        )
    if len(rows_out) < minimum_rows:
        raise RuntimeError(f"H8 target matrix has only {len(rows_out)} rows; minimum is {minimum_rows}.")

    output_dir.mkdir(parents=True, exist_ok=True)
    matrix_path = output_dir / "phase338_frozen_h8_target_components.csv.gz"
    write_csv_gz(matrix_path, rows_out, TARGET_MATRIX_FIELDS)
    payload = base_payload(338, "FROZEN_H8_TARGET_COMPONENTS_READY_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE338_FROZEN_H8_TARGET_BUILDER_READY_RESEARCH_ONLY",
            "target_id": target_contract.get("target_id"),
            "forecast_horizon_hours": horizon,
            "row_count": len(rows_out),
            "target_components_path": matrix_path.relative_to(ROOT).as_posix(),
            "target_components_sha256": sha256_file(matrix_path),
            "minimum_eligible_exchanges": 3,
            "training_fold_threshold_required": True,
            "outer_holdout_threshold_selection_allowed": False,
            "fold_specific_final_label_materialized": False,
            "future_values_used_as_features": False,
            "directional_return_prediction_created": False,
            "historical_experiments_executed": 0,
            "strategy_approved": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    write_json(output_dir / "phase338_frozen_h8_target_builder.json", payload)
    write_summary(
        ROOT / "docs/reports/abstention_v1/phase338_frozen_h8_target_builder_summary.md",
        title="Phase 338 — Frozen H8 Abstention/reliability Target Builder",
        gate=payload["gate"],
        bullets=[
            f"Target rows: `{len(rows_out)}`",
            "Forecast horizon: `8 hours`",
            "Final dispersion threshold source: `TRAINING_FOLD_ONLY`",
            "Outer holdout used for threshold selection: `False`",
            "Future values used as features: `False`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    artifacts = ROOT / "artifacts"
    parser.add_argument("--phase301-artifact", type=Path, default=artifacts / "phase301_official_public_history_extension_research_only/phase301_official_public_history_extension.json")
    parser.add_argument("--phase329-artifact", type=Path, default=artifacts / "phase329_non_directional_target_label_freeze_research_only/phase329_non_directional_target_label_freeze.json")
    parser.add_argument("--phase337-artifact", type=Path, default=artifacts / "phase337_asof_quality_feature_matrix_research_only/phase337_asof_quality_feature_matrix.json")
    parser.add_argument("--output-dir", type=Path, default=artifacts / "phase338_frozen_h8_target_builder_research_only")
    args = parser.parse_args()
    payload = build(args.phase301_artifact, args.phase329_artifact, args.phase337_artifact, args.output_dir)
    print(payload["gate"])
    print("Target rows:", payload["row_count"])
    print("Training-fold threshold required:", payload["training_fold_threshold_required"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
