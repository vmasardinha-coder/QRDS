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
SOURCE = "QRDS_EDGE_CANDIDATE_STABILITY_ANTI_OVERFIT_RESEARCH_ONLY"

MIN_CANDIDATE_ROWS = 100
MIN_SEGMENT_ROWS = 25
MIN_FULL_IMPROVEMENT_PCT = 0.05

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


def _bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"true", "1", "yes", "y"}


def _mean(xs: list[float]) -> float:
    return statistics.fmean(xs) if xs else 0.0


def _median(xs: list[float]) -> float:
    return statistics.median(xs) if xs else 0.0


def _phase26(root: Path) -> dict[str, Any]:
    return _load_json(root / "crypto_decision_lab/artifacts/phase26_regime_segmented_volatility_edge_audit_pack/phase26_regime_segmented_volatility_edge_audit_pack_index.json")


def _phase26_regime_path(root: Path, phase26: dict[str, Any]) -> Path:
    raw = phase26.get("regime_audit_path")
    if raw:
        return Path(raw)
    return root / "crypto_decision_lab/artifacts/phase26_regime_segmented_volatility_edge_audit_pack/regime_segmented_edge_audit.csv"


def _harness_path(root: Path, coin: str) -> Path:
    return root / "crypto_decision_lab/artifacts/phase19_offline_experiment_harness_pack/harness" / f"{coin.lower()}_offline_experiment_harness_1h.csv"


def _harness_rows(root: Path, coin: str) -> list[dict[str, Any]]:
    rows = [r for r in _read_csv(_harness_path(root, coin)) if r.get("source") in {HARNESS_SOURCE, ""}]
    return sorted(rows, key=lambda r: str(r.get("timestamp", "")))


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


def _eval_segment(rows: list[dict[str, Any]], candidate_id: str, global_id: str, ctx: dict[str, Any], selected: str) -> dict[str, float]:
    cand_mae = _mae(rows, candidate_id, ctx, selected)
    global_mae = _mae(rows, global_id, ctx, selected)
    improvement = global_mae - cand_mae if global_mae > 0 else 0.0
    pct = improvement / global_mae if global_mae > 0 else 0.0
    return {
        "candidate_mae": round(cand_mae, 12),
        "global_mae": round(global_mae, 12),
        "improvement": round(improvement, 12),
        "improvement_pct": round(pct, 8),
    }


def _evaluate_candidate(root: Path, candidate: dict[str, Any]) -> dict[str, Any]:
    coin = str(candidate.get("coin", ""))
    regime = str(candidate.get("regime_key", ""))
    candidate_id = str(candidate.get("best_regime_baseline_id", "MISSING"))
    global_id = str(candidate.get("best_global_baseline_id", "MISSING"))

    rows = _harness_rows(root, coin)
    ctx = _fit_context(rows)
    selected = _selected_validation_baseline(rows, ctx)
    holdout_regime = [r for r in rows if r.get("split") == "HOLDOUT_RESEARCH_ONLY" and _regime_key(r) == regime]

    mid = len(holdout_regime) // 2
    early = holdout_regime[:mid]
    late = holdout_regime[mid:]

    full_m = _eval_segment(holdout_regime, candidate_id, global_id, ctx, selected)
    early_m = _eval_segment(early, candidate_id, global_id, ctx, selected)
    late_m = _eval_segment(late, candidate_id, global_id, ctx, selected)

    rows_pass = len(holdout_regime) >= MIN_CANDIDATE_ROWS and len(early) >= MIN_SEGMENT_ROWS and len(late) >= MIN_SEGMENT_ROWS
    full_pass = full_m["improvement_pct"] >= MIN_FULL_IMPROVEMENT_PCT
    early_pass = early_m["improvement_pct"] > 0
    late_pass = late_m["improvement_pct"] > 0
    stable = bool(rows_pass and full_pass and early_pass and late_pass)

    return {
        "coin": coin,
        "regime_key": regime,
        "candidate_baseline_id": candidate_id,
        "global_baseline_id": global_id,
        "selected_validation_baseline": selected,
        "holdout_rows": len(holdout_regime),
        "early_rows": len(early),
        "late_rows": len(late),
        "full_candidate_mae": full_m["candidate_mae"],
        "full_global_mae": full_m["global_mae"],
        "full_improvement": full_m["improvement"],
        "full_improvement_pct": full_m["improvement_pct"],
        "early_candidate_mae": early_m["candidate_mae"],
        "early_global_mae": early_m["global_mae"],
        "early_improvement": early_m["improvement"],
        "early_improvement_pct": early_m["improvement_pct"],
        "late_candidate_mae": late_m["candidate_mae"],
        "late_global_mae": late_m["global_mae"],
        "late_improvement": late_m["improvement"],
        "late_improvement_pct": late_m["improvement_pct"],
        "rows_pass": rows_pass,
        "full_improvement_pass": full_pass,
        "early_improvement_pass": early_pass,
        "late_improvement_pass": late_pass,
        "stable_edge_research_candidate": stable,
        "edge_operationally_validated": False,
        "stability_classification": "STABLE_EDGE_RESEARCH_CANDIDATE_NOT_OPERATIONAL" if stable else "UNSTABLE_EDGE_RESEARCH_CANDIDATE_RESEARCH_ONLY",
        "trading_signal_generated": False,
        "recommendation_generated": False,
        "operational_decision_allowed": False,
        "source": SOURCE,
    }


def _criterion(cid: str, ok: bool, observed: Any, threshold: str) -> dict[str, Any]:
    return {"criterion_id": cid, "status": "PASS" if ok else "FAIL", "ready": bool(ok), "observed": observed, "threshold": threshold}


def _summaries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for coin in COINS:
        cr = [r for r in rows if r.get("coin") == coin]
        out.append({
            "coin": coin,
            "candidate_count": len(cr),
            "stable_candidate_count": sum(1 for r in cr if bool(r.get("stable_edge_research_candidate"))),
            "avg_full_improvement_pct": round(_mean([_f(r.get("full_improvement_pct"), 0.0) for r in cr]), 8),
            "avg_early_improvement_pct": round(_mean([_f(r.get("early_improvement_pct"), 0.0) for r in cr]), 8),
            "avg_late_improvement_pct": round(_mean([_f(r.get("late_improvement_pct"), 0.0) for r in cr]), 8),
            "edge_operationally_validated": False,
            "decision_layer_allowed": False,
        })
    return out


def _render_html(path: Path, payload: dict[str, Any]) -> None:
    esc = lambda x: html.escape(str(x))
    cards = [
        ("Gate", payload["edge_candidate_stability_ready"]),
        ("Phase26", payload["phase26_edge_audit_ready"]),
        ("Candidates", payload["candidate_count"]),
        ("Stable candidates", payload["stable_edge_candidate_count"]),
        ("Operational edge", payload["edge_operationally_validated"]),
        ("Decision layer", payload["decision_layer_allowed"]),
        ("Operational", payload["operational_status"]),
        ("Score", payload["mean_stability_score"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)
    cand_html = "".join(
        f"<tr><td>{esc(r['coin'])}</td><td>{esc(r['regime_key'])}</td><td>{esc(r['holdout_rows'])}</td><td>{esc(r['full_improvement_pct'])}</td><td>{esc(r['early_improvement_pct'])}</td><td>{esc(r['late_improvement_pct'])}</td><td>{esc(r['stable_edge_research_candidate'])}</td><td>{esc(r['stability_classification'])}</td></tr>"
        for r in payload["candidate_stability_preview"]
    )
    coin_html = "".join(
        f"<tr><td>{esc(r['coin'])}</td><td>{esc(r['candidate_count'])}</td><td>{esc(r['stable_candidate_count'])}</td><td>{esc(r['avg_full_improvement_pct'])}</td><td>{esc(r['avg_early_improvement_pct'])}</td><td>{esc(r['avg_late_improvement_pct'])}</td></tr>"
        for r in payload["coin_stability_summaries"]
    )
    crit_html = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td></tr>"
        for c in payload["criteria"]
    )
    page = (
        "<!doctype html><html><head><meta charset='utf-8'><title>QRDS Phase 27 Stability Audit</title>"
        "<style>body{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}.kpi{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:150px}.card{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}table{border-collapse:collapse;width:100%;background:white}th,td{border:1px solid #d9deea;padding:8px;text-align:left}th{background:#eef2ff}.blocked{background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}</style></head><body>"
        f"<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Phase 27 Edge Candidate Stability + Anti-Overfit Audit</h2>"
        f"<div class='card'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p>{card_html}<p class='blocked'>Stable research candidates are not operational edge, signals, recommendations, allocations, or decisions.</p></div>"
        f"<h2>Candidate stability</h2><table><thead><tr><th>coin</th><th>regime</th><th>rows</th><th>full imp pct</th><th>early imp pct</th><th>late imp pct</th><th>stable</th><th>classification</th></tr></thead><tbody>{cand_html}</tbody></table>"
        f"<h2>Coin summaries</h2><table><thead><tr><th>coin</th><th>candidates</th><th>stable</th><th>avg full</th><th>avg early</th><th>avg late</th></tr></thead><tbody>{coin_html}</tbody></table>"
        f"<h2>Criteria</h2><table><thead><tr><th>criterion</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th></tr></thead><tbody>{crit_html}</tbody></table>"
        f"<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"
    )
    path.write_text(page, encoding="utf-8")


def _update_project_status(root: Path, payload: dict[str, Any]) -> None:
    status_path = root / "crypto_decision_lab/docs/reports/PROJECT_STATUS_QRDS_GATE_BTC.md"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    existing = status_path.read_text(encoding="utf-8") if status_path.exists() else "# QRDS/QOS Gate BTC — Project Status\n"
    marker = "\n## Latest Phase 27 update\n"
    before = existing.split(marker)[0].rstrip()
    section = [
        marker.strip(), "",
        f"Updated at: {payload['generated_at']}", "",
        f"- Phase 27 gate: `{payload['gate_answer']}`",
        f"- Candidate stability ready: `{payload['edge_candidate_stability_ready']}`",
        f"- Candidates tested: `{payload['candidate_count']}`",
        f"- Stable research candidates: `{payload['stable_edge_candidate_count']}`",
        f"- Operational edge validated: `{payload['edge_operationally_validated']}`",
        f"- Decision layer allowed: `{payload['decision_layer_allowed']}`",
        f"- Operational status: `{payload['operational_status']}`",
        f"- Canonical writes: `{payload['canonical_data_writes']}`", "",
        "Phase 27 tests anti-overfit stability of Phase 26 edge candidates. Stable candidates remain research-only and do not authorize decisions.", "",
    ]
    status_path.write_text(before + "\n\n" + "\n".join(section), encoding="utf-8")


def build_phase27_edge_candidate_stability_anti_overfit_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    phase26 = _phase26(root)
    phase26_ready = bool(phase26.get("regime_segmented_edge_audit_ready", False))
    regime_path = _phase26_regime_path(root, phase26)
    regime_rows = _read_csv(regime_path)
    candidates = [r for r in regime_rows if _bool(r.get("edge_research_candidate"))]

    stability_rows = [_evaluate_candidate(root, c) for c in candidates]
    coin_summaries = _summaries(stability_rows)
    stable_count = sum(1 for r in stability_rows if bool(r.get("stable_edge_research_candidate")))

    stability_path = out / "edge_candidate_stability.csv"
    summary_path = out / "coin_stability_summaries.csv"
    stability_fields = [
        "coin","regime_key","candidate_baseline_id","global_baseline_id","selected_validation_baseline",
        "holdout_rows","early_rows","late_rows","full_candidate_mae","full_global_mae","full_improvement","full_improvement_pct",
        "early_candidate_mae","early_global_mae","early_improvement","early_improvement_pct",
        "late_candidate_mae","late_global_mae","late_improvement","late_improvement_pct",
        "rows_pass","full_improvement_pass","early_improvement_pass","late_improvement_pass",
        "stable_edge_research_candidate","edge_operationally_validated","stability_classification",
        "trading_signal_generated","recommendation_generated","operational_decision_allowed","source",
    ]
    summary_fields = ["coin","candidate_count","stable_candidate_count","avg_full_improvement_pct","avg_early_improvement_pct","avg_late_improvement_pct","edge_operationally_validated","decision_layer_allowed"]
    _write_csv(stability_path, stability_rows, stability_fields)
    _write_csv(summary_path, coin_summaries, summary_fields)

    edge_operationally_validated = False
    decision_layer_allowed = False
    canonical_data_writes = 0
    promotion_allowed = False
    safe_apply_allowed = False
    git_status = _git_status(root)

    criteria = [
        _criterion("phase26_index_present", bool(phase26.get("_present")), phase26.get("gate_answer", "MISSING"), "Phase 26 index present"),
        _criterion("phase26_edge_audit_ready", phase26_ready, phase26_ready, "true"),
        _criterion("phase26_candidates_present", len(candidates) > 0, len(candidates), ">0 Phase 26 research candidates"),
        _criterion("candidate_evaluations_complete", len(stability_rows) == len(candidates), f"{len(stability_rows)}/{len(candidates)}", "all candidates evaluated"),
        _criterion("candidate_stability_outputs_written", stability_path.exists() and summary_path.exists(), "written", "CSV outputs exist"),
        _criterion("stable_candidates_not_operational", edge_operationally_validated is False, edge_operationally_validated, "false"),
        _criterion("decision_layer_blocked", decision_layer_allowed is False, decision_layer_allowed, "false"),
        _criterion("signals_blocked", True, "research_stability_audit_only", "no signal/recommendation/allocation"),
        _criterion("safe_apply_blocked", not safe_apply_allowed, safe_apply_allowed, "false"),
        _criterion("promotion_blocked", not promotion_allowed, promotion_allowed, "false"),
        _criterion("canonical_writes_zero", canonical_data_writes == 0, canonical_data_writes, "0"),
        _criterion("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]
    ready_count = sum(1 for c in criteria if c["ready"])
    ready = ready_count == len(criteria)
    gate = "PHASE27_EDGE_CANDIDATE_STABILITY_ANTI_OVERFIT_READY_RESEARCH_ONLY" if ready else "PHASE27_EDGE_CANDIDATE_STABILITY_ANTI_OVERFIT_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.phase27_edge_candidate_stability_anti_overfit_pack.v1",
        "report_name": "qrds-phase27-edge-candidate-stability-anti-overfit-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": "PHASE_27_EDGE_CANDIDATE_STABILITY_ANTI_OVERFIT",
        "edge_candidate_stability_ready": ready,
        "phase26_edge_audit_ready": phase26_ready,
        "data_nature": "EDGE_CANDIDATE_STABILITY_ANTI_OVERFIT_RESEARCH_ONLY",
        "candidate_count": len(candidates),
        "stable_edge_candidate_count": stable_count,
        "coins_with_stable_candidate": len({r["coin"] for r in stability_rows if r.get("stable_edge_research_candidate")}),
        "edge_operationally_validated": edge_operationally_validated,
        "decision_layer_allowed": decision_layer_allowed,
        "candidate_stability_preview": stability_rows[:24],
        "coin_stability_summaries": coin_summaries,
        "stability_path": str(stability_path),
        "summary_path": str(summary_path),
        "stability_sha256": _sha_file(stability_path)[:16],
        "summary_sha256": _sha_file(summary_path)[:16],
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "modeling_status": "EDGE_CANDIDATE_STABILITY_READY" if ready else "EDGE_CANDIDATE_STABILITY_NEEDS_REVIEW",
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "canonical_data_writes": canonical_data_writes,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_stability_score": round(ready_count / len(criteria), 4),
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    rp = out / "phase27_edge_candidate_stability_anti_overfit_pack.json"
    mp = out / "phase27_edge_candidate_stability_anti_overfit_pack.md"
    hp = out / "index.html"
    ip = out / "phase27_edge_candidate_stability_anti_overfit_pack_index.json"

    rp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(
        f"# QRDS/QOS Phase 27 Edge Candidate Stability + Anti-Overfit Audit\n\n**Gate answer:** {gate}\n\nCandidates tested: {len(candidates)}\n\nStable research candidates: {stable_count}\n\nOperational edge validated: false\n\nDecision layer allowed: false\n\nOperational status: BLOCKED_RESEARCH_ONLY\n\nStable research candidates are not signals, recommendations, allocations, or operational decisions.\n",
        encoding="utf-8",
    )
    _render_html(hp, payload)

    index = {
        "schema": "qrds.phase27_edge_candidate_stability_anti_overfit_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": payload["station"],
        "edge_candidate_stability_ready": ready,
        "phase26_edge_audit_ready": phase26_ready,
        "data_nature": payload["data_nature"],
        "candidate_count": len(candidates),
        "stable_edge_candidate_count": stable_count,
        "coins_with_stable_candidate": payload["coins_with_stable_candidate"],
        "edge_operationally_validated": edge_operationally_validated,
        "decision_layer_allowed": decision_layer_allowed,
        "operational_status": payload["operational_status"],
        "modeling_status": payload["modeling_status"],
        "safe_apply_allowed": payload["safe_apply_allowed"],
        "promotion_allowed": payload["promotion_allowed"],
        "canonical_data_writes": payload["canonical_data_writes"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_stability_score": payload["mean_stability_score"],
        "git_status_line_count": payload["git_status_line_count"],
        "stability_path": str(stability_path),
        "summary_path": str(summary_path),
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


build_edge_candidate_stability_anti_overfit_pack = build_phase27_edge_candidate_stability_anti_overfit_pack
