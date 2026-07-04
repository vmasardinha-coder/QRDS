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
VOL_TARGET = "forward_realized_vol_24h_research_target"
HARNESS_SOURCE = "QRDS_OFFLINE_EXPERIMENT_HARNESS_RESEARCH_ONLY"
SOURCE = "QRDS_VOLATILITY_FEATURE_BASELINE_STRENGTHENING_RESEARCH_ONLY"
MIN_ROWS_PER_COIN = 3500

BASELINE_IDS = [
    "VOL_TRAIN_MEDIAN_TARGET",
    "VOL_CURRENT_24H_PROXY",
    "VOL_CURRENT_168H_PROXY",
    "VOL_TERM_MEAN_PROXY",
    "VOL_TERM_MAX_PROXY",
    "VOL_STRESS_RANGE_PROXY",
    "VOL_BLEND_24H_STRESS_PROXY",
    "VOL_BLEND_TERM_STRESS_PROXY",
    "VOL_ROBUST_MEDIAN_PROXY",
    "VOL_REGIME_TRAIN_MEDIAN",
    "VOL_VALIDATION_SELECTED_STRENGTHENED",
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


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


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


def _f(v: Any, default: float = 0.0) -> float:
    try:
        if v in ("", None):
            return default
        return float(v)
    except Exception:
        return default


def _b(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"true", "1", "yes", "y"}


def _mean(xs: list[float]) -> float:
    return statistics.fmean(xs) if xs else 0.0


def _median(xs: list[float]) -> float:
    return statistics.median(xs) if xs else 0.0


def _rmse(errs: list[float]) -> float:
    return math.sqrt(_mean([e * e for e in errs])) if errs else 0.0


def _corr(a: list[float], b: list[float]) -> float:
    if len(a) < 3 or len(a) != len(b):
        return 0.0
    ma, mb = _mean(a), _mean(b)
    da = math.sqrt(sum((x - ma) ** 2 for x in a))
    db = math.sqrt(sum((y - mb) ** 2 for y in b))
    if da == 0 or db == 0:
        return 0.0
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (da * db)


def _phase24(root: Path) -> dict[str, Any]:
    return _load_json(root / "crypto_decision_lab/artifacts/phase24_volatility_residual_diagnostics_baseline_robustness_pack/phase24_volatility_residual_diagnostics_baseline_robustness_pack_index.json")


def _harness_path(root: Path, coin: str) -> Path:
    return root / "crypto_decision_lab/artifacts/phase19_offline_experiment_harness_pack/harness" / f"{coin.lower()}_offline_experiment_harness_1h.csv"


def _harness_rows(root: Path, coin: str) -> list[dict[str, Any]]:
    return [r for r in _read_csv(_harness_path(root, coin)) if r.get("source") == HARNESS_SOURCE or r.get("source", "") == ""]


def _phase20_best(root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    p = root / "crypto_decision_lab/artifacts/phase20_baseline_metrics_null_models_harness_pack/metrics/all_baseline_null_model_metrics.csv"
    rows = [r for r in _read_csv(p) if r.get("target") == VOL_TARGET]
    best: dict[tuple[str, str], dict[str, Any]] = {}
    for r in rows:
        key = (str(r.get("coin")), str(r.get("split")))
        mae = _f(r.get("mae"), 0.0)
        if key not in best or mae < best[key]["mae"]:
            best[key] = {"mae": mae, "id": str(r.get("baseline_id", "MISSING_PHASE20_BASELINE"))}
    return best


def _phase23_best(root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    p = root / "crypto_decision_lab/artifacts/phase23_volatility_first_research_benchmark_pack/volatility_models/all_volatility_first_metrics.csv"
    rows = _read_csv(p)
    best: dict[tuple[str, str], dict[str, Any]] = {}
    for r in rows:
        key = (str(r.get("coin")), str(r.get("split")))
        mae = _f(r.get("mae"), 0.0)
        if key not in best or mae < best[key]["mae"]:
            best[key] = {"mae": mae, "id": str(r.get("model_id", "MISSING_PHASE23_MODEL"))}
    return best


def _regime_key(r: dict[str, Any]) -> str:
    return "|".join([
        str(r.get("volatility_regime_24h", "VOL_MISSING")),
        str(r.get("dispersion_regime_24h", "DISP_MISSING")),
        str(r.get("momentum_diagnostic_24h", "MOM_MISSING")),
    ])


def _stress(r: dict[str, Any]) -> float:
    return max(abs(_f(r.get("return_24h_min"), 0.0)), abs(_f(r.get("return_24h_max"), 0.0))) * math.sqrt(365.0)


def _term_vals(r: dict[str, Any]) -> list[float]:
    return [x for x in [_f(r.get("rolling_vol_24h_ann"), 0.0), _f(r.get("rolling_vol_168h_ann"), 0.0), _f(r.get("rolling_vol_720h_ann"), 0.0)] if x > 0]


def _fit_context(rows: list[dict[str, Any]]) -> dict[str, Any]:
    train = [r for r in rows if r.get("split") == "TRAIN_RESEARCH_ONLY"]
    vals = [_f(r.get(VOL_TARGET), 0.0) for r in train]
    regime: dict[str, list[float]] = {}
    for r in train:
        regime.setdefault(_regime_key(r), []).append(_f(r.get(VOL_TARGET), 0.0))
    return {
        "train_median": _median(vals),
        "train_mean": _mean(vals),
        "regime_medians": {k: _median(v) for k, v in regime.items()},
    }


def _predict(r: dict[str, Any], baseline_id: str, ctx: dict[str, Any], selected: str = "") -> float:
    if baseline_id == "VOL_VALIDATION_SELECTED_STRENGTHENED":
        return _predict(r, selected or "VOL_CURRENT_24H_PROXY", ctx)
    v24 = _f(r.get("rolling_vol_24h_ann"), 0.0)
    v168 = _f(r.get("rolling_vol_168h_ann"), 0.0)
    vals = _term_vals(r)
    term_mean = _mean(vals)
    term_max = max(vals) if vals else 0.0
    stress = _stress(r)
    if baseline_id == "VOL_TRAIN_MEDIAN_TARGET":
        return max(0.0, ctx["train_median"])
    if baseline_id == "VOL_CURRENT_24H_PROXY":
        return max(0.0, v24)
    if baseline_id == "VOL_CURRENT_168H_PROXY":
        return max(0.0, v168)
    if baseline_id == "VOL_TERM_MEAN_PROXY":
        return max(0.0, term_mean)
    if baseline_id == "VOL_TERM_MAX_PROXY":
        return max(0.0, term_max)
    if baseline_id == "VOL_STRESS_RANGE_PROXY":
        return max(0.0, stress)
    if baseline_id == "VOL_BLEND_24H_STRESS_PROXY":
        return max(0.0, 0.65 * v24 + 0.35 * stress)
    if baseline_id == "VOL_BLEND_TERM_STRESS_PROXY":
        return max(0.0, 0.70 * term_mean + 0.30 * stress)
    if baseline_id == "VOL_ROBUST_MEDIAN_PROXY":
        xs = [x for x in [v24, v168, term_mean, term_max, stress] if x > 0]
        return max(0.0, _median(xs))
    if baseline_id == "VOL_REGIME_TRAIN_MEDIAN":
        return max(0.0, ctx["regime_medians"].get(_regime_key(r), ctx["train_median"]))
    return max(0.0, v24)


def _metrics(rows: list[dict[str, Any]], preds: list[float]) -> dict[str, Any]:
    y = [_f(r.get(VOL_TARGET), 0.0) for r in rows]
    errs = [p - t for p, t in zip(preds, y)]
    return {
        "n": len(rows),
        "target_mean": round(_mean(y), 12),
        "estimate_mean": round(_mean(preds), 12),
        "bias": round(_mean(errs), 12),
        "mae": round(_mean([abs(e) for e in errs]), 12),
        "rmse": round(_rmse(errs), 12),
        "correlation": round(_corr(y, preds), 12),
    }


def _evaluate_coin(root: Path, coin: str, p20: dict[tuple[str, str], dict[str, Any]], p23: dict[tuple[str, str], dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = _harness_rows(root, coin)
    if not rows:
        return [], {
            "coin": coin,
            "ready": False,
            "reason": "missing_harness_rows",
            "harness_rows": 0,
            "metric_rows": 0,
            "holdout_beats_phase20": 0,
            "holdout_beats_phase23": 0,
            "best_holdout_baseline_id": "MISSING",
            "best_holdout_mae": 0.0,
            "best_phase20_mae": 0.0,
            "best_phase23_mae": 0.0,
            "best_improvement_vs_phase20": 0.0,
            "best_improvement_vs_phase23": 0.0,
            "selected_validation_baseline": "MISSING",
            "model_prediction_rows_generated": 0,
            "schema_complete": True,
        }

    ctx = _fit_context(rows)
    validation = [r for r in rows if r.get("split") == "VALIDATION_RESEARCH_ONLY"]
    validation_mae: dict[str, float] = {}
    for bid in BASELINE_IDS:
        if bid == "VOL_VALIDATION_SELECTED_STRENGTHENED":
            continue
        validation_mae[bid] = _metrics(validation, [_predict(r, bid, ctx) for r in validation])["mae"]
    selected = min(validation_mae, key=validation_mae.get) if validation_mae else "VOL_CURRENT_24H_PROXY"

    out: list[dict[str, Any]] = []
    for bid in BASELINE_IDS:
        for split in SPLITS:
            split_rows = [r for r in rows if r.get("split") == split]
            preds = [_predict(r, bid, ctx, selected) for r in split_rows]
            m = _metrics(split_rows, preds)
            b20 = p20.get((coin, split), {"mae": 0.0, "id": "MISSING_PHASE20"})
            b23 = p23.get((coin, split), {"mae": 0.0, "id": "MISSING_PHASE23"})
            out.append({
                "coin": coin,
                "baseline_id": bid,
                "target": VOL_TARGET,
                "split": split,
                "selected_validation_baseline": selected if bid == "VOL_VALIDATION_SELECTED_STRENGTHENED" else "",
                "best_phase20_id": b20["id"],
                "best_phase20_mae": round(float(b20["mae"]), 12),
                "improvement_vs_phase20": round(float(b20["mae"]) - float(m["mae"]), 12) if b20["mae"] else 0.0,
                "beats_phase20": bool(b20["mae"] and float(m["mae"]) < float(b20["mae"])),
                "best_phase23_id": b23["id"],
                "best_phase23_mae": round(float(b23["mae"]), 12),
                "improvement_vs_phase23": round(float(b23["mae"]) - float(m["mae"]), 12) if b23["mae"] else 0.0,
                "beats_phase23": bool(b23["mae"] and float(m["mae"]) < float(b23["mae"])),
                "source": SOURCE,
                "research_only": True,
                "model_training_run": False,
                "model_prediction_rows_generated": 0,
                "trading_signal_generated": False,
                "recommendation_generated": False,
                "operational_decision_allowed": False,
                "canonical_write": False,
                **m,
            })

    holdout = [r for r in out if r["split"] == "HOLDOUT_RESEARCH_ONLY"]
    best = min(holdout, key=lambda r: _f(r.get("mae"), 999999.0)) if holdout else {}
    summary = {
        "coin": coin,
        "ready": True,
        "reason": "",
        "harness_rows": len(rows),
        "train_rows": sum(1 for r in rows if r.get("split") == "TRAIN_RESEARCH_ONLY"),
        "validation_rows": len(validation),
        "holdout_rows": sum(1 for r in rows if r.get("split") == "HOLDOUT_RESEARCH_ONLY"),
        "metric_rows": len(out),
        "baseline_count": len(BASELINE_IDS),
        "holdout_beats_phase20": sum(1 for r in holdout if _b(r.get("beats_phase20"))),
        "holdout_beats_phase23": sum(1 for r in holdout if _b(r.get("beats_phase23"))),
        "best_holdout_baseline_id": best.get("baseline_id", "MISSING"),
        "best_holdout_mae": best.get("mae", 0.0),
        "best_phase20_mae": best.get("best_phase20_mae", 0.0),
        "best_phase23_mae": best.get("best_phase23_mae", 0.0),
        "best_improvement_vs_phase20": best.get("improvement_vs_phase20", 0.0),
        "best_improvement_vs_phase23": best.get("improvement_vs_phase23", 0.0),
        "selected_validation_baseline": selected,
        "model_prediction_rows_generated": 0,
        "schema_complete": True,
    }
    return out, summary


def _criterion(cid: str, ok: bool, observed: Any, threshold: str) -> dict[str, Any]:
    return {"criterion_id": cid, "status": "PASS" if ok else "FAIL", "ready": bool(ok), "observed": observed, "threshold": threshold}


def _render_html(path: Path, payload: dict[str, Any]) -> None:
    esc = lambda x: html.escape(str(x))
    cards = [
        ("Strength ready", payload["vol_feature_baseline_strengthening_ready"]),
        ("Phase24", payload["phase24_diagnostics_ready"]),
        ("Metric rows", payload["metric_rows_total"]),
        ("Baselines", payload["baseline_count"]),
        ("P20 beats", payload["holdout_beats_vs_phase20_total"]),
        ("P23 beats", payload["holdout_beats_vs_phase23_total"]),
        ("Operational", payload["operational_status"]),
        ("Score", payload["mean_strengthening_score"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)
    coin_html = "".join(
        f"<tr><td>{esc(s['coin'])}</td><td>{esc(s['harness_rows'])}</td><td>{esc(s['metric_rows'])}</td><td>{esc(s['holdout_beats_phase20'])}</td><td>{esc(s['holdout_beats_phase23'])}</td><td>{esc(s['best_holdout_baseline_id'])}</td><td>{esc(s['best_improvement_vs_phase20'])}</td><td>{esc(s['best_improvement_vs_phase23'])}</td><td>{esc(s['ready'])}</td></tr>"
        for s in payload["coin_strengthening_summaries"]
    )
    crit_html = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td></tr>"
        for c in payload["criteria"]
    )
    page = (
        "<!doctype html><html><head><meta charset='utf-8'><title>QRDS Phase 25 Vol Strengthening</title>"
        "<style>body{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}.kpi{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:150px}.card{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}table{border-collapse:collapse;width:100%;background:white}th,td{border:1px solid #d9deea;padding:8px;text-align:left}th{background:#eef2ff}.blocked{background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}</style></head><body>"
        f"<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Phase 25 Volatility Feature + Baseline Strengthening</h2>"
        f"<div class='card'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p>{card_html}<p class='blocked'>Strengthened baselines are research metrics, not signals, recommendations, allocations, or operational decisions.</p></div>"
        f"<h2>Coin summaries</h2><table><thead><tr><th>coin</th><th>rows</th><th>metrics</th><th>beats P20</th><th>beats P23</th><th>best baseline</th><th>imp vs P20</th><th>imp vs P23</th><th>ready</th></tr></thead><tbody>{coin_html}</tbody></table>"
        f"<h2>Criteria</h2><table><thead><tr><th>criterion</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th></tr></thead><tbody>{crit_html}</tbody></table>"
        f"<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"
    )
    path.write_text(page, encoding="utf-8")


def _update_project_status(root: Path, payload: dict[str, Any]) -> None:
    status_path = root / "crypto_decision_lab/docs/reports/PROJECT_STATUS_QRDS_GATE_BTC.md"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    existing = status_path.read_text(encoding="utf-8") if status_path.exists() else "# QRDS/QOS Gate BTC — Project Status\n"
    marker = "\n## Latest Phase 25 update\n"
    before = existing.split(marker)[0].rstrip()
    section = [
        marker.strip(), "",
        f"Updated at: {payload['generated_at']}", "",
        f"- Phase 25 gate: `{payload['gate_answer']}`",
        f"- Strengthening ready: `{payload['vol_feature_baseline_strengthening_ready']}`",
        f"- Metric rows total: `{payload['metric_rows_total']}`",
        f"- Holdout beats vs Phase 20: `{payload['holdout_beats_vs_phase20_total']}`",
        f"- Holdout beats vs Phase 23: `{payload['holdout_beats_vs_phase23_total']}`",
        f"- Operational status: `{payload['operational_status']}`",
        f"- Canonical writes: `{payload['canonical_data_writes']}`", "",
        "Phase 25 strengthens volatility baselines/features only. It creates no trading signals, recommendations, allocations, or operational decisions.", "",
    ]
    status_path.write_text(before + "\n\n" + "\n".join(section), encoding="utf-8")


def build_phase25_volatility_feature_baseline_strengthening_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    min_rows_per_coin: int = MIN_ROWS_PER_COIN,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    metrics_dir = out / "strengthened_baselines"
    metrics_dir.mkdir(parents=True, exist_ok=True)

    phase24 = _phase24(root)
    phase24_ready = bool(phase24.get("vol_residual_diagnostics_ready", False))
    phase24_path = str(phase24.get("diagnostic_path_forward", "MISSING"))
    p20 = _phase20_best(root)
    p23 = _phase23_best(root)

    all_rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []
    fields = [
        "coin","baseline_id","target","split","selected_validation_baseline","n","target_mean","estimate_mean","bias","mae","rmse","correlation",
        "best_phase20_id","best_phase20_mae","improvement_vs_phase20","beats_phase20","best_phase23_id","best_phase23_mae","improvement_vs_phase23","beats_phase23",
        "source","research_only","model_training_run","model_prediction_rows_generated","trading_signal_generated","recommendation_generated","operational_decision_allowed","canonical_write",
    ]

    for coin in COINS:
        rows, summary = _evaluate_coin(root, coin, p20, p23)
        path = metrics_dir / f"{coin.lower()}_strengthened_volatility_baselines.csv"
        _write_csv(path, rows, fields)
        summary["path"] = str(path)
        summary["sha256"] = _sha_file(path)[:16]
        summary["ready"] = bool(summary.get("ready")) and int(summary.get("harness_rows", 0)) >= min_rows_per_coin and int(summary.get("metric_rows", 0)) >= len(BASELINE_IDS) * len(SPLITS)
        summaries.append(summary)
        all_rows.extend(rows)
        outputs.append({"coin": coin, "path": str(path), "rows": len(rows), "canonical_write": False, "model_prediction_rows_generated": 0})

    combined_path = metrics_dir / "all_strengthened_volatility_baselines.csv"
    _write_csv(combined_path, all_rows, fields)

    holdout = [r for r in all_rows if r.get("split") == "HOLDOUT_RESEARCH_ONLY"]
    holdout_beats_p20 = sum(1 for r in holdout if _b(r.get("beats_phase20")))
    holdout_beats_p23 = sum(1 for r in holdout if _b(r.get("beats_phase23")))
    min_rows = min((int(s.get("harness_rows", 0)) for s in summaries), default=0)
    canonical_data_writes = 0
    promotion_allowed = False
    safe_apply_allowed = False
    git_status = _git_status(root)

    criteria = [
        _criterion("phase24_index_present", bool(phase24.get("_present")), phase24.get("gate_answer", "MISSING"), "Phase 24 index present"),
        _criterion("phase24_diagnostics_ready", phase24_ready, phase24_ready, "true"),
        _criterion("phase24_strengthen_path", phase24_path == "STRENGTHEN_VOLATILITY_BASELINES_AND_FEATURES_RESEARCH_ONLY", phase24_path, "strengthen baselines/features"),
        _criterion("coin_count", len(summaries) == 3, [s.get("coin") for s in summaries], "BTC,ETH,SOL"),
        _criterion("harness_depth_per_coin", min_rows >= min_rows_per_coin, min_rows, f">= {min_rows_per_coin}"),
        _criterion("baseline_count", len(BASELINE_IDS) >= 10, len(BASELINE_IDS), ">=10 strengthened baselines"),
        _criterion("metrics_generated", len(all_rows) >= len(COINS) * len(BASELINE_IDS) * len(SPLITS), len(all_rows), "coin x baseline x split metrics"),
        _criterion("holdout_metrics_present", len(holdout) >= len(COINS) * len(BASELINE_IDS), len(holdout), "coin x baseline holdout metrics"),
        _criterion("phase20_comparison_present", all(_f(r.get("best_phase20_mae"), 0.0) > 0 for r in holdout), "checked", "all holdout rows have Phase20 comparison"),
        _criterion("phase23_comparison_present", all(_f(r.get("best_phase23_mae"), 0.0) > 0 for r in holdout), "checked", "all holdout rows have Phase23 comparison"),
        _criterion("coin_summaries_ready", all(bool(s.get("ready")) for s in summaries), [s.get("ready") for s in summaries], "all true"),
        _criterion("model_training_not_run", True, False, "false; baselines only"),
        _criterion("operational_prediction_rows_zero", True, 0, "0 operational prediction rows"),
        _criterion("baselines_not_trading_signals", True, "research_metrics_only", "no trading signals"),
        _criterion("metric_outputs_artifact_only", all(not x["canonical_write"] for x in outputs), [x["canonical_write"] for x in outputs], "all false"),
        _criterion("safe_apply_blocked", not safe_apply_allowed, safe_apply_allowed, "false"),
        _criterion("promotion_blocked", not promotion_allowed, promotion_allowed, "false"),
        _criterion("canonical_writes_zero", canonical_data_writes == 0, canonical_data_writes, "0"),
        _criterion("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]
    ready_count = sum(1 for c in criteria if c["ready"])
    ready = ready_count == len(criteria)
    gate = "PHASE25_VOLATILITY_FEATURE_BASELINE_STRENGTHENING_READY_RESEARCH_ONLY" if ready else "PHASE25_VOLATILITY_FEATURE_BASELINE_STRENGTHENING_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.phase25_volatility_feature_baseline_strengthening_pack.v1",
        "report_name": "qrds-phase25-volatility-feature-baseline-strengthening-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": "PHASE_25_VOLATILITY_FEATURE_BASELINE_STRENGTHENING",
        "vol_feature_baseline_strengthening_ready": ready,
        "phase24_diagnostics_ready": phase24_ready,
        "phase24_diagnostic_path_forward": phase24_path,
        "data_nature": "VOLATILITY_FEATURE_BASELINE_STRENGTHENING_RESEARCH_ONLY",
        "coins": COINS,
        "coins_count": len(COINS),
        "target": VOL_TARGET,
        "baseline_ids": BASELINE_IDS,
        "baseline_count": len(BASELINE_IDS),
        "metric_rows_total": len(all_rows),
        "holdout_metric_rows": len(holdout),
        "holdout_beats_vs_phase20_total": holdout_beats_p20,
        "holdout_beats_vs_phase23_total": holdout_beats_p23,
        "min_harness_rows_per_coin": min_rows,
        "model_training_run": False,
        "model_prediction_rows_generated": 0,
        "baseline_estimates_are_operational_predictions": False,
        "baselines_are_trading_signals": False,
        "baselines_are_recommendations": False,
        "coin_strengthening_summaries": summaries,
        "strengthening_outputs": outputs,
        "combined_strengthened_baselines_path": str(combined_path),
        "combined_strengthened_baselines_sha256": _sha_file(combined_path)[:16],
        "holdout_metrics_preview": holdout[:18],
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "modeling_status": "VOLATILITY_FEATURE_BASELINE_STRENGTHENING_READY" if ready else "VOLATILITY_FEATURE_BASELINE_STRENGTHENING_NEEDS_REVIEW",
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "canonical_data_writes": canonical_data_writes,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_strengthening_score": round(ready_count / len(criteria), 4),
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    rp = out / "phase25_volatility_feature_baseline_strengthening_pack.json"
    mp = out / "phase25_volatility_feature_baseline_strengthening_pack.md"
    hp = out / "index.html"
    ip = out / "phase25_volatility_feature_baseline_strengthening_pack_index.json"
    rp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(f"# QRDS/QOS Phase 25 Volatility Feature + Baseline Strengthening\n\n**Gate answer:** {gate}\n\nMetrics: {len(all_rows)}\n\nHoldout beats vs Phase20: {holdout_beats_p20}\n\nHoldout beats vs Phase23: {holdout_beats_p23}\n\nOperational status: BLOCKED_RESEARCH_ONLY\n\nResearch-only baseline strengthening; no signal, recommendation, allocation, or operational decision.\n", encoding="utf-8")
    _render_html(hp, payload)

    index = {
        "schema": "qrds.phase25_volatility_feature_baseline_strengthening_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": payload["station"],
        "vol_feature_baseline_strengthening_ready": ready,
        "phase24_diagnostics_ready": phase24_ready,
        "phase24_diagnostic_path_forward": phase24_path,
        "data_nature": payload["data_nature"],
        "coins": COINS,
        "coins_count": len(COINS),
        "target": VOL_TARGET,
        "baseline_count": len(BASELINE_IDS),
        "metric_rows_total": len(all_rows),
        "holdout_metric_rows": len(holdout),
        "holdout_beats_vs_phase20_total": holdout_beats_p20,
        "holdout_beats_vs_phase23_total": holdout_beats_p23,
        "min_harness_rows_per_coin": min_rows,
        "model_training_run": False,
        "model_prediction_rows_generated": 0,
        "baseline_estimates_are_operational_predictions": False,
        "baselines_are_trading_signals": False,
        "baselines_are_recommendations": False,
        "operational_status": payload["operational_status"],
        "modeling_status": payload["modeling_status"],
        "safe_apply_allowed": payload["safe_apply_allowed"],
        "promotion_allowed": payload["promotion_allowed"],
        "canonical_data_writes": payload["canonical_data_writes"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_strengthening_score": payload["mean_strengthening_score"],
        "git_status_line_count": payload["git_status_line_count"],
        "combined_strengthened_baselines_path": str(combined_path),
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


build_volatility_feature_baseline_strengthening_pack = build_phase25_volatility_feature_baseline_strengthening_pack
