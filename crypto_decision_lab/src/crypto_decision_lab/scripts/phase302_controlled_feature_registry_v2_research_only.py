from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase301_305_evidence_v2_common import (
    ROOT,
    base_payload,
    lag_return,
    merge_asof,
    read_csv_gz,
    read_json,
    rolling_mean,
    rolling_std,
    sha256_file,
    to_float,
    write_csv_gz,
    write_json,
    write_text,
)

FEATURE_FIELDS = (
    "open_time_ms",
    "open_time_utc",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "quote_volume",
    "return_1h",
    "return_4h",
    "return_24h",
    "realized_vol_24h",
    "realized_vol_168h",
    "volume_z_24h",
    "volume_z_168h",
    "range_pct",
    "close_location",
    "illiquidity_proxy",
    "sma_distance_24h",
    "sma_distance_168h",
    "funding_rate_asof",
    "funding_mean_3",
    "funding_mean_21",
    "open_interest_asof",
    "open_interest_change_1h",
    "open_interest_change_24h",
)


def _float_column(rows: list[dict[str, str]], key: str) -> list[float]:
    output: list[float] = []
    for row in rows:
        value = to_float(row.get(key))
        if value is None:
            raise ValueError(f"Invalid numeric value for {key}: {row.get(key)!r}")
        output.append(value)
    return output


def _zscore(values: list[float], window: int) -> list[float | None]:
    means = rolling_mean(values, window)
    stds = rolling_std(values, window)
    result: list[float | None] = []
    for value, mean, std in zip(values, means, stds):
        if mean is None or std is None or std <= 0:
            result.append(None)
        else:
            result.append((value - mean) / std)
    return result


def _select_primary_dataset(phase301: dict[str, Any]) -> tuple[str, Path]:
    datasets = phase301["datasets"]
    preferred = ("binance_candles", "okx_candles", "bybit_candles", "coinbase_candles")
    available = [
        (name, datasets[name]["rows"], ROOT / datasets[name]["path"])
        for name in preferred
        if name in datasets
    ]
    if not available:
        raise RuntimeError("No candle dataset exists in Phase 301.")
    available.sort(key=lambda item: (item[0] != "binance_candles", -int(item[1])))
    name, _, path = available[0]
    return name, path


def _load_context(
    phase301: dict[str, Any],
    names: tuple[str, ...],
    timestamp_key: str,
    value_key: str,
) -> tuple[list[int], list[float], str | None]:
    for name in names:
        item = phase301["datasets"].get(name)
        if not item:
            continue
        path = ROOT / item["path"]
        rows = read_csv_gz(path)
        timestamps: list[int] = []
        values: list[float] = []
        for row in rows:
            value = to_float(row.get(value_key))
            if value is None:
                continue
            timestamps.append(int(row[timestamp_key]))
            values.append(value)
        ordered = sorted(zip(timestamps, values))
        return [item[0] for item in ordered], [item[1] for item in ordered], name
    return [], [], None


def feature_registry() -> list[dict[str, Any]]:
    return [
        {
            "feature_id": "return_1h",
            "family": "price",
            "definition": "log(close_t / close_t-1)",
            "source": "primary hourly candle close",
            "available_lag_hours": 1,
        },
        {
            "feature_id": "return_4h",
            "family": "price",
            "definition": "log(close_t / close_t-4)",
            "source": "primary hourly candle close",
            "available_lag_hours": 1,
        },
        {
            "feature_id": "return_24h",
            "family": "price",
            "definition": "log(close_t / close_t-24)",
            "source": "primary hourly candle close",
            "available_lag_hours": 1,
        },
        {
            "feature_id": "realized_vol_24h",
            "family": "volatility",
            "definition": "population std of 1h log returns over 24 closed candles",
            "source": "return_1h",
            "available_lag_hours": 1,
        },
        {
            "feature_id": "realized_vol_168h",
            "family": "volatility",
            "definition": "population std of 1h log returns over 168 closed candles",
            "source": "return_1h",
            "available_lag_hours": 1,
        },
        {
            "feature_id": "volume_z_24h",
            "family": "volume",
            "definition": "z-score of base volume over 24 closed candles",
            "source": "primary hourly candle volume",
            "available_lag_hours": 1,
        },
        {
            "feature_id": "volume_z_168h",
            "family": "volume",
            "definition": "z-score of base volume over 168 closed candles",
            "source": "primary hourly candle volume",
            "available_lag_hours": 1,
        },
        {
            "feature_id": "range_pct",
            "family": "liquidity_proxy",
            "definition": "(high-low)/close",
            "source": "primary hourly candle OHLC",
            "available_lag_hours": 1,
        },
        {
            "feature_id": "close_location",
            "family": "price",
            "definition": "(close-low)/(high-low), clipped by valid OHLC",
            "source": "primary hourly candle OHLC",
            "available_lag_hours": 1,
        },
        {
            "feature_id": "illiquidity_proxy",
            "family": "liquidity_proxy",
            "definition": "abs(return_1h)/quote_volume",
            "source": "return and quote volume",
            "available_lag_hours": 1,
        },
        {
            "feature_id": "sma_distance_24h",
            "family": "price",
            "definition": "close/SMA24-1",
            "source": "primary hourly candle close",
            "available_lag_hours": 1,
        },
        {
            "feature_id": "sma_distance_168h",
            "family": "price",
            "definition": "close/SMA168-1",
            "source": "primary hourly candle close",
            "available_lag_hours": 1,
        },
        {
            "feature_id": "funding_rate_asof",
            "family": "derivatives",
            "definition": "latest settled funding rate at or before candle close",
            "source": "public no-auth funding history",
            "available_lag_hours": 0,
        },
        {
            "feature_id": "funding_mean_3",
            "family": "derivatives",
            "definition": "mean of latest three settled funding observations",
            "source": "funding_rate_asof",
            "available_lag_hours": 0,
        },
        {
            "feature_id": "funding_mean_21",
            "family": "derivatives",
            "definition": "mean of latest 21 settled funding observations",
            "source": "funding_rate_asof",
            "available_lag_hours": 0,
        },
        {
            "feature_id": "open_interest_asof",
            "family": "derivatives",
            "definition": "latest public open interest observation at or before candle close",
            "source": "public no-auth open-interest history",
            "available_lag_hours": 1,
        },
        {
            "feature_id": "open_interest_change_1h",
            "family": "derivatives",
            "definition": "open_interest_asof / lag1 - 1",
            "source": "open_interest_asof",
            "available_lag_hours": 1,
        },
        {
            "feature_id": "open_interest_change_24h",
            "family": "derivatives",
            "definition": "open_interest_asof / lag24 - 1",
            "source": "open_interest_asof",
            "available_lag_hours": 1,
        },
    ]


def build(
    phase301_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    phase301 = read_json(phase301_path)
    if phase301.get("phase") != 301 or not phase301.get("complete"):
        raise RuntimeError("Phase 301 artifact is not complete.")
    primary_name, primary_path = _select_primary_dataset(phase301)
    candle_rows = read_csv_gz(primary_path)
    candle_rows.sort(key=lambda row: int(row["open_time_ms"]))
    timestamps = [int(row["open_time_ms"]) for row in candle_rows]
    opens = _float_column(candle_rows, "open")
    highs = _float_column(candle_rows, "high")
    lows = _float_column(candle_rows, "low")
    closes = _float_column(candle_rows, "close")
    volumes = _float_column(candle_rows, "volume")
    quote_volumes = _float_column(candle_rows, "quote_volume")

    return_1h = lag_return(closes, 1)
    return_4h = lag_return(closes, 4)
    return_24h = lag_return(closes, 24)
    realized_vol_24h = rolling_std(return_1h, 24)
    realized_vol_168h = rolling_std(return_1h, 168)
    volume_z_24h = _zscore(volumes, 24)
    volume_z_168h = _zscore(volumes, 168)
    sma24 = rolling_mean(closes, 24)
    sma168 = rolling_mean(closes, 168)

    funding_ts, funding_values, funding_source = _load_context(
        phase301,
        ("binance_funding", "bybit_funding"),
        "funding_time_ms",
        "funding_rate",
    )
    funding_asof = merge_asof(timestamps, funding_ts, funding_values) if funding_ts else [None] * len(timestamps)
    funding_mean_3 = rolling_mean(funding_asof, 3)
    funding_mean_21 = rolling_mean(funding_asof, 21)

    oi_ts, oi_values, oi_source = _load_context(
        phase301,
        ("bybit_open_interest",),
        "timestamp_ms",
        "open_interest",
    )
    oi_asof = merge_asof(timestamps, oi_ts, oi_values) if oi_ts else [None] * len(timestamps)

    rows: list[dict[str, Any]] = []
    for index, raw in enumerate(candle_rows):
        candle_range = highs[index] - lows[index]
        range_pct = candle_range / closes[index] if closes[index] else None
        close_location = (
            (closes[index] - lows[index]) / candle_range if candle_range > 0 else 0.5
        )
        illiquidity = (
            abs(return_1h[index]) / quote_volumes[index]
            if return_1h[index] is not None and quote_volumes[index] > 0
            else None
        )
        oi_change_1h = None
        oi_change_24h = None
        if oi_asof[index] is not None:
            if index >= 1 and oi_asof[index - 1] not in (None, 0):
                oi_change_1h = oi_asof[index] / oi_asof[index - 1] - 1.0
            if index >= 24 and oi_asof[index - 24] not in (None, 0):
                oi_change_24h = oi_asof[index] / oi_asof[index - 24] - 1.0
        rows.append(
            {
                "open_time_ms": timestamps[index],
                "open_time_utc": raw["open_time_utc"],
                "open": opens[index],
                "high": highs[index],
                "low": lows[index],
                "close": closes[index],
                "volume": volumes[index],
                "quote_volume": quote_volumes[index],
                "return_1h": return_1h[index],
                "return_4h": return_4h[index],
                "return_24h": return_24h[index],
                "realized_vol_24h": realized_vol_24h[index],
                "realized_vol_168h": realized_vol_168h[index],
                "volume_z_24h": volume_z_24h[index],
                "volume_z_168h": volume_z_168h[index],
                "range_pct": range_pct,
                "close_location": close_location,
                "illiquidity_proxy": illiquidity,
                "sma_distance_24h": (
                    closes[index] / sma24[index] - 1.0 if sma24[index] not in (None, 0) else None
                ),
                "sma_distance_168h": (
                    closes[index] / sma168[index] - 1.0 if sma168[index] not in (None, 0) else None
                ),
                "funding_rate_asof": funding_asof[index],
                "funding_mean_3": funding_mean_3[index],
                "funding_mean_21": funding_mean_21[index],
                "open_interest_asof": oi_asof[index],
                "open_interest_change_1h": oi_change_1h,
                "open_interest_change_24h": oi_change_24h,
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    matrix_path = output_dir / "phase302_feature_matrix_v2.csv.gz"
    write_csv_gz(matrix_path, rows, FEATURE_FIELDS)
    registry = feature_registry()
    missingness: dict[str, float] = {}
    for item in registry:
        key = item["feature_id"]
        missing = sum(row.get(key) in (None, "") for row in rows)
        missingness[key] = missing / len(rows) if rows else 1.0

    payload = base_payload(302, "CONTROLLED_FEATURE_REGISTRY_V2_READY_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE302_CONTROLLED_FEATURE_REGISTRY_V2_READY_RESEARCH_ONLY",
            "phase301_artifact": phase301_path.relative_to(ROOT).as_posix(),
            "phase301_fingerprint": phase301["artifact_fingerprint"],
            "primary_candle_dataset": primary_name,
            "primary_candle_path": primary_path.relative_to(ROOT).as_posix(),
            "matrix_path": matrix_path.relative_to(ROOT).as_posix(),
            "matrix_sha256": sha256_file(matrix_path),
            "row_count": len(rows),
            "feature_count": len(registry),
            "feature_registry": registry,
            "missingness": missingness,
            "funding_source": funding_source,
            "open_interest_source": oi_source,
            "future_leakage_allowed": False,
            "features_use_closed_or_settled_data_only": True,
            "feature_selection_performed": False,
            "strategy_approved": False,
        }
    )
    from crypto_decision_lab.scripts.phase301_305_evidence_v2_common import fingerprint

    payload["artifact_fingerprint"] = fingerprint(payload)
    artifact_path = output_dir / "phase302_controlled_feature_registry_v2.json"
    write_json(artifact_path, payload)
    write_text(
        ROOT / "docs/reports/evidence_v2/phase302_controlled_feature_registry_v2_summary.md",
        f"""# Phase 302 — Controlled Feature Registry v2

Gate: `{payload["gate"]}`

- Primary dataset: `{primary_name}`
- Rows: `{len(rows)}`
- Registered features: `{len(registry)}`
- Funding source: `{funding_source}`
- Open-interest source: `{oi_source}`
- Closed or settled data only: `True`
- Future leakage allowed: `False`
- Feature selection performed: `False`
- Strategy approved: `False`
- Operational: `BLOCKED_RESEARCH_ONLY`
- Action: `NO_ACTION_RESEARCH_ONLY`

The registry records price, volume, volatility, liquidity proxies and public
derivatives context with explicit lineage. Registration does not prove edge.
""",
    )
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase301-artifact",
        type=Path,
        default=ROOT
        / "artifacts/phase301_official_public_history_extension_research_only/"
        "phase301_official_public_history_extension.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "artifacts/phase302_controlled_feature_registry_v2_research_only",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build(args.phase301_artifact, args.output_dir)
    print(payload["gate"])
    print("Rows:", payload["row_count"])
    print("Features:", payload["feature_count"])
    print("Future leakage allowed:", payload["future_leakage_allowed"])
    print("Operational:", payload["locks"]["operational_status"])
    print("Action:", payload["locks"]["action_status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
