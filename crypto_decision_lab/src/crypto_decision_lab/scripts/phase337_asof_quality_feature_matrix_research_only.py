from __future__ import annotations

import argparse
import statistics
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase336_345_abstention_evaluation_common import (
    FEATURE_MATRIX_FIELDS,
    HOUR_MS,
    ROOT,
    as_float,
    asof_value,
    base_payload,
    dataset_path,
    fingerprint,
    iso_from_ms,
    read_csv_gz,
    read_csv_gz_rows,
    read_json,
    sha256_file,
    validate_phase,
    write_csv_gz,
    write_json,
    write_summary,
)


def _series(payload: dict[str, Any], dataset_name: str, timestamp_key: str, value_key: str) -> tuple[list[int], list[float]]:
    rows = read_csv_gz_rows(dataset_path(payload, dataset_name))
    pairs: list[tuple[int, float]] = []
    for row in rows:
        value = as_float(row.get(value_key))
        try:
            timestamp = int(row[timestamp_key])
        except (KeyError, TypeError, ValueError):
            continue
        if value is not None:
            pairs.append((timestamp, float(value)))
    pairs.sort()
    return [item[0] for item in pairs], [item[1] for item in pairs]


def build(
    phase301_path: Path,
    phase302_path: Path,
    phase321_path: Path,
    phase336_path: Path,
    output_dir: Path,
    *,
    minimum_rows: int = 8760,
) -> dict[str, Any]:
    phase301 = read_json(phase301_path)
    phase302 = read_json(phase302_path)
    phase321 = read_json(phase321_path)
    phase336 = read_json(phase336_path)
    for phase, item in ((301, phase301), (302, phase302), (321, phase321), (336, phase336)):
        validate_phase(item, phase)
    if phase336.get("registry_open") is not True or phase336.get("active_template_count") != 12:
        raise RuntimeError("Phase 336 registry is not open with exactly 12 templates.")

    candle_series: dict[str, dict[int, float]] = {}
    for name in sorted(phase301.get("datasets", {})):
        if not name.endswith("_candles"):
            continue
        rows = read_csv_gz_rows(dataset_path(phase301, name))
        values: dict[int, float] = {}
        for row in rows:
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
        raise RuntimeError("At least three candle providers are required.")

    primary_rows = read_csv_gz(ROOT / phase302["matrix_path"])
    primary = {int(row["open_time_ms"]): row for row in primary_rows}

    funding_sources: list[tuple[list[int], list[float]]] = []
    for name in ("binance_funding", "bybit_funding"):
        if name in phase301.get("datasets", {}):
            funding_sources.append(_series(phase301, name, "funding_time_ms", "funding_rate"))
    oi_timestamps: list[int] = []
    oi_values: list[float] = []
    if "bybit_open_interest" in phase301.get("datasets", {}):
        oi_timestamps, oi_values = _series(phase301, "bybit_open_interest", "timestamp_ms", "open_interest")

    all_timestamps = sorted(set().union(*(set(values) for values in candle_series.values())))
    output_rows: list[dict[str, Any]] = []
    for timestamp in all_timestamps:
        prices = [values[timestamp] for values in candle_series.values() if timestamp in values]
        if len(prices) < 3 or timestamp not in primary:
            continue
        median_close = statistics.median(prices)
        spread_bps = (max(prices) - min(prices)) / median_close * 10000.0 if median_close > 0 else 0.0
        max_deviation = max(abs(price - median_close) / median_close * 10000.0 for price in prices) if median_close > 0 else 0.0

        funding_values: list[float] = []
        funding_ages: list[float] = []
        for timestamps, values in funding_sources:
            value, observed_at = asof_value(timestamps, values, timestamp)
            if value is None or observed_at is None:
                continue
            age = (timestamp - observed_at) / HOUR_MS
            if 0 <= age <= 12:
                funding_values.append(value)
                funding_ages.append(age)
        funding_count = len(funding_values)
        funding_missing = max(0, 2 - funding_count)
        funding_age = max(funding_ages) if funding_ages else 24.0
        funding_dispersion = (
            (max(funding_values) - min(funding_values)) * 10000.0
            if len(funding_values) >= 2
            else 0.0
        )

        oi_value, oi_observed_at = asof_value(oi_timestamps, oi_values, timestamp)
        oi_missing = int(oi_value is None or oi_observed_at is None)
        oi_age = (
            (timestamp - int(oi_observed_at)) / HOUR_MS
            if oi_observed_at is not None
            else 24.0
        )
        if oi_age < 0:
            raise RuntimeError("Open-interest as-of join used a future observation.")
        provider_shortfall = max(0, 4 - len(prices))
        stale_funding = int(funding_age > 8)
        stale_oi = int(oi_age > 2)
        risk_score = float(provider_shortfall + funding_missing + oi_missing + stale_funding + stale_oi)
        source = primary[timestamp]
        output_rows.append(
            {
                "open_time_ms": timestamp,
                "open_time_utc": source.get("open_time_utc") or iso_from_ms(timestamp),
                "provider_count": len(prices),
                "provider_shortfall": provider_shortfall,
                "median_close": median_close,
                "spread_bps": spread_bps,
                "max_abs_deviation_bps": max_deviation,
                "funding_source_count": funding_count,
                "funding_missing_count": funding_missing,
                "funding_age_hours": funding_age,
                "funding_dispersion_bps": funding_dispersion,
                "open_interest_missing": oi_missing,
                "open_interest_age_hours": oi_age,
                "data_quality_risk_score": risk_score,
                "realized_vol_24h": as_float(source.get("realized_vol_24h"), 0.0) or 0.0,
                "return_24h": as_float(source.get("return_24h"), 0.0) or 0.0,
            }
        )
    if len(output_rows) < minimum_rows:
        raise RuntimeError(f"As-of feature matrix has only {len(output_rows)} rows; minimum is {minimum_rows}.")

    output_dir.mkdir(parents=True, exist_ok=True)
    matrix_path = output_dir / "phase337_asof_quality_feature_matrix.csv.gz"
    write_csv_gz(matrix_path, output_rows, FEATURE_MATRIX_FIELDS)
    payload = base_payload(337, "ASOF_QUALITY_FEATURE_MATRIX_READY_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE337_ASOF_QUALITY_FEATURE_MATRIX_READY_RESEARCH_ONLY",
            "phase336_registry_sha256": phase336["active_registry_sha256"],
            "row_count": len(output_rows),
            "candle_provider_count": len(candle_series),
            "matrix_path": matrix_path.relative_to(ROOT).as_posix(),
            "matrix_sha256": sha256_file(matrix_path),
            "feature_count": len(FEATURE_MATRIX_FIELDS) - 2,
            "features_available_at_or_before_decision_time": True,
            "future_feature_use_allowed": False,
            "asof_join_verified": True,
            "directional_prediction_created": False,
            "historical_experiments_executed": 0,
            "strategy_approved": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    write_json(output_dir / "phase337_asof_quality_feature_matrix.json", payload)
    write_summary(
        ROOT / "docs/reports/abstention_v1/phase337_asof_quality_feature_matrix_summary.md",
        title="Phase 337 — Strictly As-of Quality-feature Matrix",
        gate=payload["gate"],
        bullets=[
            f"Rows: `{len(output_rows)}`",
            f"Candle providers: `{len(candle_series)}`",
            "As-of join verified: `True`",
            "Future feature use: `False`",
            "Directional prediction created: `False`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    artifacts = ROOT / "artifacts"
    parser.add_argument("--phase301-artifact", type=Path, default=artifacts / "phase301_official_public_history_extension_research_only/phase301_official_public_history_extension.json")
    parser.add_argument("--phase302-artifact", type=Path, default=artifacts / "phase302_controlled_feature_registry_v2_research_only/phase302_controlled_feature_registry_v2.json")
    parser.add_argument("--phase321-artifact", type=Path, default=artifacts / "phase321_derivatives_missingness_audit_research_only/phase321_derivatives_missingness_audit.json")
    parser.add_argument("--phase336-artifact", type=Path, default=artifacts / "phase336_finite_registry_opening_research_only/phase336_finite_registry_opening.json")
    parser.add_argument("--output-dir", type=Path, default=artifacts / "phase337_asof_quality_feature_matrix_research_only")
    args = parser.parse_args()
    payload = build(args.phase301_artifact, args.phase302_artifact, args.phase321_artifact, args.phase336_artifact, args.output_dir)
    print(payload["gate"])
    print("Rows:", payload["row_count"])
    print("As-of join verified:", payload["asof_join_verified"])
    print("Operational:", payload["locks"]["operational_status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
