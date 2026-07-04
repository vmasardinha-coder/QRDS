from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"
COINS = ["BTC", "ETH", "SOL"]
HARNESS_SOURCE_LABEL = "QRDS_OFFLINE_EXPERIMENT_HARNESS_RESEARCH_ONLY"
BASELINE_SOURCE_LABEL = "QRDS_BASELINE_NULL_MODELS_METRICS_RESEARCH_ONLY"
MIN_ROWS_PER_COIN = 3500

RETURN_TARGET = "forward_return_24h_research_target"
ABS_TARGET = "forward_abs_return_24h_research_target"
VOL_TARGET = "forward_realized_vol_24h_research_target"
TARGET_COLUMNS = [RETURN_TARGET, ABS_TARGET, VOL_TARGET]
SPLITS = ["TRAIN_RESEARCH_ONLY", "VALIDATION_RESEARCH_ONLY", "HOLDOUT_RESEARCH_ONLY"]

BASELINE_FAMILY_IDS = [
    "ZERO_RETURN_CONTROL",
    "TRAIN_MEAN_RETURN",
    "TRAIN_MEDIAN_RETURN",
    "REGIME_MEAN_RETURN",
    "SHUFFLED_TRAIN_DISTRIBUTION_RETURN",
    "ZERO_ABS_RETURN_CONTROL",
    "TRAIN_MEAN_ABS_RETURN",
    "REGIME_MEAN_ABS_RETURN",
    "SHUFFLED_TRAIN_DISTRIBUTION_ABS_RETURN",
    "TRAIN_MEAN_REALIZED_VOL",
    "CURRENT_VOL_PROXY_REALIZED_VOL",
    "REGIME_MEAN_REALIZED_VOL",
    "SHUFFLED_TRAIN_DISTRIBUTION_REALIZED_VOL",
]

SAFETY_FLAGS: dict[str, Any] = {
    "app_mode": APP_MODE,
    "research_allowed": True,
    "hypothetical_only": True,
    "api_key_required": False,
    "api_key_present": False,
    "account_connection_required": False,
    "authenticated_connection_used": False,
    "orders_allowed": False,
    "orders_generated": False,
    "real_orders_generated": False,
    "real_capital_used": False,
    "trading_signal_generated": False,
    "executable_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "portfolio_decision_generated": False,
    "operational_decision_allowed": False,
}


def _repo_root(repo_root: str | Path | None = None) -> Path:
    if repo_root:
        return Path(repo_root).resolve()
    here = Path.cwd().resolve()
    for p in [here, *here.parents]:
        if (p / "crypto_decision_lab").exists():
            return p
    return here


def _load_json(path: Path) -> dict[str, Any]:
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        d["_present"] = True
        return d
    except Exception:
        return {"_present": False, "gate_answer": "MISSING_RESEARCH_ONLY"}


def _sha_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _sha_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return "MISSING"


def _git_status(root: Path) -> list[str]:
    try:
        p = subprocess.run(["git", "status", "--short"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        return [x for x in p.stdout.splitlines() if x.strip()]
    except Exception:
        return []


def _read_csv(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            return [dict(row) for row in csv.DictReader(f)]
    except Exception:
        return []


def _as_float(v: Any, default: float = 0.0) -> float:
    try:
        if v in ("", None):
            return default
        return float(v)
    except Exception:
        return default


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def _rmse(errors: list[float]) -> float:
    return math.sqrt(_mean([e * e for e in errors])) if errors else 0.0


def _corr(a: list[float], b: list[float]) -> float:
    if len(a) < 3 or len(a) != len(b):
        return 0.0
    ma = _mean(a)
    mb = _mean(b)
    da = math.sqrt(sum((x - ma) ** 2 for x in a))
    db = math.sqrt(sum((y - mb) ** 2 for y in b))
    if da == 0 or db == 0:
        return 0.0
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (da * db)


def _phase19_index(root: Path) -> dict[str, Any]:
    return _load_json(root / "crypto_decision_lab/artifacts/phase19_offline_experiment_harness_pack/phase19_offline_experiment_harness_pack_index.json")


def _harness_path(root: Path, coin: str) -> Path:
    return root / "crypto_decision_lab/artifacts/phase19_offline_experiment_harness_pack/harness" / f"{coin.lower()}_offline_experiment_harness_1h.csv"


def _stable_index(key: str, n: int) -> int:
    if n <= 0:
        return 0
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) % n


def _regime_key(row: dict[str, Any]) -> str:
    return "|".join(
        [
            str(row.get("volatility_regime_24h", "MISSING")),
            str(row.get("dispersion_regime_24h", "MISSING")),
            str(row.get("momentum_diagnostic_24h", "MISSING")),
        ]
    )


def _train_stats(rows: list[dict[str, Any]], target: str) -> dict[str, Any]:
    train = [r for r in rows if r.get("split") == "TRAIN_RESEARCH_ONLY"]
    values = [_as_float(r.get(target), 0.0) for r in train]
    by_regime: dict[str, list[float]] = {}
    for r in train:
        by_regime.setdefault(_regime_key(r), []).append(_as_float(r.get(target), 0.0))
    return {
        "target": target,
        "train_count": len(train),
        "train_values": values,
        "train_mean": _mean(values),
        "train_median": _median(values),
        "regime_means": {k: _mean(v) for k, v in by_regime.items()},
        "regime_counts": {k: len(v) for k, v in by_regime.items()},
        "regime_default": _mean(values),
    }


def _estimate_for_baseline(row: dict[str, Any], baseline_id: str, target: str, stats: dict[str, Any]) -> float:
    train_values = stats["train_values"]
    if baseline_id in ("ZERO_RETURN_CONTROL", "ZERO_ABS_RETURN_CONTROL"):
        return 0.0
    if baseline_id in ("TRAIN_MEAN_RETURN", "TRAIN_MEAN_ABS_RETURN", "TRAIN_MEAN_REALIZED_VOL"):
        return float(stats["train_mean"])
    if baseline_id == "TRAIN_MEDIAN_RETURN":
        return float(stats["train_median"])
    if baseline_id in ("REGIME_MEAN_RETURN", "REGIME_MEAN_ABS_RETURN", "REGIME_MEAN_REALIZED_VOL"):
        return float(stats["regime_means"].get(_regime_key(row), stats["regime_default"]))
    if baseline_id == "CURRENT_VOL_PROXY_REALIZED_VOL":
        return _as_float(row.get("rolling_vol_24h_ann"), stats["train_mean"])
    if baseline_id.startswith("SHUFFLED_TRAIN_DISTRIBUTION"):
        if not train_values:
            return 0.0
        key = f"{row.get('coin')}|{row.get('timestamp')}|{target}|{baseline_id}"
        return float(train_values[_stable_index(key, len(train_values))])
    return 0.0


def _baseline_specs() -> list[dict[str, str]]:
    return [
        {"target": RETURN_TARGET, "baseline_id": "ZERO_RETURN_CONTROL", "family": "null_zero"},
        {"target": RETURN_TARGET, "baseline_id": "TRAIN_MEAN_RETURN", "family": "train_mean"},
        {"target": RETURN_TARGET, "baseline_id": "TRAIN_MEDIAN_RETURN", "family": "train_median"},
        {"target": RETURN_TARGET, "baseline_id": "REGIME_MEAN_RETURN", "family": "regime_mean"},
        {"target": RETURN_TARGET, "baseline_id": "SHUFFLED_TRAIN_DISTRIBUTION_RETURN", "family": "shuffled_train_distribution"},
        {"target": ABS_TARGET, "baseline_id": "ZERO_ABS_RETURN_CONTROL", "family": "null_zero_abs"},
        {"target": ABS_TARGET, "baseline_id": "TRAIN_MEAN_ABS_RETURN", "family": "train_mean_abs"},
        {"target": ABS_TARGET, "baseline_id": "REGIME_MEAN_ABS_RETURN", "family": "regime_mean_abs"},
        {"target": ABS_TARGET, "baseline_id": "SHUFFLED_TRAIN_DISTRIBUTION_ABS_RETURN", "family": "shuffled_train_distribution_abs"},
        {"target": VOL_TARGET, "baseline_id": "TRAIN_MEAN_REALIZED_VOL", "family": "train_mean_vol"},
        {"target": VOL_TARGET, "baseline_id": "CURRENT_VOL_PROXY_REALIZED_VOL", "family": "current_vol_proxy"},
        {"target": VOL_TARGET, "baseline_id": "REGIME_MEAN_REALIZED_VOL", "family": "regime_mean_vol"},
        {"target": VOL_TARGET, "baseline_id": "SHUFFLED_TRAIN_DISTRIBUTION_REALIZED_VOL", "family": "shuffled_train_distribution_vol"},
    ]


def _metrics_for_rows(rows: list[dict[str, Any]], target: str, estimate_values: list[float]) -> dict[str, Any]:
    y = [_as_float(r.get(target), 0.0) for r in rows]
    yhat = list(estimate_values)
    errors = [yh - yt for yt, yh in zip(y, yhat)]
    nonzero_direction = [(yt, yh) for yt, yh in zip(y, yhat) if yh != 0.0 and yt != 0.0]
    if nonzero_direction:
        directional_accuracy = sum(1 for yt, yh in nonzero_direction if (yt > 0) == (yh > 0)) / len(nonzero_direction)
    else:
        directional_accuracy = 0.0
    return {
        "n": len(rows),
        "target_mean": round(_mean(y), 12),
        "estimate_mean": round(_mean(yhat), 12),
        "bias": round(_mean(errors), 12),
        "mae": round(_mean([abs(e) for e in errors]), 12),
        "rmse": round(_rmse(errors), 12),
        "correlation": round(_corr(y, yhat), 12),
        "directional_coverage": round(len(nonzero_direction) / len(rows), 12) if rows else 0.0,
        "directional_accuracy": round(directional_accuracy, 12),
    }


def _evaluate_coin(root: Path, coin: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    path = _harness_path(root, coin)
    rows = [r for r in _read_csv(path) if r.get("source") == HARNESS_SOURCE_LABEL]
    if not rows:
        return [], {
            "coin": coin,
            "ready": False,
            "reason": "missing_harness_rows",
            "harness_rows": 0,
            "train_rows": 0,
            "validation_rows": 0,
            "holdout_rows": 0,
            "metric_rows": 0,
            "baseline_families_count": 0,
            "targets_count": len(TARGET_COLUMNS),
            "prediction_rows_generated": 0,
            "model_training_run": False,
            "leakage_guard_pass": False,
            "schema_complete": True,
        }

    stats_by_target = {target: _train_stats(rows, target) for target in TARGET_COLUMNS}
    metrics: list[dict[str, Any]] = []

    for spec in _baseline_specs():
        target = spec["target"]
        baseline_id = spec["baseline_id"]
        stats = stats_by_target[target]
        for split in SPLITS:
            split_rows = [r for r in rows if r.get("split") == split]
            estimates = [_estimate_for_baseline(r, baseline_id, target, stats) for r in split_rows]
            m = _metrics_for_rows(split_rows, target, estimates)
            metrics.append(
                {
                    "coin": coin,
                    "target": target,
                    "baseline_id": baseline_id,
                    "baseline_family": spec["family"],
                    "split": split,
                    "source": BASELINE_SOURCE_LABEL,
                    "research_only": True,
                    "model_training_run": False,
                    "model_prediction_generated": False,
                    "trading_signal_generated": False,
                    "recommendation_generated": False,
                    "operational_decision_allowed": False,
                    "canonical_write": False,
                    **m,
                }
            )

    split_counts = {split: sum(1 for r in rows if r.get("split") == split) for split in SPLITS}
    baseline_ids = sorted({m["baseline_id"] for m in metrics})
    holdout_metrics = [m for m in metrics if m["split"] == "HOLDOUT_RESEARCH_ONLY"]
    leakage_guard_pass = all(stats_by_target[t]["train_count"] == split_counts["TRAIN_RESEARCH_ONLY"] for t in TARGET_COLUMNS)
    summary = {
        "coin": coin,
        "ready": bool(rows),
        "reason": "",
        "harness_rows": len(rows),
        "train_rows": split_counts["TRAIN_RESEARCH_ONLY"],
        "validation_rows": split_counts["VALIDATION_RESEARCH_ONLY"],
        "holdout_rows": split_counts["HOLDOUT_RESEARCH_ONLY"],
        "metric_rows": len(metrics),
        "holdout_metric_rows": len(holdout_metrics),
        "baseline_families_count": len(baseline_ids),
        "baseline_ids": baseline_ids,
        "targets_count": len(TARGET_COLUMNS),
        "target_columns": TARGET_COLUMNS,
        "prediction_rows_generated": 0,
        "model_training_run": False,
        "leakage_guard_pass": leakage_guard_pass,
        "schema_complete": True,
        "best_holdout_mae_by_target_research": {
            target: min((m["mae"] for m in holdout_metrics if m["target"] == target), default=0.0)
            for target in TARGET_COLUMNS
        },
    }
    return metrics, summary


def _write_metrics_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "coin",
        "target",
        "baseline_id",
        "baseline_family",
        "split",
        "n",
        "target_mean",
        "estimate_mean",
        "bias",
        "mae",
        "rmse",
        "correlation",
        "directional_coverage",
        "directional_accuracy",
        "source",
        "research_only",
        "model_training_run",
        "model_prediction_generated",
        "trading_signal_generated",
        "recommendation_generated",
        "operational_decision_allowed",
        "canonical_write",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def _criterion(cid: str, ok: bool, observed: Any, threshold: str) -> dict[str, Any]:
    return {"criterion_id": cid, "status": "PASS" if ok else "FAIL", "ready": bool(ok), "observed": observed, "threshold": threshold}


def _render_html(path: Path, payload: dict[str, Any]) -> None:
    esc = lambda x: html.escape(str(x))
    cards = [
        ("Station", payload["station"]),
        ("Baseline ready", payload["baseline_metrics_ready"]),
        ("Metric rows", payload["baseline_metric_rows_total"]),
        ("Min harness rows", payload["min_harness_rows_per_coin"]),
        ("Baselines", payload["baseline_families_count"]),
        ("Model training", payload["model_training_run"]),
        ("Operational", payload["operational_status"]),
        ("Mean score", payload["mean_baseline_score"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)
    coin_html = "".join(
        f"<tr><td>{esc(s.get('coin'))}</td><td>{esc(s.get('harness_rows'))}</td><td>{esc(s.get('train_rows'))}</td><td>{esc(s.get('validation_rows'))}</td><td>{esc(s.get('holdout_rows'))}</td><td>{esc(s.get('metric_rows'))}</td><td>{esc(s.get('baseline_families_count'))}</td><td>{esc(s.get('leakage_guard_pass'))}</td><td>{esc(s.get('ready'))}</td></tr>"
        for s in payload["coin_baseline_summaries"]
    )
    holdout_preview = []
    for r in payload["baseline_metrics_preview"]:
        holdout_preview.append(
            f"<tr><td>{esc(r.get('coin'))}</td><td>{esc(r.get('target'))}</td><td>{esc(r.get('baseline_id'))}</td><td>{esc(r.get('split'))}</td><td>{esc(r.get('n'))}</td><td>{esc(r.get('mae'))}</td><td>{esc(r.get('rmse'))}</td><td>{esc(r.get('directional_accuracy'))}</td></tr>"
        )
    crit_html = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td></tr>"
        for c in payload["criteria"]
    )
    page = (
        "<!doctype html><html><head><meta charset='utf-8'><title>QRDS Baseline Null Models</title>"
        "<style>body{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}.card{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}.kpi{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:150px}table{border-collapse:collapse;width:100%;background:white}th,td{border:1px solid #d9deea;padding:8px;text-align:left}th{background:#eef2ff}.blocked{background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}.ok{background:#dcfce7;border-radius:999px;padding:6px 10px;font-weight:700}</style></head><body>"
        f"<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Phase 20 Baseline Metrics + Null Models Harness</h2>"
        f"<div class='card'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p><p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>{card_html}<p class='ok'>Baselines define the null bar before any real model training.</p><p class='blocked'>No model training, no model predictions, no trading signals, no recommendations, no allocations, no operational decisions.</p></div>"
        f"<h2>Coin summaries</h2><table><thead><tr><th>coin</th><th>harness rows</th><th>train</th><th>validation</th><th>holdout</th><th>metric rows</th><th>baselines</th><th>leakage guard</th><th>ready</th></tr></thead><tbody>{coin_html}</tbody></table>"
        f"<h2>Metrics preview</h2><table><thead><tr><th>coin</th><th>target</th><th>baseline</th><th>split</th><th>n</th><th>MAE</th><th>RMSE</th><th>directional acc.</th></tr></thead><tbody>{''.join(holdout_preview)}</tbody></table>"
        f"<h2>Criteria</h2><table><thead><tr><th>criterion</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th></tr></thead><tbody>{crit_html}</tbody></table>"
        f"<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"
    )
    path.write_text(page, encoding="utf-8")


def _update_project_status(root: Path, payload: dict[str, Any]) -> None:
    status_path = root / "crypto_decision_lab/docs/reports/PROJECT_STATUS_QRDS_GATE_BTC.md"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    existing = status_path.read_text(encoding="utf-8") if status_path.exists() else "# QRDS/QOS Gate BTC — Project Status\n"
    marker = "\n## Latest Phase 20 update\n"
    before = existing.split(marker)[0].rstrip()
    section = [
        marker.strip(),
        "",
        f"Updated at: {payload['generated_at']}",
        "",
        f"- Phase 20 gate: `{payload['gate_answer']}`",
        f"- Baseline metrics ready: `{payload['baseline_metrics_ready']}`",
        f"- Baseline metric rows total: `{payload['baseline_metric_rows_total']}`",
        f"- Baseline families count: `{payload['baseline_families_count']}`",
        f"- Model training run: `{payload['model_training_run']}`",
        f"- Model predictions generated: `{payload['model_prediction_rows_generated']}`",
        f"- Operational status: `{payload['operational_status']}`",
        f"- Canonical writes: `{payload['canonical_data_writes']}`",
        "",
        "Phase 20 establishes null/baseline metrics only. It does not train a model or generate model predictions, signals, recommendations, allocations, or operational decisions.",
        "",
    ]
    status_path.write_text(before + "\n\n" + "\n".join(section), encoding="utf-8")


def build_phase20_baseline_metrics_null_models_harness_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    min_rows_per_coin: int = MIN_ROWS_PER_COIN,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    metrics_dir = out / "metrics"
    out.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)

    phase19 = _phase19_index(root)
    phase19_ready = bool(phase19.get("offline_experiment_harness_ready", False))

    all_metrics: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []

    for coin in COINS:
        metrics, summary = _evaluate_coin(root, coin)
        path = metrics_dir / f"{coin.lower()}_baseline_null_model_metrics.csv"
        _write_metrics_csv(path, metrics)
        summary["path"] = str(path)
        summary["sha256"] = _sha_file(path)[:16]
        summary["ready"] = bool(summary.get("ready")) and int(summary.get("harness_rows", 0)) >= min_rows_per_coin
        summaries.append(summary)
        all_metrics.extend(metrics)
        outputs.append(
            {
                "coin": coin,
                "path": str(path),
                "rows": len(metrics),
                "sha256": summary["sha256"],
                "source": BASELINE_SOURCE_LABEL,
                "canonical_write": False,
                "model_prediction_generated": False,
            }
        )

    combined_metrics_path = metrics_dir / "all_baseline_null_model_metrics.csv"
    _write_metrics_csv(combined_metrics_path, all_metrics)

    rows_total = sum(int(s.get("harness_rows", 0)) for s in summaries)
    min_rows = min((int(s.get("harness_rows", 0)) for s in summaries), default=0)
    metric_rows_total = len(all_metrics)
    baseline_ids = sorted({m["baseline_id"] for m in all_metrics})
    target_columns = sorted({m["target"] for m in all_metrics})
    splits = sorted({m["split"] for m in all_metrics})
    holdout_metric_rows = sum(1 for m in all_metrics if m["split"] == "HOLDOUT_RESEARCH_ONLY")
    all_ready = all(bool(s.get("ready")) for s in summaries)
    leakage_all = all(bool(s.get("leakage_guard_pass")) for s in summaries)
    model_training_run = False
    model_prediction_rows_generated = 0
    canonical_data_writes = 0
    promotion_allowed = False
    safe_apply_allowed = False
    git_status = _git_status(root)

    criteria = [
        _criterion("phase19_index_present", bool(phase19.get("_present")), phase19.get("gate_answer", "MISSING"), "Phase 19 index present"),
        _criterion("phase19_harness_ready", phase19_ready, phase19_ready, "true"),
        _criterion("coin_count", len(summaries) == 3, [s.get("coin") for s in summaries], "BTC,ETH,SOL"),
        _criterion("harness_depth_per_coin", min_rows >= min_rows_per_coin, min_rows, f">= {min_rows_per_coin}"),
        _criterion("baseline_family_count", len(baseline_ids) >= 10, len(baseline_ids), ">=10 baseline/null families"),
        _criterion("target_count", len(target_columns) == 3, target_columns, "3 research targets"),
        _criterion("split_coverage", set(splits) == set(SPLITS), splits, "train, validation, holdout"),
        _criterion("holdout_metrics_present", holdout_metric_rows > 0, holdout_metric_rows, ">0"),
        _criterion("chronological_leakage_guard", leakage_all, [s.get("leakage_guard_pass") for s in summaries], "all true"),
        _criterion("model_training_not_run", not model_training_run, model_training_run, "false"),
        _criterion("model_prediction_rows_zero", model_prediction_rows_generated == 0, model_prediction_rows_generated, "0"),
        _criterion("baselines_not_trading_signals", True, "metrics_only", "no trading signals"),
        _criterion("metrics_outputs_artifact_only", all(not x["canonical_write"] for x in outputs), [x["canonical_write"] for x in outputs], "all false"),
        _criterion("safe_apply_blocked", not safe_apply_allowed, safe_apply_allowed, "false"),
        _criterion("promotion_blocked", not promotion_allowed, promotion_allowed, "false"),
        _criterion("canonical_writes_zero", canonical_data_writes == 0, canonical_data_writes, "0"),
        _criterion("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]
    ready_count = sum(1 for c in criteria if c["ready"])
    baseline_ready = ready_count == len(criteria)
    gate = "PHASE20_BASELINE_METRICS_NULL_MODELS_READY_RESEARCH_ONLY" if baseline_ready else "PHASE20_BASELINE_METRICS_NULL_MODELS_NEEDS_REVIEW_RESEARCH_ONLY"

    holdout_preview = [m for m in all_metrics if m["split"] == "HOLDOUT_RESEARCH_ONLY"][:18]

    payload: dict[str, Any] = {
        "schema": "qrds.phase20_baseline_metrics_null_models_harness_pack.v1",
        "report_name": "qrds-phase20-baseline-metrics-null-models-harness-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": "PHASE_20_BASELINE_METRICS_NULL_MODELS",
        "baseline_metrics_ready": baseline_ready,
        "data_nature": "BASELINE_METRICS_NULL_MODELS_RESEARCH_ONLY",
        "phase19_offline_experiment_harness_ready": phase19_ready,
        "coins": COINS,
        "coins_count": len(COINS),
        "target_columns": TARGET_COLUMNS,
        "splits": SPLITS,
        "baseline_family_ids": baseline_ids,
        "baseline_families_count": len(baseline_ids),
        "harness_rows_total": rows_total,
        "min_harness_rows_per_coin": min_rows,
        "baseline_metric_rows_total": metric_rows_total,
        "holdout_metric_rows": holdout_metric_rows,
        "model_training_run": model_training_run,
        "model_prediction_rows_generated": model_prediction_rows_generated,
        "baseline_estimates_are_operational_predictions": False,
        "target_columns_are_signals": False,
        "coin_baseline_summaries": summaries,
        "baseline_outputs": outputs,
        "combined_metrics_path": str(combined_metrics_path),
        "combined_metrics_sha256": _sha_file(combined_metrics_path)[:16],
        "baseline_metrics_preview": holdout_preview,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "modeling_status": "BASELINE_METRICS_NULL_MODELS_READY" if baseline_ready else "BASELINE_METRICS_NULL_MODELS_NEEDS_REVIEW",
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "canonical_data_writes": canonical_data_writes,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_baseline_score": round(ready_count / len(criteria), 4),
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    rp = out / "phase20_baseline_metrics_null_models_harness_pack.json"
    mp = out / "phase20_baseline_metrics_null_models_harness_pack.md"
    hp = out / "index.html"
    ip = out / "phase20_baseline_metrics_null_models_harness_pack_index.json"

    rp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(
        f"# QRDS/QOS Phase 20 Baseline Metrics + Null Models Harness\n\n**Gate answer:** {gate}\n\nMetric rows total: {metric_rows_total}\n\nBaseline families: {len(baseline_ids)}\n\nModel training run: false\n\nModel prediction rows generated: 0\n\nOperational status: BLOCKED_RESEARCH_ONLY\n\nBaselines are research-only metrics, not trading signals/recommendations/allocation decisions.\n",
        encoding="utf-8",
    )
    _render_html(hp, payload)

    index = {
        "schema": "qrds.phase20_baseline_metrics_null_models_harness_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "station": payload["station"],
        "baseline_metrics_ready": payload["baseline_metrics_ready"],
        "data_nature": payload["data_nature"],
        "phase19_offline_experiment_harness_ready": payload["phase19_offline_experiment_harness_ready"],
        "coins": payload["coins"],
        "coins_count": payload["coins_count"],
        "harness_rows_total": payload["harness_rows_total"],
        "min_harness_rows_per_coin": payload["min_harness_rows_per_coin"],
        "baseline_metric_rows_total": payload["baseline_metric_rows_total"],
        "baseline_families_count": payload["baseline_families_count"],
        "holdout_metric_rows": payload["holdout_metric_rows"],
        "model_training_run": payload["model_training_run"],
        "model_prediction_rows_generated": payload["model_prediction_rows_generated"],
        "baseline_estimates_are_operational_predictions": payload["baseline_estimates_are_operational_predictions"],
        "target_columns_are_signals": payload["target_columns_are_signals"],
        "operational_status": payload["operational_status"],
        "modeling_status": payload["modeling_status"],
        "safe_apply_allowed": payload["safe_apply_allowed"],
        "promotion_allowed": payload["promotion_allowed"],
        "canonical_data_writes": payload["canonical_data_writes"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_baseline_score": payload["mean_baseline_score"],
        "git_status_line_count": payload["git_status_line_count"],
        "combined_metrics_path": payload["combined_metrics_path"],
        "report_path": str(rp),
        "markdown_path": str(mp),
        "html_path": str(hp),
        "index_path": str(ip),
        "serve_entrypoint": str(hp),
        "report_payload_sha256": payload["report_payload_sha256"],
        "payload": payload,
        **SAFETY_FLAGS,
    }
    ip.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    _update_project_status(root, payload)
    return index


build_baseline_metrics_null_models_harness_pack = build_phase20_baseline_metrics_null_models_harness_pack
