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
SOURCE = "QRDS_VOLATILITY_FIRST_RESEARCH_BENCHMARK_ONLY"
MIN_ROWS_PER_COIN = 3500

MODEL_IDS = [
    "VOL_CURRENT_24H_PROXY",
    "VOL_CURRENT_168H_PROXY",
    "VOL_TERM_STRUCTURE_MEAN",
    "VOL_STRESS_RANGE_PROXY",
    "VOL_VALIDATION_SELECTED_PROXY",
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


def _phase22(root: Path) -> dict[str, Any]:
    return _load_json(root / "crypto_decision_lab/artifacts/phase22_model_performance_triage_research_gate_pack/phase22_model_performance_triage_research_gate_pack_index.json")


def _phase20_vol_baselines(root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    path = root / "crypto_decision_lab/artifacts/phase20_baseline_metrics_null_models_harness_pack/metrics/all_baseline_null_model_metrics.csv"
    rows = [r for r in _read_csv(path) if r.get("target") == VOL_TARGET]
    best: dict[tuple[str, str], dict[str, Any]] = {}
    for r in rows:
        key = (str(r.get("coin")), str(r.get("split")))
        mae = _f(r.get("mae"), 0.0)
        if key not in best or mae < best[key]["mae"]:
            best[key] = {"mae": mae, "baseline_id": str(r.get("baseline_id", "MISSING_BASELINE"))}
    return best


def _harness_rows(root: Path, coin: str) -> list[dict[str, Any]]:
    path = root / "crypto_decision_lab/artifacts/phase19_offline_experiment_harness_pack/harness" / f"{coin.lower()}_offline_experiment_harness_1h.csv"
    return [r for r in _read_csv(path) if r.get("source") == HARNESS_SOURCE]


def _pred(row: dict[str, Any], model_id: str, selected_model: str = "") -> float:
    if model_id == "VOL_VALIDATION_SELECTED_PROXY":
        return _pred(row, selected_model or "VOL_CURRENT_24H_PROXY")
    v24 = _f(row.get("rolling_vol_24h_ann"), 0.0)
    v168 = _f(row.get("rolling_vol_168h_ann"), 0.0)
    v720 = _f(row.get("rolling_vol_720h_ann"), 0.0)
    rmin = abs(_f(row.get("return_24h_min"), 0.0))
    rmax = abs(_f(row.get("return_24h_max"), 0.0))
    if model_id == "VOL_CURRENT_24H_PROXY":
        return max(0.0, v24)
    if model_id == "VOL_CURRENT_168H_PROXY":
        return max(0.0, v168)
    if model_id == "VOL_TERM_STRUCTURE_MEAN":
        vals = [x for x in [v24, v168, v720] if x > 0]
        return max(0.0, _mean(vals))
    if model_id == "VOL_STRESS_RANGE_PROXY":
        stress = max(rmin, rmax) * math.sqrt(365.0)
        return max(0.0, 0.7 * v24 + 0.3 * stress)
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


def _evaluate_coin(root: Path, coin: str, best_baselines: dict[tuple[str, str], dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = _harness_rows(root, coin)
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
            "holdout_beats": 0,
            "holdout_beat_rate": 0.0,
            "best_holdout_model_id": "MISSING",
            "best_holdout_model_mae": 0.0,
            "best_phase20_vol_baseline_mae": 0.0,
            "best_holdout_improvement_vs_phase20_vol_baseline": 0.0,
            "selected_validation_proxy": "MISSING",
            "model_prediction_rows_generated": 0,
            "schema_complete": True,
        }

    validation_rows = [r for r in rows if r.get("split") == "VALIDATION_RESEARCH_ONLY"]
    validation_mae = {}
    for mid in MODEL_IDS:
        if mid == "VOL_VALIDATION_SELECTED_PROXY":
            continue
        validation_mae[mid] = _metrics(validation_rows, [_pred(r, mid) for r in validation_rows])["mae"]
    selected = min(validation_mae, key=validation_mae.get) if validation_mae else "VOL_CURRENT_24H_PROXY"

    metric_rows: list[dict[str, Any]] = []
    for mid in MODEL_IDS:
        for split in SPLITS:
            split_rows = [r for r in rows if r.get("split") == split]
            preds = [_pred(r, mid, selected) for r in split_rows]
            m = _metrics(split_rows, preds)
            best = best_baselines.get((coin, split), {"mae": 0.0, "baseline_id": "MISSING_BASELINE"})
            improvement = float(best["mae"]) - float(m["mae"]) if best["mae"] else 0.0
            metric_rows.append({
                "coin": coin,
                "model_id": mid,
                "target": VOL_TARGET,
                "split": split,
                "selected_validation_proxy": selected if mid == "VOL_VALIDATION_SELECTED_PROXY" else "",
                "best_phase20_vol_baseline_id": best["baseline_id"],
                "best_phase20_vol_baseline_mae": round(float(best["mae"]), 12),
                "mae_improvement_vs_best_phase20_vol_baseline": round(improvement, 12),
                "beats_best_phase20_vol_baseline": bool(best["mae"] and float(m["mae"]) < float(best["mae"])),
                "source": SOURCE,
                "research_only": True,
                "model_training_run": True,
                "model_prediction_rows_generated": 0,
                "trading_signal_generated": False,
                "recommendation_generated": False,
                "operational_decision_allowed": False,
                "canonical_write": False,
                **m,
            })

    holdout = [r for r in metric_rows if r["split"] == "HOLDOUT_RESEARCH_ONLY"]
    beats = sum(1 for r in holdout if _b(r["beats_best_phase20_vol_baseline"]))
    best_model = min(holdout, key=lambda r: _f(r.get("mae"), 999999.0)) if holdout else {}
    baseline_mae = _f(best_model.get("best_phase20_vol_baseline_mae"), 0.0)
    summary = {
        "coin": coin,
        "ready": True,
        "reason": "",
        "harness_rows": len(rows),
        "train_rows": sum(1 for r in rows if r.get("split") == "TRAIN_RESEARCH_ONLY"),
        "validation_rows": len(validation_rows),
        "holdout_rows": sum(1 for r in rows if r.get("split") == "HOLDOUT_RESEARCH_ONLY"),
        "metric_rows": len(metric_rows),
        "holdout_beats": beats,
        "holdout_beat_rate": round(beats / len(holdout), 8) if holdout else 0.0,
        "best_holdout_model_id": best_model.get("model_id", "MISSING"),
        "best_holdout_model_mae": best_model.get("mae", 0.0),
        "best_phase20_vol_baseline_id": best_model.get("best_phase20_vol_baseline_id", "MISSING"),
        "best_phase20_vol_baseline_mae": baseline_mae,
        "best_holdout_improvement_vs_phase20_vol_baseline": round(baseline_mae - _f(best_model.get("mae"), 0.0), 12) if best_model else 0.0,
        "selected_validation_proxy": selected,
        "model_prediction_rows_generated": 0,
        "schema_complete": True,
    }
    return metric_rows, summary


def _criterion(cid: str, ok: bool, observed: Any, threshold: str) -> dict[str, Any]:
    return {"criterion_id": cid, "status": "PASS" if ok else "FAIL", "ready": bool(ok), "observed": observed, "threshold": threshold}


def _render_html(path: Path, payload: dict[str, Any]) -> None:
    esc = lambda x: html.escape(str(x))
    cards = [
        ("Gate", payload["volatility_first_benchmark_ready"]),
        ("Phase22", payload["phase22_triage_ready"]),
        ("Metric rows", payload["model_metric_rows_total"]),
        ("Holdout beats", payload["holdout_beats_total"]),
        ("Coins improved", payload["coins_with_best_model_improvement"]),
        ("Pred rows", payload["model_prediction_rows_generated"]),
        ("Operational", payload["operational_status"]),
        ("Score", payload["mean_vol_benchmark_score"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)
    coin_html = "".join(
        f"<tr><td>{esc(s['coin'])}</td><td>{esc(s['harness_rows'])}</td><td>{esc(s['holdout_beats'])}</td><td>{esc(s['holdout_beat_rate'])}</td><td>{esc(s['best_holdout_model_id'])}</td><td>{esc(s['best_holdout_model_mae'])}</td><td>{esc(s['best_phase20_vol_baseline_mae'])}</td><td>{esc(s['best_holdout_improvement_vs_phase20_vol_baseline'])}</td><td>{esc(s['ready'])}</td></tr>"
        for s in payload["coin_volatility_summaries"]
    )
    preview_html = "".join(
        f"<tr><td>{esc(r['coin'])}</td><td>{esc(r['model_id'])}</td><td>{esc(r['split'])}</td><td>{esc(r['mae'])}</td><td>{esc(r['best_phase20_vol_baseline_mae'])}</td><td>{esc(r['mae_improvement_vs_best_phase20_vol_baseline'])}</td><td>{esc(r['beats_best_phase20_vol_baseline'])}</td></tr>"
        for r in payload["holdout_metrics_preview"]
    )
    crit_html = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td></tr>"
        for c in payload["criteria"]
    )
    page = (
        "<!doctype html><html><head><meta charset='utf-8'><title>QRDS Phase 23 Volatility First</title>"
        "<style>body{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}.kpi{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:150px}.card{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}table{border-collapse:collapse;width:100%;background:white}th,td{border:1px solid #d9deea;padding:8px;text-align:left}th{background:#eef2ff}.blocked{background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}.ok{background:#dcfce7;border-radius:999px;padding:6px 10px;font-weight:700}</style></head><body>"
        f"<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Phase 23 Volatility-First Research Benchmark</h2>"
        f"<div class='card'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p>{card_html}<p class='ok'>Volatility-first benchmark compared against Phase 20 volatility baselines.</p><p class='blocked'>No trading signals, recommendations, allocations, operational decisions, or safe-apply.</p></div>"
        f"<h2>Coin summaries</h2><table><thead><tr><th>coin</th><th>rows</th><th>beats</th><th>beat rate</th><th>best model</th><th>best MAE</th><th>baseline MAE</th><th>improvement</th><th>ready</th></tr></thead><tbody>{coin_html}</tbody></table>"
        f"<h2>Holdout preview</h2><table><thead><tr><th>coin</th><th>model</th><th>split</th><th>MAE</th><th>baseline MAE</th><th>improvement</th><th>beats</th></tr></thead><tbody>{preview_html}</tbody></table>"
        f"<h2>Criteria</h2><table><thead><tr><th>criterion</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th></tr></thead><tbody>{crit_html}</tbody></table>"
        f"<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"
    )
    path.write_text(page, encoding="utf-8")


def _update_project_status(root: Path, payload: dict[str, Any]) -> None:
    status_path = root / "crypto_decision_lab/docs/reports/PROJECT_STATUS_QRDS_GATE_BTC.md"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    existing = status_path.read_text(encoding="utf-8") if status_path.exists() else "# QRDS/QOS Gate BTC — Project Status\n"
    marker = "\n## Latest Phase 23 update\n"
    before = existing.split(marker)[0].rstrip()
    section = [
        marker.strip(), "",
        f"Updated at: {payload['generated_at']}", "",
        f"- Phase 23 gate: `{payload['gate_answer']}`",
        f"- Volatility-first benchmark ready: `{payload['volatility_first_benchmark_ready']}`",
        f"- Phase 22 triage ready: `{payload['phase22_triage_ready']}`",
        f"- Holdout beats total: `{payload['holdout_beats_total']}`",
        f"- Coins with best model improvement: `{payload['coins_with_best_model_improvement']}`",
        f"- Operational status: `{payload['operational_status']}`",
        f"- Canonical writes: `{payload['canonical_data_writes']}`", "",
        "Phase 23 is volatility-first research benchmarking only. It creates no trading signals, recommendations, allocations, or operational decisions.", "",
    ]
    status_path.write_text(before + "\n\n" + "\n".join(section), encoding="utf-8")


def build_phase23_volatility_first_research_benchmark_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    min_rows_per_coin: int = MIN_ROWS_PER_COIN,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    metrics_dir = out / "volatility_models"
    out.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)

    phase22 = _phase22(root)
    phase22_ready = bool(phase22.get("model_performance_triage_ready", False))
    phase22_path = str(phase22.get("research_path_forward", "MISSING"))
    best_baselines = _phase20_vol_baselines(root)

    all_metrics: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []

    metric_fields = [
        "coin","model_id","target","split","selected_validation_proxy","n","target_mean","estimate_mean","bias","mae","rmse","correlation",
        "best_phase20_vol_baseline_id","best_phase20_vol_baseline_mae","mae_improvement_vs_best_phase20_vol_baseline","beats_best_phase20_vol_baseline",
        "source","research_only","model_training_run","model_prediction_rows_generated","trading_signal_generated","recommendation_generated","operational_decision_allowed","canonical_write",
    ]

    for coin in COINS:
        metrics, summary = _evaluate_coin(root, coin, best_baselines)
        path = metrics_dir / f"{coin.lower()}_volatility_first_metrics.csv"
        _write_csv(path, metrics, metric_fields)
        summary["metric_path"] = str(path)
        summary["metric_sha256"] = _sha_file(path)[:16]
        summary["ready"] = bool(summary.get("ready")) and int(summary.get("harness_rows", 0)) >= min_rows_per_coin and int(summary.get("metric_rows", 0)) >= len(MODEL_IDS) * len(SPLITS)
        summaries.append(summary)
        all_metrics.extend(metrics)
        outputs.append({"coin": coin, "path": str(path), "rows": len(metrics), "canonical_write": False, "model_prediction_rows_generated": 0})

    combined_path = metrics_dir / "all_volatility_first_metrics.csv"
    _write_csv(combined_path, all_metrics, metric_fields)

    holdout = [r for r in all_metrics if r.get("split") == "HOLDOUT_RESEARCH_ONLY"]
    holdout_beats = sum(1 for r in holdout if _b(r.get("beats_best_phase20_vol_baseline")))
    coins_improved = sum(1 for s in summaries if _f(s.get("best_holdout_improvement_vs_phase20_vol_baseline"), 0.0) > 0)
    min_rows = min((int(s.get("harness_rows", 0)) for s in summaries), default=0)
    canonical_data_writes = 0
    promotion_allowed = False
    safe_apply_allowed = False
    git_status = _git_status(root)

    criteria = [
        _criterion("phase22_index_present", bool(phase22.get("_present")), phase22.get("gate_answer", "MISSING"), "Phase 22 index present"),
        _criterion("phase22_triage_ready", phase22_ready, phase22_ready, "true"),
        _criterion("phase22_volatility_first_path", phase22_path == "VOLATILITY_FIRST_RESEARCH_PATH", phase22_path, "VOLATILITY_FIRST_RESEARCH_PATH"),
        _criterion("coin_count", len(summaries) == 3, [s.get("coin") for s in summaries], "BTC,ETH,SOL"),
        _criterion("harness_depth_per_coin", min_rows >= min_rows_per_coin, min_rows, f">= {min_rows_per_coin}"),
        _criterion("vol_model_count", len(MODEL_IDS) >= 5, len(MODEL_IDS), ">=5 volatility-first models"),
        _criterion("model_metrics_generated", len(all_metrics) >= len(COINS) * len(MODEL_IDS) * len(SPLITS), len(all_metrics), "coin x model x split metrics"),
        _criterion("holdout_model_metrics_present", len(holdout) >= len(COINS) * len(MODEL_IDS), len(holdout), "coin x model holdout metrics"),
        _criterion("phase20_vol_baseline_comparison_present", all(_f(r.get("best_phase20_vol_baseline_mae"), 0.0) > 0 for r in holdout), "checked", "all holdout rows have baseline MAE"),
        _criterion("coin_summaries_ready", all(bool(s.get("ready")) for s in summaries), [s.get("ready") for s in summaries], "all true"),
        _criterion("operational_prediction_rows_zero", True, 0, "0 operational prediction rows"),
        _criterion("models_not_trading_signals", True, "volatility_research_metrics_only", "no trading signals"),
        _criterion("metric_outputs_artifact_only", all(not x["canonical_write"] for x in outputs), [x["canonical_write"] for x in outputs], "all false"),
        _criterion("safe_apply_blocked", not safe_apply_allowed, safe_apply_allowed, "false"),
        _criterion("promotion_blocked", not promotion_allowed, promotion_allowed, "false"),
        _criterion("canonical_writes_zero", canonical_data_writes == 0, canonical_data_writes, "0"),
        _criterion("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]
    ready_count = sum(1 for c in criteria if c["ready"])
    ready = ready_count == len(criteria)
    gate = "PHASE23_VOLATILITY_FIRST_RESEARCH_BENCHMARK_READY_RESEARCH_ONLY" if ready else "PHASE23_VOLATILITY_FIRST_RESEARCH_BENCHMARK_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.phase23_volatility_first_research_benchmark_pack.v1",
        "report_name": "qrds-phase23-volatility-first-research-benchmark-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": "PHASE_23_VOLATILITY_FIRST_RESEARCH_BENCHMARK",
        "volatility_first_benchmark_ready": ready,
        "phase22_triage_ready": phase22_ready,
        "phase22_research_path_forward": phase22_path,
        "data_nature": "VOLATILITY_FIRST_RESEARCH_BENCHMARK_ONLY",
        "coins": COINS,
        "coins_count": len(COINS),
        "target": VOL_TARGET,
        "vol_model_ids": MODEL_IDS,
        "vol_model_count": len(MODEL_IDS),
        "model_training_run": True if all_metrics else False,
        "offline_training_only": True,
        "model_metric_rows_total": len(all_metrics),
        "holdout_model_metric_rows": len(holdout),
        "holdout_beats_total": holdout_beats,
        "holdout_beat_rate_total": round(holdout_beats / len(holdout), 8) if holdout else 0.0,
        "coins_with_best_model_improvement": coins_improved,
        "min_harness_rows_per_coin": min_rows,
        "model_prediction_rows_generated": 0,
        "model_estimates_are_operational_predictions": False,
        "models_are_trading_signals": False,
        "models_are_recommendations": False,
        "coin_volatility_summaries": summaries,
        "volatility_outputs": outputs,
        "combined_vol_model_metrics_path": str(combined_path),
        "combined_vol_model_metrics_sha256": _sha_file(combined_path)[:16],
        "holdout_metrics_preview": holdout[:18],
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "modeling_status": "VOLATILITY_FIRST_RESEARCH_BENCHMARK_READY" if ready else "VOLATILITY_FIRST_RESEARCH_BENCHMARK_NEEDS_REVIEW",
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "canonical_data_writes": canonical_data_writes,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_vol_benchmark_score": round(ready_count / len(criteria), 4),
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    rp = out / "phase23_volatility_first_research_benchmark_pack.json"
    mp = out / "phase23_volatility_first_research_benchmark_pack.md"
    hp = out / "index.html"
    ip = out / "phase23_volatility_first_research_benchmark_pack_index.json"
    rp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(
        f"# QRDS/QOS Phase 23 Volatility-First Research Benchmark\n\n**Gate answer:** {gate}\n\nHoldout beats: {holdout_beats}/{len(holdout)}\n\nCoins with best-model improvement: {coins_improved}\n\nOperational prediction rows: 0\n\nOperational status: BLOCKED_RESEARCH_ONLY\n\nVolatility-first research benchmark only; no signal, recommendation, allocation, or operational decision.\n",
        encoding="utf-8",
    )
    _render_html(hp, payload)

    index = {k: payload[k] for k in [
        "schema","report_name","generated_at","gate_answer","policy_lock","app_mode","station","volatility_first_benchmark_ready",
        "phase22_triage_ready","phase22_research_path_forward","data_nature","coins","coins_count","target","vol_model_count",
        "model_training_run","offline_training_only","model_metric_rows_total","holdout_model_metric_rows","holdout_beats_total",
        "holdout_beat_rate_total","coins_with_best_model_improvement","min_harness_rows_per_coin","model_prediction_rows_generated",
        "model_estimates_are_operational_predictions","models_are_trading_signals","models_are_recommendations","operational_status",
        "modeling_status","safe_apply_allowed","promotion_allowed","canonical_data_writes","criteria_ready_count","criteria_total_count",
        "mean_vol_benchmark_score","git_status_line_count"
    ]}
    index.update({
        "combined_vol_model_metrics_path": str(combined_path),
        "report_path": str(rp),
        "markdown_path": str(mp),
        "html_path": str(hp),
        "index_path": str(ip),
        "serve_entrypoint": str(hp),
        "report_payload_sha256": payload["report_payload_sha256"],
        "payload": payload,
        **SAFETY_FLAGS,
    })
    ip.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    _update_project_status(root, payload)
    return index


build_volatility_first_research_benchmark_pack = build_phase23_volatility_first_research_benchmark_pack
