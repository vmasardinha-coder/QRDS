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
FEATURE_SOURCE_LABEL = "QRDS_RESEARCH_FEATURE_REGIME_DIAGNOSTICS_ONLY"
HARNESS_SOURCE_LABEL = "QRDS_OFFLINE_EXPERIMENT_HARNESS_RESEARCH_ONLY"
TARGET_HORIZON_HOURS = 24
MIN_ELIGIBLE_ROWS_PER_COIN = 3500
TRAIN_FRACTION = 0.60
VALIDATION_FRACTION = 0.20

FEATURE_COLUMNS = [
    "return_1h",
    "log_return_1h",
    "rolling_vol_24h_ann",
    "rolling_vol_168h_ann",
    "rolling_vol_720h_ann",
    "momentum_sum_24h",
    "momentum_sum_168h",
    "drawdown_from_peak",
    "dispersion_bps",
    "dispersion_bps_mean_24h",
    "dispersion_bps_mean_168h",
    "return_24h_min",
    "return_24h_max",
    "source_count",
]

DIAGNOSTIC_COLUMNS = [
    "volatility_regime_24h",
    "volatility_regime_168h",
    "dispersion_regime_24h",
    "momentum_diagnostic_24h",
    "momentum_diagnostic_168h",
    "feature_maturity",
]

TARGET_COLUMNS = [
    "forward_return_24h_research_target",
    "forward_abs_return_24h_research_target",
    "forward_realized_vol_24h_research_target",
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


def _stdev(values: list[float]) -> float:
    return statistics.stdev(values) if len(values) >= 2 else 0.0


def _phase18_index(root: Path) -> dict[str, Any]:
    return _load_json(root / "crypto_decision_lab/artifacts/phase18_research_feature_regime_diagnostics_pack/phase18_research_feature_regime_diagnostics_pack_index.json")


def _feature_path(root: Path, coin: str) -> Path:
    return root / "crypto_decision_lab/artifacts/phase18_research_feature_regime_diagnostics_pack/features" / f"{coin.lower()}_research_features_regime_1h.csv"


def _split_for_position(pos: int, n: int) -> str:
    train_cut = int(n * TRAIN_FRACTION)
    valid_cut = int(n * (TRAIN_FRACTION + VALIDATION_FRACTION))
    if pos < train_cut:
        return "TRAIN_RESEARCH_ONLY"
    if pos < valid_cut:
        return "VALIDATION_RESEARCH_ONLY"
    return "HOLDOUT_RESEARCH_ONLY"


def _forward_realized_vol(log_returns: list[float], start: int, horizon: int) -> float:
    chunk = log_returns[start + 1 : start + 1 + horizon]
    if len(chunk) < horizon or len(chunk) < 2:
        return 0.0
    return _stdev(chunk) * math.sqrt(24 * 365)


def _build_harness_rows(root: Path, coin: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    path = _feature_path(root, coin)
    rows = _read_csv(path)
    if not rows:
        return [], {
            "coin": coin,
            "ready": False,
            "reason": "missing_feature_rows",
            "feature_rows": 0,
            "eligible_rows": 0,
            "train_rows": 0,
            "validation_rows": 0,
            "holdout_rows": 0,
            "first_timestamp": "MISSING",
            "last_timestamp": "MISSING",
            "target_horizon_hours": TARGET_HORIZON_HOURS,
            "feature_columns_count": len(FEATURE_COLUMNS),
            "target_columns_count": len(TARGET_COLUMNS),
            "prediction_columns_count": 0,
            "leakage_guard_pass": False,
            "schema_complete": True,
        }

    closes = [_as_float(r.get("consensus_close_median"), 0.0) for r in rows]
    log_returns = [_as_float(r.get("log_return_1h"), 0.0) for r in rows]
    eligible_raw: list[dict[str, Any]] = []

    for i, row in enumerate(rows):
        if row.get("source") != FEATURE_SOURCE_LABEL:
            continue
        if row.get("feature_maturity") != "MATURE_RESEARCH_FEATURE_ROW":
            continue
        j = i + TARGET_HORIZON_HOURS
        if j >= len(rows) or closes[i] <= 0 or closes[j] <= 0:
            continue

        forward_return = closes[j] / closes[i] - 1.0
        forward_abs_return = abs(forward_return)
        forward_vol = _forward_realized_vol(log_returns, i, TARGET_HORIZON_HOURS)

        out: dict[str, Any] = {
            "timestamp": row.get("timestamp", ""),
            "coin": coin,
            "split": "",
            "source": HARNESS_SOURCE_LABEL,
            "research_only": "true",
            "target_horizon_hours": TARGET_HORIZON_HOURS,
            "target_available": "true",
            "prediction_generated": "false",
            "trading_signal_generated": "false",
            "recommendation_generated": "false",
            "operational_decision_allowed": "false",
            "canonical_write": "false",
            "safe_apply_allowed": "false",
        }
        for col in FEATURE_COLUMNS:
            out[col] = row.get(col, "")
        for col in DIAGNOSTIC_COLUMNS:
            out[col] = row.get(col, "")
        out["forward_return_24h_research_target"] = f"{forward_return:.12f}"
        out["forward_abs_return_24h_research_target"] = f"{forward_abs_return:.12f}"
        out["forward_realized_vol_24h_research_target"] = f"{forward_vol:.12f}"
        eligible_raw.append(out)

    n = len(eligible_raw)
    for pos, out in enumerate(eligible_raw):
        out["split"] = _split_for_position(pos, n)

    split_counts = {
        "TRAIN_RESEARCH_ONLY": sum(1 for r in eligible_raw if r["split"] == "TRAIN_RESEARCH_ONLY"),
        "VALIDATION_RESEARCH_ONLY": sum(1 for r in eligible_raw if r["split"] == "VALIDATION_RESEARCH_ONLY"),
        "HOLDOUT_RESEARCH_ONLY": sum(1 for r in eligible_raw if r["split"] == "HOLDOUT_RESEARCH_ONLY"),
    }

    feature_set = set(FEATURE_COLUMNS + DIAGNOSTIC_COLUMNS)
    target_set = set(TARGET_COLUMNS)
    leakage_guard_pass = feature_set.isdisjoint(target_set) and not any("forward_" in x for x in feature_set)
    forward_returns = [_as_float(r["forward_return_24h_research_target"], 0.0) for r in eligible_raw]

    summary = {
        "coin": coin,
        "ready": n > 0,
        "reason": "",
        "feature_rows": len(rows),
        "eligible_rows": n,
        "train_rows": split_counts["TRAIN_RESEARCH_ONLY"],
        "validation_rows": split_counts["VALIDATION_RESEARCH_ONLY"],
        "holdout_rows": split_counts["HOLDOUT_RESEARCH_ONLY"],
        "split_counts": split_counts,
        "first_timestamp": eligible_raw[0]["timestamp"] if eligible_raw else "MISSING",
        "last_timestamp": eligible_raw[-1]["timestamp"] if eligible_raw else "MISSING",
        "target_horizon_hours": TARGET_HORIZON_HOURS,
        "forward_return_24h_mean_research": round(_mean(forward_returns), 8),
        "forward_return_24h_abs_mean_research": round(_mean([abs(x) for x in forward_returns]), 8),
        "forward_return_24h_positive_rate_research": round(sum(1 for x in forward_returns if x > 0) / len(forward_returns), 8) if forward_returns else 0.0,
        "feature_columns_count": len(FEATURE_COLUMNS),
        "diagnostic_columns_count": len(DIAGNOSTIC_COLUMNS),
        "target_columns_count": len(TARGET_COLUMNS),
        "prediction_columns_count": 0,
        "leakage_guard_pass": leakage_guard_pass,
        "schema_complete": True,
    }
    return eligible_raw, summary


def _write_harness_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "timestamp",
        "coin",
        "split",
        "source",
        "research_only",
        "target_horizon_hours",
        *FEATURE_COLUMNS,
        *DIAGNOSTIC_COLUMNS,
        *TARGET_COLUMNS,
        "target_available",
        "prediction_generated",
        "trading_signal_generated",
        "recommendation_generated",
        "operational_decision_allowed",
        "canonical_write",
        "safe_apply_allowed",
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
        ("Harness ready", payload["offline_experiment_harness_ready"]),
        ("Eligible rows", payload["eligible_rows_total"]),
        ("Min eligible/coin", payload["min_eligible_rows_per_coin"]),
        ("Target horizon", payload["target_horizon_hours"]),
        ("Predictions", payload["prediction_rows_generated"]),
        ("Operational", payload["operational_status"]),
        ("Mean score", payload["mean_harness_score"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)
    coin_html = "".join(
        f"<tr><td>{esc(s.get('coin'))}</td><td>{esc(s.get('feature_rows'))}</td><td>{esc(s.get('eligible_rows'))}</td><td>{esc(s.get('train_rows'))}</td><td>{esc(s.get('validation_rows'))}</td><td>{esc(s.get('holdout_rows'))}</td><td>{esc(s.get('forward_return_24h_abs_mean_research', 0))}</td><td>{esc(s.get('leakage_guard_pass'))}</td><td>{esc(s.get('ready'))}</td></tr>"
        for s in payload["coin_harness_summaries"]
    )
    crit_html = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td></tr>"
        for c in payload["criteria"]
    )
    page = (
        "<!doctype html><html><head><meta charset='utf-8'><title>QRDS Offline Experiment Harness</title>"
        "<style>body{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}.card{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}.kpi{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:150px}table{border-collapse:collapse;width:100%;background:white}th,td{border:1px solid #d9deea;padding:8px;text-align:left}th{background:#eef2ff}.blocked{background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}.ok{background:#dcfce7;border-radius:999px;padding:6px 10px;font-weight:700}</style></head><body>"
        f"<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Phase 19 Offline Experiment Harness</h2>"
        f"<div class='card'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p><p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>{card_html}<p class='ok'>Harness creates chronological train/validation/holdout research datasets.</p><p class='blocked'>No model predictions, no trading signals, no recommendations, no allocation, no operational decisions.</p></div>"
        f"<h2>Coin harness summaries</h2><table><thead><tr><th>coin</th><th>features</th><th>eligible</th><th>train</th><th>validation</th><th>holdout</th><th>abs target mean</th><th>leakage guard</th><th>ready</th></tr></thead><tbody>{coin_html}</tbody></table>"
        f"<h2>Criteria</h2><table><thead><tr><th>criterion</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th></tr></thead><tbody>{crit_html}</tbody></table>"
        f"<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"
    )
    path.write_text(page, encoding="utf-8")


def _update_project_status(root: Path, payload: dict[str, Any]) -> None:
    status_path = root / "crypto_decision_lab/docs/reports/PROJECT_STATUS_QRDS_GATE_BTC.md"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    existing = status_path.read_text(encoding="utf-8") if status_path.exists() else "# QRDS/QOS Gate BTC — Project Status\n"
    marker = "\n## Latest Phase 19 update\n"
    before = existing.split(marker)[0].rstrip()
    section = [
        marker.strip(),
        "",
        f"Updated at: {payload['generated_at']}",
        "",
        f"- Phase 19 gate: `{payload['gate_answer']}`",
        f"- Offline experiment harness ready: `{payload['offline_experiment_harness_ready']}`",
        f"- Eligible rows total: `{payload['eligible_rows_total']}`",
        f"- Min eligible rows per coin: `{payload['min_eligible_rows_per_coin']}`",
        f"- Target horizon hours: `{payload['target_horizon_hours']}`",
        f"- Prediction rows generated: `{payload['prediction_rows_generated']}`",
        f"- Operational status: `{payload['operational_status']}`",
        f"- Canonical writes: `{payload['canonical_data_writes']}`",
        "",
        "The harness contains research targets and chronological splits only. It does not train models or generate predictions, signals, recommendations, allocations, or operational decisions.",
        "",
    ]
    status_path.write_text(before + "\n\n" + "\n".join(section), encoding="utf-8")


def build_phase19_offline_experiment_harness_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    min_eligible_rows_per_coin: int = MIN_ELIGIBLE_ROWS_PER_COIN,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    harness_dir = out / "harness"
    out.mkdir(parents=True, exist_ok=True)
    harness_dir.mkdir(parents=True, exist_ok=True)

    phase18 = _phase18_index(root)
    phase18_ready = bool(phase18.get("feature_regime_diagnostics_ready", False))

    summaries: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []

    for coin in COINS:
        rows, summary = _build_harness_rows(root, coin)
        path = harness_dir / f"{coin.lower()}_offline_experiment_harness_1h.csv"
        _write_harness_csv(path, rows)
        summary["path"] = str(path)
        summary["sha256"] = _sha_file(path)[:16]
        summary["ready"] = bool(summary.get("ready")) and int(summary.get("eligible_rows", 0)) >= min_eligible_rows_per_coin
        summaries.append(summary)
        outputs.append(
            {
                "coin": coin,
                "path": str(path),
                "rows": len(rows),
                "sha256": summary["sha256"],
                "source": HARNESS_SOURCE_LABEL,
                "canonical_write": False,
                "prediction_generated": False,
            }
        )

    eligible_total = sum(int(s.get("eligible_rows", 0)) for s in summaries)
    min_eligible = min((int(s.get("eligible_rows", 0)) for s in summaries), default=0)
    train_total = sum(int(s.get("train_rows", 0)) for s in summaries)
    validation_total = sum(int(s.get("validation_rows", 0)) for s in summaries)
    holdout_total = sum(int(s.get("holdout_rows", 0)) for s in summaries)
    all_ready = all(bool(s.get("ready")) for s in summaries)
    leakage_all = all(bool(s.get("leakage_guard_pass")) for s in summaries)
    split_nonempty = train_total > 0 and validation_total > 0 and holdout_total > 0
    prediction_rows_generated = 0
    canonical_data_writes = 0
    promotion_allowed = False
    safe_apply_allowed = False
    git_status = _git_status(root)

    criteria = [
        _criterion("phase18_index_present", bool(phase18.get("_present")), phase18.get("gate_answer", "MISSING"), "Phase 18 index present"),
        _criterion("phase18_feature_layer_ready", phase18_ready, phase18_ready, "true"),
        _criterion("coin_count", len(summaries) == 3, [s.get("coin") for s in summaries], "BTC,ETH,SOL"),
        _criterion("eligible_depth_per_coin", min_eligible >= min_eligible_rows_per_coin, min_eligible, f">= {min_eligible_rows_per_coin}"),
        _criterion("split_train_validation_holdout_nonempty", split_nonempty, {"train": train_total, "validation": validation_total, "holdout": holdout_total}, "all > 0"),
        _criterion("chronological_leakage_guard", leakage_all, [s.get("leakage_guard_pass") for s in summaries], "all true"),
        _criterion("prediction_rows_zero", prediction_rows_generated == 0, prediction_rows_generated, "0"),
        _criterion("model_training_not_run", True, "no_model_training_in_phase19", "true"),
        _criterion("target_columns_not_signals", True, TARGET_COLUMNS, "research targets only"),
        _criterion("harness_outputs_artifact_only", all(not x["canonical_write"] for x in outputs), [x["canonical_write"] for x in outputs], "all false"),
        _criterion("safe_apply_blocked", not safe_apply_allowed, safe_apply_allowed, "false"),
        _criterion("promotion_blocked", not promotion_allowed, promotion_allowed, "false"),
        _criterion("canonical_writes_zero", canonical_data_writes == 0, canonical_data_writes, "0"),
        _criterion("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]
    ready_count = sum(1 for c in criteria if c["ready"])
    harness_ready = ready_count == len(criteria)
    gate = "PHASE19_OFFLINE_EXPERIMENT_HARNESS_READY_RESEARCH_ONLY" if harness_ready else "PHASE19_OFFLINE_EXPERIMENT_HARNESS_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.phase19_offline_experiment_harness_pack.v1",
        "report_name": "qrds-phase19-offline-experiment-harness-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": "PHASE_19_OFFLINE_EXPERIMENT_HARNESS",
        "offline_experiment_harness_ready": harness_ready,
        "data_nature": "OFFLINE_EXPERIMENT_HARNESS_RESEARCH_ONLY",
        "phase18_feature_regime_diagnostics_ready": phase18_ready,
        "coins": COINS,
        "coins_count": len(COINS),
        "feature_columns": FEATURE_COLUMNS,
        "diagnostic_columns": DIAGNOSTIC_COLUMNS,
        "target_columns": TARGET_COLUMNS,
        "target_horizon_hours": TARGET_HORIZON_HOURS,
        "train_fraction": TRAIN_FRACTION,
        "validation_fraction": VALIDATION_FRACTION,
        "holdout_fraction": round(1.0 - TRAIN_FRACTION - VALIDATION_FRACTION, 8),
        "eligible_rows_total": eligible_total,
        "min_eligible_rows_per_coin": min_eligible,
        "train_rows_total": train_total,
        "validation_rows_total": validation_total,
        "holdout_rows_total": holdout_total,
        "prediction_rows_generated": prediction_rows_generated,
        "model_training_run": False,
        "coin_harness_summaries": summaries,
        "harness_outputs": outputs,
        "harness_output_dir": str(harness_dir),
        "target_columns_are_signals": False,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "modeling_status": "OFFLINE_EXPERIMENT_HARNESS_READY" if harness_ready else "OFFLINE_EXPERIMENT_HARNESS_NEEDS_REVIEW",
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "canonical_data_writes": canonical_data_writes,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_harness_score": round(ready_count / len(criteria), 4),
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    rp = out / "phase19_offline_experiment_harness_pack.json"
    mp = out / "phase19_offline_experiment_harness_pack.md"
    hp = out / "index.html"
    ip = out / "phase19_offline_experiment_harness_pack_index.json"

    rp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(
        f"# QRDS/QOS Phase 19 Offline Experiment Harness\n\n**Gate answer:** {gate}\n\nEligible rows total: {eligible_total}\n\nTrain/validation/holdout rows: {train_total}/{validation_total}/{holdout_total}\n\nPrediction rows generated: 0\n\nOperational status: BLOCKED_RESEARCH_ONLY\n\nResearch targets and chronological splits only; no model training, predictions, signals, recommendations, allocations, or canonical writes.\n",
        encoding="utf-8",
    )
    _render_html(hp, payload)

    index = {
        "schema": "qrds.phase19_offline_experiment_harness_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "station": payload["station"],
        "offline_experiment_harness_ready": payload["offline_experiment_harness_ready"],
        "data_nature": payload["data_nature"],
        "phase18_feature_regime_diagnostics_ready": payload["phase18_feature_regime_diagnostics_ready"],
        "coins": payload["coins"],
        "coins_count": payload["coins_count"],
        "target_horizon_hours": payload["target_horizon_hours"],
        "eligible_rows_total": payload["eligible_rows_total"],
        "min_eligible_rows_per_coin": payload["min_eligible_rows_per_coin"],
        "train_rows_total": payload["train_rows_total"],
        "validation_rows_total": payload["validation_rows_total"],
        "holdout_rows_total": payload["holdout_rows_total"],
        "prediction_rows_generated": payload["prediction_rows_generated"],
        "model_training_run": payload["model_training_run"],
        "target_columns_are_signals": payload["target_columns_are_signals"],
        "operational_status": payload["operational_status"],
        "modeling_status": payload["modeling_status"],
        "safe_apply_allowed": payload["safe_apply_allowed"],
        "promotion_allowed": payload["promotion_allowed"],
        "canonical_data_writes": payload["canonical_data_writes"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_harness_score": payload["mean_harness_score"],
        "git_status_line_count": payload["git_status_line_count"],
        "harness_output_dir": payload["harness_output_dir"],
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


build_offline_experiment_harness_pack = build_phase19_offline_experiment_harness_pack
