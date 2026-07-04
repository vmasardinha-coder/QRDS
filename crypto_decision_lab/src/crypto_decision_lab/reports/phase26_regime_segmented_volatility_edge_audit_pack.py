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
HARNESS_SOURCE = "QRDS_OFFLINE_EXPERIMENT_HARNESS_RESEARCH_ONLY"
SOURCE = "QRDS_REGIME_SEGMENTED_VOLATILITY_EDGE_AUDIT_RESEARCH_ONLY"
MIN_ROWS_PER_COIN = 3500
MIN_REGIME_ROWS = 100
EDGE_IMPROVEMENT_MAE_PCT = 0.05

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


def _mean(xs: list[float]) -> float:
    return statistics.fmean(xs) if xs else 0.0


def _median(xs: list[float]) -> float:
    return statistics.median(xs) if xs else 0.0


def _phase25(root: Path) -> dict[str, Any]:
    return _load_json(root / "crypto_decision_lab/artifacts/phase25_volatility_feature_baseline_strengthening_pack/phase25_volatility_feature_baseline_strengthening_pack_index.json")


def _harness_path(root: Path, coin: str) -> Path:
    return root / "crypto_decision_lab/artifacts/phase19_offline_experiment_harness_pack/harness" / f"{coin.lower()}_offline_experiment_harness_1h.csv"


def _harness_rows(root: Path, coin: str) -> list[dict[str, Any]]:
    return [r for r in _read_csv(_harness_path(root, coin)) if r.get("source") in {HARNESS_SOURCE, ""}]


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


def _mae(rows: list[dict[str, Any]], baseline_id: str, ctx: dict[str, Any], selected: str = "") -> float:
    if not rows:
        return 0.0
    return _mean([abs(_predict(r, baseline_id, ctx, selected) - _f(r.get(VOL_TARGET), 0.0)) for r in rows])


def _selected_validation_baseline(rows: list[dict[str, Any]], ctx: dict[str, Any]) -> str:
    val = [r for r in rows if r.get("split") == "VALIDATION_RESEARCH_ONLY"]
    scores = {
        bid: _mae(val, bid, ctx)
        for bid in BASELINE_IDS
        if bid != "VOL_VALIDATION_SELECTED_STRENGTHENED"
    }
    return min(scores, key=scores.get) if scores else "VOL_CURRENT_24H_PROXY"


def _evaluate_coin(root: Path, coin: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = _harness_rows(root, coin)
    if not rows:
        return [], {
            "coin": coin,
            "ready": False,
            "reason": "missing_harness_rows",
            "harness_rows": 0,
            "holdout_rows": 0,
            "regime_count": 0,
            "regime_edge_candidate_count": 0,
            "best_global_baseline_id": "MISSING",
            "best_global_holdout_mae": 0.0,
            "best_regime_improvement_pct": 0.0,
            "edge_research_candidate": False,
            "edge_operationally_validated": False,
            "schema_complete": True,
        }

    ctx = _fit_context(rows)
    selected = _selected_validation_baseline(rows, ctx)
    holdout = [r for r in rows if r.get("split") == "HOLDOUT_RESEARCH_ONLY"]

    global_scores = {}
    for bid in BASELINE_IDS:
        global_scores[bid] = _mae(holdout, bid, ctx, selected)
    best_global_id = min(global_scores, key=global_scores.get) if global_scores else "MISSING"
    best_global_mae = global_scores.get(best_global_id, 0.0)

    regimes: dict[str, list[dict[str, Any]]] = {}
    for r in holdout:
        regimes.setdefault(_regime_key(r), []).append(r)

    regime_rows: list[dict[str, Any]] = []
    for regime, rr in sorted(regimes.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        scores = {bid: _mae(rr, bid, ctx, selected) for bid in BASELINE_IDS}
        best_id = min(scores, key=scores.get) if scores else "MISSING"
        best_mae = scores.get(best_id, 0.0)
        improvement = best_global_mae - best_mae if best_global_mae > 0 else 0.0
        improvement_pct = improvement / best_global_mae if best_global_mae > 0 else 0.0
        enough_rows = len(rr) >= MIN_REGIME_ROWS
        candidate = bool(enough_rows and improvement_pct >= EDGE_IMPROVEMENT_MAE_PCT)
        regime_rows.append({
            "coin": coin,
            "regime_key": regime,
            "holdout_rows": len(rr),
            "best_regime_baseline_id": best_id,
            "best_regime_mae": round(best_mae, 12),
            "best_global_baseline_id": best_global_id,
            "best_global_holdout_mae": round(best_global_mae, 12),
            "mae_improvement_vs_global": round(improvement, 12),
            "mae_improvement_pct_vs_global": round(improvement_pct, 8),
            "min_rows_pass": enough_rows,
            "edge_research_candidate": candidate,
            "edge_operationally_validated": False,
            "trading_signal_generated": False,
            "recommendation_generated": False,
            "operational_decision_allowed": False,
            "source": SOURCE,
        })

    candidates = [r for r in regime_rows if r["edge_research_candidate"]]
    summary = {
        "coin": coin,
        "ready": True,
        "reason": "",
        "harness_rows": len(rows),
        "train_rows": sum(1 for r in rows if r.get("split") == "TRAIN_RESEARCH_ONLY"),
        "validation_rows": sum(1 for r in rows if r.get("split") == "VALIDATION_RESEARCH_ONLY"),
        "holdout_rows": len(holdout),
        "regime_count": len(regime_rows),
        "regime_edge_candidate_count": len(candidates),
        "best_global_baseline_id": best_global_id,
        "best_global_holdout_mae": round(best_global_mae, 12),
        "best_regime_improvement_pct": max((r["mae_improvement_pct_vs_global"] for r in regime_rows), default=0.0),
        "selected_validation_baseline": selected,
        "edge_research_candidate": bool(candidates),
        "edge_operationally_validated": False,
        "schema_complete": True,
    }
    return regime_rows, summary


def _criterion(cid: str, ok: bool, observed: Any, threshold: str) -> dict[str, Any]:
    return {"criterion_id": cid, "status": "PASS" if ok else "FAIL", "ready": bool(ok), "observed": observed, "threshold": threshold}


def _render_html(path: Path, payload: dict[str, Any]) -> None:
    esc = lambda x: html.escape(str(x))
    cards = [
        ("Gate", payload["regime_segmented_edge_audit_ready"]),
        ("Phase25", payload["phase25_strengthening_ready"]),
        ("Regimes", payload["regime_rows_total"]),
        ("Edge candidates", payload["regime_edge_candidate_count_total"]),
        ("Operational edge", payload["edge_operationally_validated"]),
        ("Decision eligible", payload["decision_layer_allowed"]),
        ("Operational", payload["operational_status"]),
        ("Score", payload["mean_edge_audit_score"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)
    coin_html = "".join(
        f"<tr><td>{esc(s['coin'])}</td><td>{esc(s['holdout_rows'])}</td><td>{esc(s['regime_count'])}</td><td>{esc(s['regime_edge_candidate_count'])}</td><td>{esc(s['best_global_baseline_id'])}</td><td>{esc(s['best_global_holdout_mae'])}</td><td>{esc(s['best_regime_improvement_pct'])}</td><td>{esc(s['edge_research_candidate'])}</td></tr>"
        for s in payload["coin_edge_summaries"]
    )
    regime_html = "".join(
        f"<tr><td>{esc(r['coin'])}</td><td>{esc(r['regime_key'])}</td><td>{esc(r['holdout_rows'])}</td><td>{esc(r['best_regime_baseline_id'])}</td><td>{esc(r['mae_improvement_pct_vs_global'])}</td><td>{esc(r['edge_research_candidate'])}</td></tr>"
        for r in payload["regime_edge_preview"]
    )
    crit_html = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td></tr>"
        for c in payload["criteria"]
    )
    page = (
        "<!doctype html><html><head><meta charset='utf-8'><title>QRDS Phase 26 Edge Audit</title>"
        "<style>body{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}.kpi{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:150px}.card{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}table{border-collapse:collapse;width:100%;background:white}th,td{border:1px solid #d9deea;padding:8px;text-align:left}th{background:#eef2ff}.blocked{background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}</style></head><body>"
        f"<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Phase 26 Regime-Segmented Volatility Edge Audit</h2>"
        f"<div class='card'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p>{card_html}<p class='blocked'>Research edge candidates are not operational edge, signals, recommendations, allocations, or decisions.</p></div>"
        f"<h2>Coin summaries</h2><table><thead><tr><th>coin</th><th>holdout rows</th><th>regimes</th><th>candidates</th><th>global baseline</th><th>global MAE</th><th>best regime improvement pct</th><th>research candidate</th></tr></thead><tbody>{coin_html}</tbody></table>"
        f"<h2>Regime preview</h2><table><thead><tr><th>coin</th><th>regime</th><th>rows</th><th>best baseline</th><th>improvement pct</th><th>candidate</th></tr></thead><tbody>{regime_html}</tbody></table>"
        f"<h2>Criteria</h2><table><thead><tr><th>criterion</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th></tr></thead><tbody>{crit_html}</tbody></table>"
        f"<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"
    )
    path.write_text(page, encoding="utf-8")


def _update_project_status(root: Path, payload: dict[str, Any]) -> None:
    status_path = root / "crypto_decision_lab/docs/reports/PROJECT_STATUS_QRDS_GATE_BTC.md"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    existing = status_path.read_text(encoding="utf-8") if status_path.exists() else "# QRDS/QOS Gate BTC — Project Status\n"
    marker = "\n## Latest Phase 26 update\n"
    before = existing.split(marker)[0].rstrip()
    section = [
        marker.strip(), "",
        f"Updated at: {payload['generated_at']}", "",
        f"- Phase 26 gate: `{payload['gate_answer']}`",
        f"- Regime edge audit ready: `{payload['regime_segmented_edge_audit_ready']}`",
        f"- Research edge candidates: `{payload['regime_edge_candidate_count_total']}`",
        f"- Operational edge validated: `{payload['edge_operationally_validated']}`",
        f"- Decision layer allowed: `{payload['decision_layer_allowed']}`",
        f"- Operational status: `{payload['operational_status']}`",
        f"- Canonical writes: `{payload['canonical_data_writes']}`", "",
        "Phase 26 audits potential edge by regime. Research candidates are not operational edge and do not authorize signals, recommendations, allocations, or decisions.", "",
    ]
    status_path.write_text(before + "\n\n" + "\n".join(section), encoding="utf-8")


def build_phase26_regime_segmented_volatility_edge_audit_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    min_rows_per_coin: int = MIN_ROWS_PER_COIN,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    phase25 = _phase25(root)
    phase25_ready = bool(phase25.get("vol_feature_baseline_strengthening_ready", False))

    all_regimes: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for coin in COINS:
        regime_rows, summary = _evaluate_coin(root, coin)
        summary["ready"] = bool(summary.get("ready")) and int(summary.get("harness_rows", 0)) >= min_rows_per_coin
        all_regimes.extend(regime_rows)
        summaries.append(summary)

    regime_path = out / "regime_segmented_edge_audit.csv"
    summary_path = out / "coin_edge_summaries.csv"
    regime_fields = ["coin","regime_key","holdout_rows","best_regime_baseline_id","best_regime_mae","best_global_baseline_id","best_global_holdout_mae","mae_improvement_vs_global","mae_improvement_pct_vs_global","min_rows_pass","edge_research_candidate","edge_operationally_validated","trading_signal_generated","recommendation_generated","operational_decision_allowed","source"]
    summary_fields = ["coin","ready","reason","harness_rows","train_rows","validation_rows","holdout_rows","regime_count","regime_edge_candidate_count","best_global_baseline_id","best_global_holdout_mae","best_regime_improvement_pct","selected_validation_baseline","edge_research_candidate","edge_operationally_validated","schema_complete"]
    _write_csv(regime_path, all_regimes, regime_fields)
    _write_csv(summary_path, summaries, summary_fields)

    regime_candidates = [r for r in all_regimes if r["edge_research_candidate"]]
    candidate_count = len(regime_candidates)
    coins_with_candidate = len({r["coin"] for r in regime_candidates})
    min_rows = min((int(s.get("harness_rows", 0)) for s in summaries), default=0)

    edge_operationally_validated = False
    decision_layer_allowed = False
    canonical_data_writes = 0
    promotion_allowed = False
    safe_apply_allowed = False
    git_status = _git_status(root)

    criteria = [
        _criterion("phase25_index_present", bool(phase25.get("_present")), phase25.get("gate_answer", "MISSING"), "Phase 25 index present"),
        _criterion("phase25_strengthening_ready", phase25_ready, phase25_ready, "true"),
        _criterion("coin_count", len(summaries) == 3, [s.get("coin") for s in summaries], "BTC,ETH,SOL"),
        _criterion("harness_depth_per_coin", min_rows >= min_rows_per_coin, min_rows, f">= {min_rows_per_coin}"),
        _criterion("regime_rows_present", len(all_regimes) > 0, len(all_regimes), ">0 regime rows"),
        _criterion("coin_summaries_ready", all(bool(s.get("ready")) for s in summaries), [s.get("ready") for s in summaries], "all true"),
        _criterion("research_edge_not_operational", edge_operationally_validated is False, edge_operationally_validated, "false"),
        _criterion("decision_layer_blocked", decision_layer_allowed is False, decision_layer_allowed, "false"),
        _criterion("signals_blocked", True, "research_edge_audit_only", "no signal/recommendation/allocation"),
        _criterion("safe_apply_blocked", not safe_apply_allowed, safe_apply_allowed, "false"),
        _criterion("promotion_blocked", not promotion_allowed, promotion_allowed, "false"),
        _criterion("canonical_writes_zero", canonical_data_writes == 0, canonical_data_writes, "0"),
        _criterion("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]
    ready_count = sum(1 for c in criteria if c["ready"])
    ready = ready_count == len(criteria)
    gate = "PHASE26_REGIME_SEGMENTED_VOLATILITY_EDGE_AUDIT_READY_RESEARCH_ONLY" if ready else "PHASE26_REGIME_SEGMENTED_VOLATILITY_EDGE_AUDIT_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.phase26_regime_segmented_volatility_edge_audit_pack.v1",
        "report_name": "qrds-phase26-regime-segmented-volatility-edge-audit-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": "PHASE_26_REGIME_SEGMENTED_VOLATILITY_EDGE_AUDIT",
        "regime_segmented_edge_audit_ready": ready,
        "phase25_strengthening_ready": phase25_ready,
        "data_nature": "REGIME_SEGMENTED_VOLATILITY_EDGE_AUDIT_RESEARCH_ONLY",
        "edge_definition": "Edge, in this project, means repeatable out-of-sample improvement over strong baselines after costs/robustness gates; Phase 26 can only find research candidates, not operational edge.",
        "coins": COINS,
        "coins_count": len(COINS),
        "target": VOL_TARGET,
        "regime_rows_total": len(all_regimes),
        "regime_edge_candidate_count_total": candidate_count,
        "coins_with_regime_edge_candidate": coins_with_candidate,
        "min_regime_rows_threshold": MIN_REGIME_ROWS,
        "edge_improvement_mae_pct_threshold": EDGE_IMPROVEMENT_MAE_PCT,
        "edge_operationally_validated": edge_operationally_validated,
        "decision_layer_allowed": decision_layer_allowed,
        "coin_edge_summaries": summaries,
        "regime_edge_preview": all_regimes[:24],
        "regime_edge_candidates_preview": regime_candidates[:24],
        "regime_audit_path": str(regime_path),
        "coin_summary_path": str(summary_path),
        "regime_audit_sha256": _sha_file(regime_path)[:16],
        "coin_summary_sha256": _sha_file(summary_path)[:16],
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "modeling_status": "REGIME_SEGMENTED_EDGE_AUDIT_READY" if ready else "REGIME_SEGMENTED_EDGE_AUDIT_NEEDS_REVIEW",
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "canonical_data_writes": canonical_data_writes,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_edge_audit_score": round(ready_count / len(criteria), 4),
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    rp = out / "phase26_regime_segmented_volatility_edge_audit_pack.json"
    mp = out / "phase26_regime_segmented_volatility_edge_audit_pack.md"
    hp = out / "index.html"
    ip = out / "phase26_regime_segmented_volatility_edge_audit_pack_index.json"

    rp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(
        f"# QRDS/QOS Phase 26 Regime-Segmented Volatility Edge Audit\n\n**Gate answer:** {gate}\n\nResearch edge candidates: {candidate_count}\n\nCoins with candidates: {coins_with_candidate}\n\nOperational edge validated: false\n\nDecision layer allowed: false\n\nOperational status: BLOCKED_RESEARCH_ONLY\n\nResearch candidates are not signals, recommendations, allocations, or operational decisions.\n",
        encoding="utf-8",
    )
    _render_html(hp, payload)

    index = {
        "schema": "qrds.phase26_regime_segmented_volatility_edge_audit_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": payload["station"],
        "regime_segmented_edge_audit_ready": ready,
        "phase25_strengthening_ready": phase25_ready,
        "data_nature": payload["data_nature"],
        "regime_rows_total": len(all_regimes),
        "regime_edge_candidate_count_total": candidate_count,
        "coins_with_regime_edge_candidate": coins_with_candidate,
        "edge_operationally_validated": edge_operationally_validated,
        "decision_layer_allowed": decision_layer_allowed,
        "operational_status": payload["operational_status"],
        "modeling_status": payload["modeling_status"],
        "safe_apply_allowed": payload["safe_apply_allowed"],
        "promotion_allowed": payload["promotion_allowed"],
        "canonical_data_writes": payload["canonical_data_writes"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_edge_audit_score": payload["mean_edge_audit_score"],
        "git_status_line_count": payload["git_status_line_count"],
        "regime_audit_path": str(regime_path),
        "coin_summary_path": str(summary_path),
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


build_regime_segmented_volatility_edge_audit_pack = build_phase26_regime_segmented_volatility_edge_audit_pack
