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
SPLITS = ["TRAIN_RESEARCH_ONLY", "VALIDATION_RESEARCH_ONLY", "HOLDOUT_RESEARCH_ONLY"]
HARNESS_SOURCE_LABEL = "QRDS_OFFLINE_EXPERIMENT_HARNESS_RESEARCH_ONLY"
MODEL_BENCHMARK_SOURCE_LABEL = "QRDS_INTERPRETABLE_OFFLINE_MODEL_BENCHMARK_RESEARCH_ONLY"

RETURN_TARGET = "forward_return_24h_research_target"
ABS_TARGET = "forward_abs_return_24h_research_target"
VOL_TARGET = "forward_realized_vol_24h_research_target"
TARGET_COLUMNS = [RETURN_TARGET, ABS_TARGET, VOL_TARGET]

MIN_ROWS_PER_COIN = 3500
RIDGE_LAMBDA = 1.0

MODEL_SPECS: list[dict[str, Any]] = [
    {
        "model_id": "LINEAR_RETURN_MOMENTUM_24H",
        "target": RETURN_TARGET,
        "features": ["momentum_sum_24h"],
        "family": "interpretable_univariate_linear",
    },
    {
        "model_id": "LINEAR_RETURN_MOMENTUM_VOL_DISP",
        "target": RETURN_TARGET,
        "features": ["momentum_sum_24h", "momentum_sum_168h", "rolling_vol_24h_ann", "dispersion_bps_mean_24h", "drawdown_from_peak"],
        "family": "interpretable_multifeature_linear",
    },
    {
        "model_id": "LINEAR_ABS_RETURN_VOL_DISP",
        "target": ABS_TARGET,
        "features": ["rolling_vol_24h_ann", "rolling_vol_168h_ann", "dispersion_bps_mean_24h", "return_24h_min", "return_24h_max"],
        "family": "interpretable_volatility_proxy_linear",
    },
    {
        "model_id": "LINEAR_REALIZED_VOL_CURRENT_VOL",
        "target": VOL_TARGET,
        "features": ["rolling_vol_24h_ann"],
        "family": "interpretable_univariate_vol_proxy",
    },
    {
        "model_id": "LINEAR_REALIZED_VOL_MULTI",
        "target": VOL_TARGET,
        "features": ["rolling_vol_24h_ann", "rolling_vol_168h_ann", "rolling_vol_720h_ann", "dispersion_bps_mean_24h", "return_24h_min", "return_24h_max"],
        "family": "interpretable_multifeature_vol_proxy",
    },
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


def _read_csv(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            return [dict(row) for row in csv.DictReader(f)]
    except Exception:
        return []


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


def _stdev(values: list[float]) -> float:
    return statistics.stdev(values) if len(values) >= 2 else 0.0


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


def _phase20_index(root: Path) -> dict[str, Any]:
    return _load_json(root / "crypto_decision_lab/artifacts/phase20_baseline_metrics_null_models_harness_pack/phase20_baseline_metrics_null_models_harness_pack_index.json")


def _harness_path(root: Path, coin: str) -> Path:
    return root / "crypto_decision_lab/artifacts/phase19_offline_experiment_harness_pack/harness" / f"{coin.lower()}_offline_experiment_harness_1h.csv"


def _default_phase20_metrics_path(root: Path) -> Path:
    return root / "crypto_decision_lab/artifacts/phase20_baseline_metrics_null_models_harness_pack/metrics/all_baseline_null_model_metrics.csv"


def _baseline_metrics_path(root: Path, phase20: dict[str, Any]) -> Path:
    raw = phase20.get("combined_metrics_path")
    if raw:
        return Path(raw)
    return _default_phase20_metrics_path(root)


def _metric_key(coin: str, target: str, split: str) -> tuple[str, str, str]:
    return (coin, target, split)


def _audit_phase20(root: Path, phase20: dict[str, Any]) -> dict[str, Any]:
    path = _baseline_metrics_path(root, phase20)
    rows = _read_csv(path)
    best_mae: dict[tuple[str, str, str], float] = {}
    best_baseline: dict[tuple[str, str, str], str] = {}

    for row in rows:
        coin = str(row.get("coin", ""))
        target = str(row.get("target", ""))
        split = str(row.get("split", ""))
        key = _metric_key(coin, target, split)
        mae = _as_float(row.get("mae"), 0.0)
        if key not in best_mae or mae < best_mae[key]:
            best_mae[key] = mae
            best_baseline[key] = str(row.get("baseline_id", ""))

    coins = sorted({str(r.get("coin", "")) for r in rows if r.get("coin")})
    targets = sorted({str(r.get("target", "")) for r in rows if r.get("target")})
    splits = sorted({str(r.get("split", "")) for r in rows if r.get("split")})
    baseline_ids = sorted({str(r.get("baseline_id", "")) for r in rows if r.get("baseline_id")})
    phase20_ready = bool(phase20.get("baseline_metrics_ready", False))

    expected_comparison_keys = len(COINS) * len(TARGET_COLUMNS) * len(SPLITS)
    return {
        "phase20_index_present": bool(phase20.get("_present")),
        "phase20_gate_answer": phase20.get("gate_answer", "MISSING_RESEARCH_ONLY"),
        "phase20_baseline_metrics_ready": phase20_ready,
        "phase20_metrics_path": str(path),
        "phase20_metric_rows": len(rows),
        "phase20_coins": coins,
        "phase20_targets": targets,
        "phase20_splits": splits,
        "phase20_baseline_ids": baseline_ids,
        "phase20_baseline_family_count": len(baseline_ids),
        "phase20_best_mae_key_count": len(best_mae),
        "phase20_expected_best_mae_key_count": expected_comparison_keys,
        "phase20_model_training_run": bool(phase20.get("model_training_run", False)),
        "phase20_model_prediction_rows_generated": int(phase20.get("model_prediction_rows_generated", 0) or 0),
        "best_mae": {f"{a}|{b}|{c}": v for (a, b, c), v in best_mae.items()},
        "best_baseline": {f"{a}|{b}|{c}": v for (a, b, c), v in best_baseline.items()},
        "audit_ready": bool(
            phase20_ready
            and len(rows) >= 100
            and set(coins) >= set(COINS)
            and set(targets) >= set(TARGET_COLUMNS)
            and set(splits) >= set(SPLITS)
            and len(baseline_ids) >= 10
            and len(best_mae) >= expected_comparison_keys
            and not bool(phase20.get("model_training_run", False))
            and int(phase20.get("model_prediction_rows_generated", 0) or 0) == 0
        ),
    }


def _load_harness_rows(root: Path, coin: str) -> list[dict[str, Any]]:
    return [r for r in _read_csv(_harness_path(root, coin)) if r.get("source") == HARNESS_SOURCE_LABEL]


def _solve_linear_system(a: list[list[float]], b: list[float]) -> list[float]:
    n = len(b)
    if n == 0:
        return []
    mat = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(mat[r][col]))
        if abs(mat[pivot][col]) < 1e-12:
            mat[pivot][col] = 1e-12
        if pivot != col:
            mat[col], mat[pivot] = mat[pivot], mat[col]
        div = mat[col][col]
        if abs(div) < 1e-12:
            div = 1e-12
        mat[col] = [x / div for x in mat[col]]
        for r in range(n):
            if r == col:
                continue
            factor = mat[r][col]
            if factor == 0:
                continue
            mat[r] = [rv - factor * cv for rv, cv in zip(mat[r], mat[col])]
    return [mat[i][-1] for i in range(n)]


def _fit_ridge(train_rows: list[dict[str, Any]], target: str, features: list[str]) -> dict[str, Any]:
    means: dict[str, float] = {}
    stds: dict[str, float] = {}
    for f in features:
        vals = [_as_float(r.get(f), 0.0) for r in train_rows]
        means[f] = _mean(vals)
        sd = _stdev(vals)
        stds[f] = sd if sd > 1e-12 else 1.0

    p = len(features) + 1
    xtx = [[0.0 for _ in range(p)] for _ in range(p)]
    xty = [0.0 for _ in range(p)]

    for r in train_rows:
        x = [1.0] + [(_as_float(r.get(f), 0.0) - means[f]) / stds[f] for f in features]
        y = _as_float(r.get(target), 0.0)
        for i in range(p):
            xty[i] += x[i] * y
            for j in range(p):
                xtx[i][j] += x[i] * x[j]

    for i in range(1, p):
        xtx[i][i] += RIDGE_LAMBDA

    beta = _solve_linear_system(xtx, xty)
    return {"target": target, "features": features, "means": means, "stds": stds, "beta": beta}


def _predict(model: dict[str, Any], row: dict[str, Any]) -> float:
    beta = model["beta"]
    features = model["features"]
    if not beta:
        return 0.0
    yhat = beta[0]
    for idx, f in enumerate(features, start=1):
        yhat += beta[idx] * ((_as_float(row.get(f), 0.0) - model["means"][f]) / model["stds"][f])
    return float(yhat)


def _metrics_for_rows(rows: list[dict[str, Any]], target: str, predictions: list[float]) -> dict[str, Any]:
    y = [_as_float(r.get(target), 0.0) for r in rows]
    yhat = list(predictions)
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


def _evaluate_coin_models(root: Path, coin: str, audit: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows = _load_harness_rows(root, coin)
    if not rows:
        return [], [], {
            "coin": coin,
            "ready": False,
            "reason": "missing_harness_rows",
            "harness_rows": 0,
            "train_rows": 0,
            "validation_rows": 0,
            "holdout_rows": 0,
            "model_metric_rows": 0,
            "coefficient_rows": 0,
            "model_count": 0,
            "baseline_comparison_coverage": 0.0,
            "holdout_models_beating_best_baseline_count": 0,
            "model_training_run": False,
            "model_prediction_rows_generated": 0,
            "schema_complete": True,
        }

    train_rows = [r for r in rows if r.get("split") == "TRAIN_RESEARCH_ONLY"]
    model_metrics: list[dict[str, Any]] = []
    coefficients: list[dict[str, Any]] = []
    best_mae = audit.get("best_mae", {})
    best_baseline = audit.get("best_baseline", {})

    for spec in MODEL_SPECS:
        model = _fit_ridge(train_rows, spec["target"], spec["features"])
        beta = model["beta"]
        coefficients.append(
            {
                "coin": coin,
                "model_id": spec["model_id"],
                "target": spec["target"],
                "feature": "INTERCEPT_STANDARDIZED_SPACE",
                "coefficient": round(beta[0] if beta else 0.0, 12),
                "source": MODEL_BENCHMARK_SOURCE_LABEL,
                "research_only": True,
                "model_training_run": True,
                "trading_signal_generated": False,
                "recommendation_generated": False,
                "operational_decision_allowed": False,
                "canonical_write": False,
            }
        )
        for idx, f in enumerate(spec["features"], start=1):
            coefficients.append(
                {
                    "coin": coin,
                    "model_id": spec["model_id"],
                    "target": spec["target"],
                    "feature": f,
                    "coefficient": round(beta[idx] if idx < len(beta) else 0.0, 12),
                    "source": MODEL_BENCHMARK_SOURCE_LABEL,
                    "research_only": True,
                    "model_training_run": True,
                    "trading_signal_generated": False,
                    "recommendation_generated": False,
                    "operational_decision_allowed": False,
                    "canonical_write": False,
                }
            )

        for split in SPLITS:
            split_rows = [r for r in rows if r.get("split") == split]
            preds = [_predict(model, r) for r in split_rows]
            metrics = _metrics_for_rows(split_rows, spec["target"], preds)
            key = f"{coin}|{spec['target']}|{split}"
            baseline_mae = float(best_mae.get(key, 0.0))
            baseline_id = str(best_baseline.get(key, "MISSING_BASELINE"))
            model_mae = float(metrics["mae"])
            improvement = baseline_mae - model_mae if baseline_mae > 0 else 0.0
            model_metrics.append(
                {
                    "coin": coin,
                    "model_id": spec["model_id"],
                    "model_family": spec["family"],
                    "target": spec["target"],
                    "split": split,
                    "feature_count": len(spec["features"]),
                    "features": "|".join(spec["features"]),
                    "best_phase20_baseline_id": baseline_id,
                    "best_phase20_baseline_mae": round(baseline_mae, 12),
                    "mae_improvement_vs_best_baseline": round(improvement, 12),
                    "beats_best_phase20_baseline": bool(baseline_mae > 0 and model_mae < baseline_mae),
                    "source": MODEL_BENCHMARK_SOURCE_LABEL,
                    "research_only": True,
                    "model_training_run": True,
                    "model_prediction_rows_generated": 0,
                    "trading_signal_generated": False,
                    "recommendation_generated": False,
                    "operational_decision_allowed": False,
                    "canonical_write": False,
                    **metrics,
                }
            )

    comparison_coverage = sum(1 for m in model_metrics if m["best_phase20_baseline_id"] != "MISSING_BASELINE") / len(model_metrics) if model_metrics else 0.0
    holdout_beats = sum(1 for m in model_metrics if m["split"] == "HOLDOUT_RESEARCH_ONLY" and bool(m["beats_best_phase20_baseline"]))
    summary = {
        "coin": coin,
        "ready": True,
        "reason": "",
        "harness_rows": len(rows),
        "train_rows": len(train_rows),
        "validation_rows": sum(1 for r in rows if r.get("split") == "VALIDATION_RESEARCH_ONLY"),
        "holdout_rows": sum(1 for r in rows if r.get("split") == "HOLDOUT_RESEARCH_ONLY"),
        "model_metric_rows": len(model_metrics),
        "coefficient_rows": len(coefficients),
        "model_count": len(MODEL_SPECS),
        "baseline_comparison_coverage": round(comparison_coverage, 8),
        "holdout_models_beating_best_baseline_count": holdout_beats,
        "model_training_run": True,
        "model_prediction_rows_generated": 0,
        "schema_complete": True,
    }
    return model_metrics, coefficients, summary


def _write_model_metrics_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "coin",
        "model_id",
        "model_family",
        "target",
        "split",
        "feature_count",
        "features",
        "n",
        "target_mean",
        "estimate_mean",
        "bias",
        "mae",
        "rmse",
        "correlation",
        "directional_coverage",
        "directional_accuracy",
        "best_phase20_baseline_id",
        "best_phase20_baseline_mae",
        "mae_improvement_vs_best_baseline",
        "beats_best_phase20_baseline",
        "source",
        "research_only",
        "model_training_run",
        "model_prediction_rows_generated",
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


def _write_coefficients_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "coin",
        "model_id",
        "target",
        "feature",
        "coefficient",
        "source",
        "research_only",
        "model_training_run",
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
        ("Benchmark ready", payload["interpretable_model_benchmark_ready"]),
        ("Phase20 audit", payload["phase20_audit_ready"]),
        ("Model metrics", payload["model_metric_rows_total"]),
        ("Models", payload["model_count"]),
        ("Prediction rows", payload["model_prediction_rows_generated"]),
        ("Operational", payload["operational_status"]),
        ("Mean score", payload["mean_model_benchmark_score"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)
    coin_html = "".join(
        f"<tr><td>{esc(s.get('coin'))}</td><td>{esc(s.get('harness_rows'))}</td><td>{esc(s.get('train_rows'))}</td><td>{esc(s.get('validation_rows'))}</td><td>{esc(s.get('holdout_rows'))}</td><td>{esc(s.get('model_metric_rows'))}</td><td>{esc(s.get('coefficient_rows'))}</td><td>{esc(s.get('baseline_comparison_coverage'))}</td><td>{esc(s.get('holdout_models_beating_best_baseline_count'))}</td><td>{esc(s.get('ready'))}</td></tr>"
        for s in payload["coin_model_summaries"]
    )
    preview_html = "".join(
        f"<tr><td>{esc(m.get('coin'))}</td><td>{esc(m.get('model_id'))}</td><td>{esc(m.get('target'))}</td><td>{esc(m.get('split'))}</td><td>{esc(m.get('mae'))}</td><td>{esc(m.get('best_phase20_baseline_mae'))}</td><td>{esc(m.get('mae_improvement_vs_best_baseline'))}</td><td>{esc(m.get('beats_best_phase20_baseline'))}</td></tr>"
        for m in payload["model_metrics_preview"]
    )
    crit_html = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td></tr>"
        for c in payload["criteria"]
    )
    page = (
        "<!doctype html><html><head><meta charset='utf-8'><title>QRDS Interpretable Model Benchmark</title>"
        "<style>body{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}.card{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}.kpi{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:150px}table{border-collapse:collapse;width:100%;background:white}th,td{border:1px solid #d9deea;padding:8px;text-align:left}th{background:#eef2ff}.blocked{background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}.ok{background:#dcfce7;border-radius:999px;padding:6px 10px;font-weight:700}</style></head><body>"
        f"<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Phase 21 Baseline Audit + Interpretable Offline Model Benchmark</h2>"
        f"<div class='card'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p><p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>{card_html}<p class='ok'>Models are simple linear/ridge-lite research benchmarks compared against Phase 20 baselines.</p><p class='blocked'>No operational predictions, trading signals, recommendations, allocations, or safe-apply decisions.</p></div>"
        f"<h2>Coin model summaries</h2><table><thead><tr><th>coin</th><th>harness rows</th><th>train</th><th>validation</th><th>holdout</th><th>metric rows</th><th>coef rows</th><th>baseline coverage</th><th>holdout beats</th><th>ready</th></tr></thead><tbody>{coin_html}</tbody></table>"
        f"<h2>Holdout metrics preview</h2><table><thead><tr><th>coin</th><th>model</th><th>target</th><th>split</th><th>MAE</th><th>best baseline MAE</th><th>improvement</th><th>beats</th></tr></thead><tbody>{preview_html}</tbody></table>"
        f"<h2>Criteria</h2><table><thead><tr><th>criterion</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th></tr></thead><tbody>{crit_html}</tbody></table>"
        f"<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"
    )
    path.write_text(page, encoding="utf-8")


def _update_project_status(root: Path, payload: dict[str, Any]) -> None:
    status_path = root / "crypto_decision_lab/docs/reports/PROJECT_STATUS_QRDS_GATE_BTC.md"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    existing = status_path.read_text(encoding="utf-8") if status_path.exists() else "# QRDS/QOS Gate BTC — Project Status\n"
    marker = "\n## Latest Phase 21 update\n"
    before = existing.split(marker)[0].rstrip()
    section = [
        marker.strip(),
        "",
        f"Updated at: {payload['generated_at']}",
        "",
        f"- Phase 21 gate: `{payload['gate_answer']}`",
        f"- Phase 20 audit ready: `{payload['phase20_audit_ready']}`",
        f"- Interpretable model benchmark ready: `{payload['interpretable_model_benchmark_ready']}`",
        f"- Model count: `{payload['model_count']}`",
        f"- Model metric rows total: `{payload['model_metric_rows_total']}`",
        f"- Coefficient rows total: `{payload['coefficient_rows_total']}`",
        f"- Operational prediction rows generated: `{payload['model_prediction_rows_generated']}`",
        f"- Operational status: `{payload['operational_status']}`",
        f"- Canonical writes: `{payload['canonical_data_writes']}`",
        "",
        "Phase 21 trains simple offline interpretable research models only for benchmark metrics. These outputs are not trading signals, recommendations, allocations, or operational decisions.",
        "",
    ]
    status_path.write_text(before + "\n\n" + "\n".join(section), encoding="utf-8")


def build_phase21_baseline_audit_interpretable_model_benchmark_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    min_rows_per_coin: int = MIN_ROWS_PER_COIN,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    metrics_dir = out / "model_metrics"
    out.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)

    phase20 = _phase20_index(root)
    audit = _audit_phase20(root, phase20)

    all_metrics: list[dict[str, Any]] = []
    all_coefficients: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    metric_outputs: list[dict[str, Any]] = []

    for coin in COINS:
        metrics, coefficients, summary = _evaluate_coin_models(root, coin, audit)
        metric_path = metrics_dir / f"{coin.lower()}_interpretable_model_metrics.csv"
        coef_path = metrics_dir / f"{coin.lower()}_interpretable_model_coefficients.csv"
        _write_model_metrics_csv(metric_path, metrics)
        _write_coefficients_csv(coef_path, coefficients)

        summary["metric_path"] = str(metric_path)
        summary["metric_sha256"] = _sha_file(metric_path)[:16]
        summary["coefficient_path"] = str(coef_path)
        summary["coefficient_sha256"] = _sha_file(coef_path)[:16]
        summary["ready"] = (
            bool(summary.get("ready"))
            and int(summary.get("harness_rows", 0)) >= min_rows_per_coin
            and int(summary.get("model_metric_rows", 0)) >= len(MODEL_SPECS) * len(SPLITS)
            and float(summary.get("baseline_comparison_coverage", 0.0)) >= 1.0
            and int(summary.get("coefficient_rows", 0)) > 0
        )

        summaries.append(summary)
        all_metrics.extend(metrics)
        all_coefficients.extend(coefficients)
        metric_outputs.append(
            {
                "coin": coin,
                "metric_path": str(metric_path),
                "coefficient_path": str(coef_path),
                "metric_rows": len(metrics),
                "coefficient_rows": len(coefficients),
                "canonical_write": False,
                "model_prediction_rows_generated": 0,
            }
        )

    combined_metrics_path = metrics_dir / "all_interpretable_model_metrics.csv"
    combined_coefficients_path = metrics_dir / "all_interpretable_model_coefficients.csv"
    _write_model_metrics_csv(combined_metrics_path, all_metrics)
    _write_coefficients_csv(combined_coefficients_path, all_coefficients)

    model_training_run = len(all_metrics) > 0
    model_prediction_rows_generated = 0
    canonical_data_writes = 0
    promotion_allowed = False
    safe_apply_allowed = False
    git_status = _git_status(root)

    min_rows = min((int(s.get("harness_rows", 0)) for s in summaries), default=0)
    min_baseline_coverage = min((float(s.get("baseline_comparison_coverage", 0.0)) for s in summaries), default=0.0)
    all_coin_ready = all(bool(s.get("ready")) for s in summaries)
    holdout_metric_rows = sum(1 for m in all_metrics if m.get("split") == "HOLDOUT_RESEARCH_ONLY")
    holdout_beats_total = sum(1 for s in summaries for _ in range(int(s.get("holdout_models_beating_best_baseline_count", 0))))
    max_feature_count = max((int(m.get("feature_count", 0)) for m in all_metrics), default=0)

    criteria = [
        _criterion("phase20_index_present", bool(phase20.get("_present")), phase20.get("gate_answer", "MISSING"), "Phase 20 index present"),
        _criterion("phase20_audit_ready", bool(audit.get("audit_ready")), audit.get("phase20_metric_rows"), "Phase 20 metrics complete and ready"),
        _criterion("coin_count", len(summaries) == 3, [s.get("coin") for s in summaries], "BTC,ETH,SOL"),
        _criterion("harness_depth_per_coin", min_rows >= min_rows_per_coin, min_rows, f">= {min_rows_per_coin}"),
        _criterion("model_count", len(MODEL_SPECS) >= 5, len(MODEL_SPECS), ">=5 interpretable model specs"),
        _criterion("model_metrics_generated", len(all_metrics) >= len(COINS) * len(MODEL_SPECS) * len(SPLITS), len(all_metrics), "coin x model x split metrics"),
        _criterion("holdout_model_metrics_present", holdout_metric_rows >= len(COINS) * len(MODEL_SPECS), holdout_metric_rows, ">= coin x model holdout metrics"),
        _criterion("coefficients_generated", len(all_coefficients) > 0, len(all_coefficients), ">0 coefficient rows"),
        _criterion("interpretability_feature_cap", max_feature_count <= 6, max_feature_count, "<=6 features/model"),
        _criterion("baseline_comparison_coverage", min_baseline_coverage >= 1.0, min_baseline_coverage, "100% model metrics have Phase 20 best-baseline comparison"),
        _criterion("coin_model_summaries_ready", all_coin_ready, [s.get("ready") for s in summaries], "all true"),
        _criterion("model_training_run_offline_only", model_training_run, model_training_run, "true, offline research only"),
        _criterion("operational_prediction_rows_zero", model_prediction_rows_generated == 0, model_prediction_rows_generated, "0 operational prediction rows"),
        _criterion("models_not_trading_signals", True, "benchmark_metrics_only", "no trading signals"),
        _criterion("metric_outputs_artifact_only", all(not x["canonical_write"] for x in metric_outputs), [x["canonical_write"] for x in metric_outputs], "all false"),
        _criterion("safe_apply_blocked", not safe_apply_allowed, safe_apply_allowed, "false"),
        _criterion("promotion_blocked", not promotion_allowed, promotion_allowed, "false"),
        _criterion("canonical_writes_zero", canonical_data_writes == 0, canonical_data_writes, "0"),
        _criterion("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]
    ready_count = sum(1 for c in criteria if c["ready"])
    benchmark_ready = ready_count == len(criteria)
    gate = "PHASE21_BASELINE_AUDIT_INTERPRETABLE_MODEL_BENCHMARK_READY_RESEARCH_ONLY" if benchmark_ready else "PHASE21_BASELINE_AUDIT_INTERPRETABLE_MODEL_BENCHMARK_NEEDS_REVIEW_RESEARCH_ONLY"

    preview = [m for m in all_metrics if m.get("split") == "HOLDOUT_RESEARCH_ONLY"][:18]

    payload: dict[str, Any] = {
        "schema": "qrds.phase21_baseline_audit_interpretable_model_benchmark_pack.v1",
        "report_name": "qrds-phase21-baseline-audit-interpretable-model-benchmark-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": "PHASE_21_BASELINE_AUDIT_INTERPRETABLE_MODEL_BENCHMARK",
        "interpretable_model_benchmark_ready": benchmark_ready,
        "phase20_audit_ready": bool(audit.get("audit_ready")),
        "data_nature": "INTERPRETABLE_OFFLINE_MODEL_BENCHMARK_RESEARCH_ONLY",
        "coins": COINS,
        "coins_count": len(COINS),
        "model_specs": MODEL_SPECS,
        "model_count": len(MODEL_SPECS),
        "model_training_run": model_training_run,
        "offline_training_only": True,
        "model_metric_rows_total": len(all_metrics),
        "coefficient_rows_total": len(all_coefficients),
        "holdout_model_metric_rows": holdout_metric_rows,
        "holdout_models_beating_best_baseline_count": holdout_beats_total,
        "min_harness_rows_per_coin": min_rows,
        "min_baseline_comparison_coverage": min_baseline_coverage,
        "max_feature_count_per_model": max_feature_count,
        "model_prediction_rows_generated": model_prediction_rows_generated,
        "model_estimates_are_operational_predictions": False,
        "models_are_trading_signals": False,
        "models_are_recommendations": False,
        "phase20_audit": audit,
        "coin_model_summaries": summaries,
        "metric_outputs": metric_outputs,
        "combined_model_metrics_path": str(combined_metrics_path),
        "combined_model_metrics_sha256": _sha_file(combined_metrics_path)[:16],
        "combined_coefficients_path": str(combined_coefficients_path),
        "combined_coefficients_sha256": _sha_file(combined_coefficients_path)[:16],
        "model_metrics_preview": preview,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "modeling_status": "INTERPRETABLE_MODEL_BENCHMARK_READY" if benchmark_ready else "INTERPRETABLE_MODEL_BENCHMARK_NEEDS_REVIEW",
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "canonical_data_writes": canonical_data_writes,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_model_benchmark_score": round(ready_count / len(criteria), 4),
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    rp = out / "phase21_baseline_audit_interpretable_model_benchmark_pack.json"
    mp = out / "phase21_baseline_audit_interpretable_model_benchmark_pack.md"
    hp = out / "index.html"
    ip = out / "phase21_baseline_audit_interpretable_model_benchmark_pack_index.json"

    rp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(
        f"# QRDS/QOS Phase 21 Baseline Audit + Interpretable Offline Model Benchmark\n\n**Gate answer:** {gate}\n\nPhase 20 audit ready: {payload['phase20_audit_ready']}\n\nModel count: {len(MODEL_SPECS)}\n\nModel metric rows: {len(all_metrics)}\n\nCoefficient rows: {len(all_coefficients)}\n\nOperational prediction rows: 0\n\nOperational status: BLOCKED_RESEARCH_ONLY\n\nThese are offline research benchmark metrics only; they are not trading signals, recommendations, allocations, or operational decisions.\n",
        encoding="utf-8",
    )
    _render_html(hp, payload)

    index = {
        "schema": "qrds.phase21_baseline_audit_interpretable_model_benchmark_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "station": payload["station"],
        "interpretable_model_benchmark_ready": payload["interpretable_model_benchmark_ready"],
        "phase20_audit_ready": payload["phase20_audit_ready"],
        "data_nature": payload["data_nature"],
        "coins": payload["coins"],
        "coins_count": payload["coins_count"],
        "model_count": payload["model_count"],
        "model_training_run": payload["model_training_run"],
        "offline_training_only": payload["offline_training_only"],
        "model_metric_rows_total": payload["model_metric_rows_total"],
        "coefficient_rows_total": payload["coefficient_rows_total"],
        "holdout_model_metric_rows": payload["holdout_model_metric_rows"],
        "holdout_models_beating_best_baseline_count": payload["holdout_models_beating_best_baseline_count"],
        "min_harness_rows_per_coin": payload["min_harness_rows_per_coin"],
        "min_baseline_comparison_coverage": payload["min_baseline_comparison_coverage"],
        "max_feature_count_per_model": payload["max_feature_count_per_model"],
        "model_prediction_rows_generated": payload["model_prediction_rows_generated"],
        "model_estimates_are_operational_predictions": payload["model_estimates_are_operational_predictions"],
        "models_are_trading_signals": payload["models_are_trading_signals"],
        "models_are_recommendations": payload["models_are_recommendations"],
        "operational_status": payload["operational_status"],
        "modeling_status": payload["modeling_status"],
        "safe_apply_allowed": payload["safe_apply_allowed"],
        "promotion_allowed": payload["promotion_allowed"],
        "canonical_data_writes": payload["canonical_data_writes"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_model_benchmark_score": payload["mean_model_benchmark_score"],
        "git_status_line_count": payload["git_status_line_count"],
        "combined_model_metrics_path": payload["combined_model_metrics_path"],
        "combined_coefficients_path": payload["combined_coefficients_path"],
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


build_baseline_audit_interpretable_model_benchmark_pack = build_phase21_baseline_audit_interpretable_model_benchmark_pack
