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
VOL_TARGET = "forward_realized_vol_24h_research_target"
SOURCE = "QRDS_VOL_RESIDUAL_DIAGNOSTICS_BASELINE_ROBUSTNESS_RESEARCH_ONLY"
MIN_HOLDOUT_ROWS = 15

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


def _pct(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    i = min(max(int(round((len(s)-1)*p)), 0), len(s)-1)
    return s[i]


def _phase23(root: Path) -> dict[str, Any]:
    return _load_json(root / "crypto_decision_lab/artifacts/phase23_volatility_first_research_benchmark_pack/phase23_volatility_first_research_benchmark_pack_index.json")


def _phase23_metrics_path(root: Path, phase23: dict[str, Any]) -> Path:
    raw = phase23.get("combined_vol_model_metrics_path")
    if raw:
        return Path(raw)
    return root / "crypto_decision_lab/artifacts/phase23_volatility_first_research_benchmark_pack/volatility_models/all_volatility_first_metrics.csv"


def _harness_path(root: Path, coin: str) -> Path:
    return root / "crypto_decision_lab/artifacts/phase19_offline_experiment_harness_pack/harness" / f"{coin.lower()}_offline_experiment_harness_1h.csv"


def _diagnose_metrics(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    holdout = [r for r in rows if r.get("split") == "HOLDOUT_RESEARCH_ONLY"]
    coin_rows: list[dict[str, Any]] = []
    model_rows: list[dict[str, Any]] = []

    for coin in COINS:
        cr = [r for r in holdout if r.get("coin") == coin]
        beats = sum(1 for r in cr if _b(r.get("beats_best_phase20_vol_baseline")))
        imps = [_f(r.get("mae_improvement_vs_best_phase20_vol_baseline"), 0.0) for r in cr]
        maes = [_f(r.get("mae"), 0.0) for r in cr]
        baseline_maes = [_f(r.get("best_phase20_vol_baseline_mae"), 0.0) for r in cr]
        best = min(cr, key=lambda r: _f(r.get("mae"), 999999.0)) if cr else {}
        coin_rows.append({
            "coin": coin,
            "holdout_model_rows": len(cr),
            "holdout_beats": beats,
            "holdout_beat_rate": round(beats / len(cr), 8) if cr else 0.0,
            "mean_improvement": round(_mean(imps), 12),
            "median_improvement": round(_median(imps), 12),
            "best_model_id": best.get("model_id", "MISSING"),
            "best_model_mae": best.get("mae", 0.0),
            "best_baseline_mae": best.get("best_phase20_vol_baseline_mae", 0.0),
            "best_improvement": best.get("mae_improvement_vs_best_phase20_vol_baseline", 0.0),
            "mae_spread_model_vs_baseline_mean": round(_mean(maes) - _mean(baseline_maes), 12) if cr else 0.0,
            "research_interpretation": "VOL_MODEL_WEAK_OR_MIXED_RESEARCH_ONLY" if beats < max(2, len(cr)//2) else "VOL_MODEL_HAS_PARTIAL_EVIDENCE_RESEARCH_ONLY",
            "trading_signal_generated": False,
            "recommendation_generated": False,
            "operational_decision_allowed": False,
        })

    for model_id in sorted({r.get("model_id", "") for r in holdout if r.get("model_id")}):
        mr = [r for r in holdout if r.get("model_id") == model_id]
        beats = sum(1 for r in mr if _b(r.get("beats_best_phase20_vol_baseline")))
        imps = [_f(r.get("mae_improvement_vs_best_phase20_vol_baseline"), 0.0) for r in mr]
        model_rows.append({
            "model_id": model_id,
            "coins_tested": len(mr),
            "coin_beats": beats,
            "coin_beat_rate": round(beats / len(mr), 8) if mr else 0.0,
            "mean_improvement": round(_mean(imps), 12),
            "median_improvement": round(_median(imps), 12),
            "p25_improvement": round(_pct(imps, 0.25), 12),
            "p75_improvement": round(_pct(imps, 0.75), 12),
            "research_interpretation": "MODEL_NOT_ROBUST_RESEARCH_ONLY" if beats < 2 else "MODEL_PARTIALLY_ROBUST_RESEARCH_ONLY",
            "trading_signal_generated": False,
            "recommendation_generated": False,
            "operational_decision_allowed": False,
        })

    total_beats = sum(1 for r in holdout if _b(r.get("beats_best_phase20_vol_baseline")))
    coins_improved = sum(1 for r in coin_rows if _f(r.get("best_improvement"), 0.0) > 0)
    best_model_robust = max((r["coin_beat_rate"] for r in model_rows), default=0.0)
    diagnostic_path = (
        "STRENGTHEN_VOLATILITY_BASELINES_AND_FEATURES_RESEARCH_ONLY"
        if total_beats < max(2, len(holdout)//3) or coins_improved < 2 or best_model_robust < 0.67
        else "VOLATILITY_MODEL_CAN_BE_STUDIED_FURTHER_RESEARCH_ONLY"
    )
    overall = {
        "holdout_model_rows": len(holdout),
        "holdout_beats_total": total_beats,
        "holdout_beat_rate_total": round(total_beats / len(holdout), 8) if holdout else 0.0,
        "coins_with_best_model_improvement": coins_improved,
        "max_model_coin_beat_rate": round(best_model_robust, 8),
        "diagnostic_path_forward": diagnostic_path,
        "complex_model_allowed_by_triage": False,
        "return_model_advancement_allowed": False,
        "vol_model_operationalization_allowed": False,
    }
    return coin_rows, model_rows, overall


def _target_distribution(root: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for coin in COINS:
        rows = [r for r in _read_csv(_harness_path(root, coin)) if r.get("split") == "HOLDOUT_RESEARCH_ONLY"]
        vals = [_f(r.get(VOL_TARGET), 0.0) for r in rows]
        out.append({
            "coin": coin,
            "holdout_rows": len(rows),
            "target_mean": round(_mean(vals), 12),
            "target_median": round(_median(vals), 12),
            "target_p25": round(_pct(vals, 0.25), 12),
            "target_p75": round(_pct(vals, 0.75), 12),
            "target_p95": round(_pct(vals, 0.95), 12),
            "target_max": round(max(vals) if vals else 0.0, 12),
            "source": SOURCE,
        })
    return out


def _criterion(cid: str, ok: bool, observed: Any, threshold: str) -> dict[str, Any]:
    return {"criterion_id": cid, "status": "PASS" if ok else "FAIL", "ready": bool(ok), "observed": observed, "threshold": threshold}


def _render_html(path: Path, payload: dict[str, Any]) -> None:
    esc = lambda x: html.escape(str(x))
    cards = [
        ("Diag ready", payload["vol_residual_diagnostics_ready"]),
        ("Phase23", payload["phase23_vol_benchmark_ready"]),
        ("Holdout beats", payload["holdout_beats_total"]),
        ("Coins improved", payload["coins_with_best_model_improvement"]),
        ("Path", payload["diagnostic_path_forward"]),
        ("Complex allowed", payload["complex_model_allowed_by_triage"]),
        ("Operational", payload["operational_status"]),
        ("Score", payload["mean_diagnostic_score"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)
    coin_html = "".join(
        f"<tr><td>{esc(r['coin'])}</td><td>{esc(r['holdout_model_rows'])}</td><td>{esc(r['holdout_beats'])}</td><td>{esc(r['holdout_beat_rate'])}</td><td>{esc(r['best_model_id'])}</td><td>{esc(r['best_improvement'])}</td><td>{esc(r['research_interpretation'])}</td></tr>"
        for r in payload["coin_diagnostics"]
    )
    model_html = "".join(
        f"<tr><td>{esc(r['model_id'])}</td><td>{esc(r['coins_tested'])}</td><td>{esc(r['coin_beats'])}</td><td>{esc(r['coin_beat_rate'])}</td><td>{esc(r['mean_improvement'])}</td><td>{esc(r['research_interpretation'])}</td></tr>"
        for r in payload["model_robustness_diagnostics"]
    )
    crit_html = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td></tr>"
        for c in payload["criteria"]
    )
    page = (
        "<!doctype html><html><head><meta charset='utf-8'><title>QRDS Phase 24 Vol Diagnostics</title>"
        "<style>body{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}.kpi{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:150px}.card{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}table{border-collapse:collapse;width:100%;background:white}th,td{border:1px solid #d9deea;padding:8px;text-align:left}th{background:#eef2ff}.blocked{background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}</style></head><body>"
        f"<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Phase 24 Volatility Residual Diagnostics + Baseline Robustness</h2>"
        f"<div class='card'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p>{card_html}<p class='blocked'>Diagnostic path labels are not signals, recommendations, allocations, or operational decisions.</p></div>"
        f"<h2>Coin diagnostics</h2><table><thead><tr><th>coin</th><th>models</th><th>beats</th><th>beat rate</th><th>best model</th><th>best improvement</th><th>interpretation</th></tr></thead><tbody>{coin_html}</tbody></table>"
        f"<h2>Model robustness</h2><table><thead><tr><th>model</th><th>coins</th><th>beats</th><th>beat rate</th><th>mean improvement</th><th>interpretation</th></tr></thead><tbody>{model_html}</tbody></table>"
        f"<h2>Criteria</h2><table><thead><tr><th>criterion</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th></tr></thead><tbody>{crit_html}</tbody></table>"
        f"<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"
    )
    path.write_text(page, encoding="utf-8")


def _update_project_status(root: Path, payload: dict[str, Any]) -> None:
    status_path = root / "crypto_decision_lab/docs/reports/PROJECT_STATUS_QRDS_GATE_BTC.md"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    existing = status_path.read_text(encoding="utf-8") if status_path.exists() else "# QRDS/QOS Gate BTC — Project Status\n"
    marker = "\n## Latest Phase 24 update\n"
    before = existing.split(marker)[0].rstrip()
    section = [
        marker.strip(), "",
        f"Updated at: {payload['generated_at']}", "",
        f"- Phase 24 gate: `{payload['gate_answer']}`",
        f"- Diagnostics ready: `{payload['vol_residual_diagnostics_ready']}`",
        f"- Diagnostic path forward: `{payload['diagnostic_path_forward']}`",
        f"- Complex model allowed by triage: `{payload['complex_model_allowed_by_triage']}`",
        f"- Holdout beats total: `{payload['holdout_beats_total']}`",
        f"- Coins with best model improvement: `{payload['coins_with_best_model_improvement']}`",
        f"- Operational status: `{payload['operational_status']}`",
        f"- Canonical writes: `{payload['canonical_data_writes']}`", "",
        "Phase 24 is diagnostics only and recommends no operational action. It blocks complex-model escalation when robustness is weak.", "",
    ]
    status_path.write_text(before + "\n\n" + "\n".join(section), encoding="utf-8")


def build_phase24_volatility_residual_diagnostics_baseline_robustness_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    phase23 = _phase23(root)
    phase23_ready = bool(phase23.get("volatility_first_benchmark_ready", False))
    metrics_path = Path(phase23.get("combined_vol_model_metrics_path") or root / "crypto_decision_lab/artifacts/phase23_volatility_first_research_benchmark_pack/volatility_models/all_volatility_first_metrics.csv")
    metrics = _read_csv(metrics_path)

    coin_diag, model_diag, overall = _diagnose_metrics(metrics)
    target_dist = _target_distribution(root)

    coin_path = out / "coin_volatility_diagnostics.csv"
    model_path = out / "model_robustness_diagnostics.csv"
    target_path = out / "holdout_vol_target_distribution.csv"
    _write_csv(coin_path, coin_diag, ["coin","holdout_model_rows","holdout_beats","holdout_beat_rate","mean_improvement","median_improvement","best_model_id","best_model_mae","best_baseline_mae","best_improvement","mae_spread_model_vs_baseline_mean","research_interpretation","trading_signal_generated","recommendation_generated","operational_decision_allowed"])
    _write_csv(model_path, model_diag, ["model_id","coins_tested","coin_beats","coin_beat_rate","mean_improvement","median_improvement","p25_improvement","p75_improvement","research_interpretation","trading_signal_generated","recommendation_generated","operational_decision_allowed"])
    _write_csv(target_path, target_dist, ["coin","holdout_rows","target_mean","target_median","target_p25","target_p75","target_p95","target_max","source"])

    canonical_data_writes = 0
    promotion_allowed = False
    safe_apply_allowed = False
    git_status = _git_status(root)

    criteria = [
        _criterion("phase23_index_present", bool(phase23.get("_present")), phase23.get("gate_answer", "MISSING"), "Phase 23 index present"),
        _criterion("phase23_vol_benchmark_ready", phase23_ready, phase23_ready, "true"),
        _criterion("phase23_metrics_present", len(metrics) >= 45, len(metrics), ">=45 Phase 23 metric rows"),
        _criterion("holdout_rows_present", overall["holdout_model_rows"] >= MIN_HOLDOUT_ROWS, overall["holdout_model_rows"], f">= {MIN_HOLDOUT_ROWS}"),
        _criterion("coin_diagnostics_complete", len(coin_diag) == len(COINS), len(coin_diag), "BTC,ETH,SOL diagnostics"),
        _criterion("model_diagnostics_present", len(model_diag) >= 5, len(model_diag), ">=5 model diagnostics"),
        _criterion("complex_model_blocked_when_weak", overall["complex_model_allowed_by_triage"] is False, overall["complex_model_allowed_by_triage"], "false when robustness weak"),
        _criterion("return_advancement_blocked", overall["return_model_advancement_allowed"] is False, overall["return_model_advancement_allowed"], "false"),
        _criterion("operationalization_blocked", overall["vol_model_operationalization_allowed"] is False, overall["vol_model_operationalization_allowed"], "false"),
        _criterion("diagnostics_not_signals", True, "research_diagnostics_only", "no signal"),
        _criterion("safe_apply_blocked", not safe_apply_allowed, safe_apply_allowed, "false"),
        _criterion("promotion_blocked", not promotion_allowed, promotion_allowed, "false"),
        _criterion("canonical_writes_zero", canonical_data_writes == 0, canonical_data_writes, "0"),
        _criterion("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]
    ready_count = sum(1 for c in criteria if c["ready"])
    ready = ready_count == len(criteria)
    gate = "PHASE24_VOLATILITY_RESIDUAL_DIAGNOSTICS_BASELINE_ROBUSTNESS_READY_RESEARCH_ONLY" if ready else "PHASE24_VOLATILITY_RESIDUAL_DIAGNOSTICS_BASELINE_ROBUSTNESS_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.phase24_volatility_residual_diagnostics_baseline_robustness_pack.v1",
        "report_name": "qrds-phase24-volatility-residual-diagnostics-baseline-robustness-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": "PHASE_24_VOLATILITY_RESIDUAL_DIAGNOSTICS_BASELINE_ROBUSTNESS",
        "vol_residual_diagnostics_ready": ready,
        "phase23_vol_benchmark_ready": phase23_ready,
        "data_nature": "VOLATILITY_RESIDUAL_DIAGNOSTICS_BASELINE_ROBUSTNESS_RESEARCH_ONLY",
        "phase23_metric_rows": len(metrics),
        **overall,
        "coin_diagnostics": coin_diag,
        "model_robustness_diagnostics": model_diag,
        "target_distribution": target_dist,
        "coin_diagnostics_path": str(coin_path),
        "model_robustness_diagnostics_path": str(model_path),
        "target_distribution_path": str(target_path),
        "coin_diagnostics_sha256": _sha_file(coin_path)[:16],
        "model_robustness_diagnostics_sha256": _sha_file(model_path)[:16],
        "target_distribution_sha256": _sha_file(target_path)[:16],
        "diagnostic_labels_are_signals": False,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "modeling_status": "VOL_RESIDUAL_DIAGNOSTICS_READY" if ready else "VOL_RESIDUAL_DIAGNOSTICS_NEEDS_REVIEW",
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "canonical_data_writes": canonical_data_writes,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_diagnostic_score": round(ready_count / len(criteria), 4),
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    rp = out / "phase24_volatility_residual_diagnostics_baseline_robustness_pack.json"
    mp = out / "phase24_volatility_residual_diagnostics_baseline_robustness_pack.md"
    hp = out / "index.html"
    ip = out / "phase24_volatility_residual_diagnostics_baseline_robustness_pack_index.json"
    rp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(f"# QRDS/QOS Phase 24 Volatility Residual Diagnostics + Baseline Robustness\n\n**Gate answer:** {gate}\n\nDiagnostic path forward: `{overall['diagnostic_path_forward']}`\n\nComplex model allowed by triage: false\n\nOperational status: BLOCKED_RESEARCH_ONLY\n\nDiagnostics only; no signal, recommendation, allocation, or operational decision.\n", encoding="utf-8")
    _render_html(hp, payload)

    index = {
        "schema": "qrds.phase24_volatility_residual_diagnostics_baseline_robustness_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": payload["station"],
        "vol_residual_diagnostics_ready": ready,
        "phase23_vol_benchmark_ready": phase23_ready,
        "data_nature": payload["data_nature"],
        "phase23_metric_rows": len(metrics),
        "holdout_model_rows": overall["holdout_model_rows"],
        "holdout_beats_total": overall["holdout_beats_total"],
        "holdout_beat_rate_total": overall["holdout_beat_rate_total"],
        "coins_with_best_model_improvement": overall["coins_with_best_model_improvement"],
        "max_model_coin_beat_rate": overall["max_model_coin_beat_rate"],
        "diagnostic_path_forward": overall["diagnostic_path_forward"],
        "complex_model_allowed_by_triage": overall["complex_model_allowed_by_triage"],
        "return_model_advancement_allowed": overall["return_model_advancement_allowed"],
        "vol_model_operationalization_allowed": overall["vol_model_operationalization_allowed"],
        "diagnostic_labels_are_signals": False,
        "operational_status": payload["operational_status"],
        "modeling_status": payload["modeling_status"],
        "safe_apply_allowed": payload["safe_apply_allowed"],
        "promotion_allowed": payload["promotion_allowed"],
        "canonical_data_writes": payload["canonical_data_writes"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_diagnostic_score": payload["mean_diagnostic_score"],
        "git_status_line_count": payload["git_status_line_count"],
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


build_volatility_residual_diagnostics_baseline_robustness_pack = build_phase24_volatility_residual_diagnostics_baseline_robustness_pack
