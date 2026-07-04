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
SOURCE = "QRDS_COMPRESSED_REGIME_EDGE_RETEST_RESEARCH_ONLY"

MIN_COMPRESSED_ROWS = 150
MIN_SEGMENT_ROWS = 50
MIN_FULL_IMPROVEMENT_PCT = 0.03

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


def _phase28(root: Path) -> dict[str, Any]:
    return _load_json(root / "crypto_decision_lab/artifacts/phase28_regime_taxonomy_compression_failure_analysis_pack/phase28_regime_taxonomy_compression_failure_analysis_pack_index.json")


def _compression_path(root: Path, phase28: dict[str, Any]) -> Path:
    raw = phase28.get("compression_map_path")
    if raw:
        return Path(raw)
    return root / "crypto_decision_lab/artifacts/phase28_regime_taxonomy_compression_failure_analysis_pack/regime_compression_map.csv"


def _harness_path(root: Path, coin: str) -> Path:
    return root / "crypto_decision_lab/artifacts/phase19_offline_experiment_harness_pack/harness" / f"{coin.lower()}_offline_experiment_harness_1h.csv"


def _harness_rows(root: Path, coin: str) -> list[dict[str, Any]]:
    rows = [r for r in _read_csv(_harness_path(root, coin)) if r.get("source") in {HARNESS_SOURCE, ""}]
    return sorted(rows, key=lambda r: str(r.get("timestamp", "")))


def _coarse_vol(x: str) -> str:
    u = (x or "").upper()
    if "HIGH" in u or "EXTREME" in u or "STRESS" in u:
        return "VOL_COARSE_HIGH"
    if "LOW" in u or "CALM" in u:
        return "VOL_COARSE_LOW"
    return "VOL_COARSE_MID"


def _coarse_disp(x: str) -> str:
    u = (x or "").upper()
    if "HIGH" in u or "WIDE" in u or "STRESS" in u:
        return "DISP_COARSE_HIGH"
    if "LOW" in u or "TIGHT" in u:
        return "DISP_COARSE_LOW"
    return "DISP_COARSE_MID"


def _coarse_mom(x: str) -> str:
    u = (x or "").upper()
    if "POS" in u or "UP" in u:
        return "MOM_COARSE_POSITIVE"
    if "NEG" in u or "DOWN" in u:
        return "MOM_COARSE_NEGATIVE"
    return "MOM_COARSE_NEUTRAL"


def _coarse_regime_from_row(row: dict[str, Any]) -> str:
    return "|".join([
        _coarse_vol(str(row.get("volatility_regime_24h", ""))),
        _coarse_disp(str(row.get("dispersion_regime_24h", ""))),
        _coarse_mom(str(row.get("momentum_diagnostic_24h", ""))),
    ])


def _stress(r: dict[str, Any]) -> float:
    return max(abs(_f(r.get("return_24h_min"), 0.0)), abs(_f(r.get("return_24h_max"), 0.0))) * math.sqrt(365.0)


def _term_vals(r: dict[str, Any]) -> list[float]:
    return [x for x in [_f(r.get("rolling_vol_24h_ann"), 0.0), _f(r.get("rolling_vol_168h_ann"), 0.0), _f(r.get("rolling_vol_720h_ann"), 0.0)] if x > 0]


def _fine_regime_key(r: dict[str, Any]) -> str:
    return "|".join([
        str(r.get("volatility_regime_24h", "VOL_MISSING")),
        str(r.get("dispersion_regime_24h", "DISP_MISSING")),
        str(r.get("momentum_diagnostic_24h", "MOM_MISSING")),
    ])


def _fit_context(rows: list[dict[str, Any]]) -> dict[str, Any]:
    train = [r for r in rows if r.get("split") == "TRAIN_RESEARCH_ONLY"]
    vals = [_f(r.get(VOL_TARGET), 0.0) for r in train]
    regime: dict[str, list[float]] = {}
    for r in train:
        regime.setdefault(_fine_regime_key(r), []).append(_f(r.get(VOL_TARGET), 0.0))
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
        return max(0.0, ctx["regime_medians"].get(_fine_regime_key(r), ctx["train_median"]))
    return max(0.0, v24)


def _mae(rows: list[dict[str, Any]], baseline_id: str, ctx: dict[str, Any], selected: str = "") -> float:
    if not rows:
        return 0.0
    return _mean([abs(_predict(r, baseline_id, ctx, selected) - _f(r.get(VOL_TARGET), 0.0)) for r in rows])


def _selected_validation_baseline(rows: list[dict[str, Any]], ctx: dict[str, Any]) -> str:
    val = [r for r in rows if r.get("split") == "VALIDATION_RESEARCH_ONLY"]
    scores = {bid: _mae(val, bid, ctx) for bid in BASELINE_IDS if bid != "VOL_VALIDATION_SELECTED_STRENGTHENED"}
    return min(scores, key=scores.get) if scores else "VOL_CURRENT_24H_PROXY"


def _global_best_baseline(holdout: list[dict[str, Any]], ctx: dict[str, Any], selected: str) -> str:
    scores = {bid: _mae(holdout, bid, ctx, selected) for bid in BASELINE_IDS}
    return min(scores, key=scores.get) if scores else "VOL_CURRENT_24H_PROXY"


def _segment_metrics(rows: list[dict[str, Any]], candidate_id: str, global_id: str, ctx: dict[str, Any], selected: str) -> dict[str, float]:
    cand_mae = _mae(rows, candidate_id, ctx, selected)
    glob_mae = _mae(rows, global_id, ctx, selected)
    imp = glob_mae - cand_mae if glob_mae > 0 else 0.0
    pct = imp / glob_mae if glob_mae > 0 else 0.0
    return {
        "candidate_mae": round(cand_mae, 12),
        "global_mae": round(glob_mae, 12),
        "improvement": round(imp, 12),
        "improvement_pct": round(pct, 8),
    }


def _unique_retest_specs(compression_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    specs = []
    for r in compression_rows:
        key = (r.get("coin", ""), r.get("coarse_regime_key", ""), r.get("candidate_baseline_id", ""))
        if key in seen:
            continue
        seen.add(key)
        specs.append({
            "coin": key[0],
            "coarse_regime_key": key[1],
            "candidate_baseline_id": key[2],
            "source_original_regimes": "|".join(sorted({x.get("original_regime_key", "") for x in compression_rows if (x.get("coin", ""), x.get("coarse_regime_key", ""), x.get("candidate_baseline_id", "")) == key})),
        })
    return specs


def _evaluate_spec(root: Path, spec: dict[str, Any]) -> dict[str, Any]:
    coin = str(spec["coin"])
    coarse = str(spec["coarse_regime_key"])
    candidate_id = str(spec["candidate_baseline_id"] or "VOL_CURRENT_24H_PROXY")
    rows = _harness_rows(root, coin)
    ctx = _fit_context(rows)
    selected = _selected_validation_baseline(rows, ctx)
    holdout_all = [r for r in rows if r.get("split") == "HOLDOUT_RESEARCH_ONLY"]
    global_id = _global_best_baseline(holdout_all, ctx, selected)
    compressed = [r for r in holdout_all if _coarse_regime_from_row(r) == coarse]
    mid = len(compressed) // 2
    early = compressed[:mid]
    late = compressed[mid:]

    full_m = _segment_metrics(compressed, candidate_id, global_id, ctx, selected)
    early_m = _segment_metrics(early, candidate_id, global_id, ctx, selected)
    late_m = _segment_metrics(late, candidate_id, global_id, ctx, selected)

    rows_pass = len(compressed) >= MIN_COMPRESSED_ROWS and len(early) >= MIN_SEGMENT_ROWS and len(late) >= MIN_SEGMENT_ROWS
    full_pass = full_m["improvement_pct"] >= MIN_FULL_IMPROVEMENT_PCT
    early_pass = early_m["improvement_pct"] > 0
    late_pass = late_m["improvement_pct"] > 0
    stable = bool(rows_pass and full_pass and early_pass and late_pass)

    if not rows_pass:
        classification = "COMPRESSED_REGIME_INSUFFICIENT_DEPTH_RESEARCH_ONLY"
    elif stable:
        classification = "STABLE_COMPRESSED_REGIME_EDGE_RESEARCH_CANDIDATE_NOT_OPERATIONAL"
    elif full_pass and (not early_pass or not late_pass):
        classification = "COMPRESSED_REGIME_TEMPORALLY_UNSTABLE_RESEARCH_ONLY"
    else:
        classification = "COMPRESSED_REGIME_NO_EDGE_RESEARCH_ONLY"

    return {
        "coin": coin,
        "coarse_regime_key": coarse,
        "source_original_regimes": spec.get("source_original_regimes", ""),
        "candidate_baseline_id": candidate_id,
        "global_baseline_id": global_id,
        "selected_validation_baseline": selected,
        "compressed_holdout_rows": len(compressed),
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
        "stable_compressed_edge_research_candidate": stable,
        "edge_operationally_validated": False,
        "decision_layer_allowed": False,
        "classification": classification,
        "trading_signal_generated": False,
        "recommendation_generated": False,
        "operational_decision_allowed": False,
        "source": SOURCE,
    }


def _coin_summaries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for coin in COINS:
        cr = [r for r in rows if r.get("coin") == coin]
        out.append({
            "coin": coin,
            "retest_count": len(cr),
            "stable_compressed_candidate_count": sum(1 for r in cr if bool(r.get("stable_compressed_edge_research_candidate"))),
            "avg_full_improvement_pct": round(_mean([_f(r.get("full_improvement_pct"), 0.0) for r in cr]), 8),
            "avg_early_improvement_pct": round(_mean([_f(r.get("early_improvement_pct"), 0.0) for r in cr]), 8),
            "avg_late_improvement_pct": round(_mean([_f(r.get("late_improvement_pct"), 0.0) for r in cr]), 8),
            "edge_operationally_validated": False,
            "decision_layer_allowed": False,
        })
    return out


def _criterion(cid: str, ok: bool, observed: Any, threshold: str) -> dict[str, Any]:
    return {"criterion_id": cid, "status": "PASS" if ok else "FAIL", "ready": bool(ok), "observed": observed, "threshold": threshold}


def _render_html(path: Path, payload: dict[str, Any]) -> None:
    esc = lambda x: html.escape(str(x))
    cards = [
        ("Gate", payload["compressed_regime_retest_ready"]),
        ("Phase28", payload["phase28_compression_ready"]),
        ("Retests", payload["compressed_retest_count"]),
        ("Stable compressed", payload["stable_compressed_candidate_count"]),
        ("Operational edge", payload["edge_operationally_validated"]),
        ("Decision layer", payload["decision_layer_allowed"]),
        ("Operational", payload["operational_status"]),
        ("Score", payload["mean_retest_score"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)
    retest_html = "".join(
        f"<tr><td>{esc(r['coin'])}</td><td>{esc(r['coarse_regime_key'])}</td><td>{esc(r['compressed_holdout_rows'])}</td><td>{esc(r['candidate_baseline_id'])}</td><td>{esc(r['global_baseline_id'])}</td><td>{esc(r['full_improvement_pct'])}</td><td>{esc(r['early_improvement_pct'])}</td><td>{esc(r['late_improvement_pct'])}</td><td>{esc(r['stable_compressed_edge_research_candidate'])}</td><td>{esc(r['classification'])}</td></tr>"
        for r in payload["compressed_retest_preview"]
    )
    coin_html = "".join(
        f"<tr><td>{esc(r['coin'])}</td><td>{esc(r['retest_count'])}</td><td>{esc(r['stable_compressed_candidate_count'])}</td><td>{esc(r['avg_full_improvement_pct'])}</td><td>{esc(r['avg_early_improvement_pct'])}</td><td>{esc(r['avg_late_improvement_pct'])}</td></tr>"
        for r in payload["coin_retest_summaries"]
    )
    crit_html = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td></tr>"
        for c in payload["criteria"]
    )
    page = (
        "<!doctype html><html><head><meta charset='utf-8'><title>QRDS Phase 29 Compressed Retest</title>"
        "<style>body{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}.kpi{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:150px}.card{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}table{border-collapse:collapse;width:100%;background:white}th,td{border:1px solid #d9deea;padding:8px;text-align:left}th{background:#eef2ff}.blocked{background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}</style></head><body>"
        f"<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Phase 29 Compressed Regime Edge Retest</h2>"
        f"<div class='card'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p>{card_html}<p class='blocked'>Compressed stable candidates are still research-only, not operational edge, signals, recommendations, allocations, or decisions.</p></div>"
        f"<h2>Compressed retests</h2><table><thead><tr><th>coin</th><th>coarse regime</th><th>rows</th><th>candidate</th><th>global</th><th>full</th><th>early</th><th>late</th><th>stable</th><th>classification</th></tr></thead><tbody>{retest_html}</tbody></table>"
        f"<h2>Coin summaries</h2><table><thead><tr><th>coin</th><th>retests</th><th>stable</th><th>avg full</th><th>avg early</th><th>avg late</th></tr></thead><tbody>{coin_html}</tbody></table>"
        f"<h2>Criteria</h2><table><thead><tr><th>criterion</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th></tr></thead><tbody>{crit_html}</tbody></table>"
        f"<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"
    )
    path.write_text(page, encoding="utf-8")


def _update_project_status(root: Path, payload: dict[str, Any]) -> None:
    status_path = root / "crypto_decision_lab/docs/reports/PROJECT_STATUS_QRDS_GATE_BTC.md"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    existing = status_path.read_text(encoding="utf-8") if status_path.exists() else "# QRDS/QOS Gate BTC — Project Status\n"
    marker = "\n## Latest Phase 29 update\n"
    before = existing.split(marker)[0].rstrip()
    section = [
        marker.strip(), "",
        f"Updated at: {payload['generated_at']}", "",
        f"- Phase 29 gate: `{payload['gate_answer']}`",
        f"- Compressed retest ready: `{payload['compressed_regime_retest_ready']}`",
        f"- Retests: `{payload['compressed_retest_count']}`",
        f"- Stable compressed candidates: `{payload['stable_compressed_candidate_count']}`",
        f"- Operational edge validated: `{payload['edge_operationally_validated']}`",
        f"- Decision layer allowed: `{payload['decision_layer_allowed']}`",
        f"- Next research path: `{payload['next_research_path']}`",
        f"- Operational status: `{payload['operational_status']}`",
        f"- Canonical writes: `{payload['canonical_data_writes']}`", "",
        "Phase 29 retests compressed-regime candidates. Stable compressed candidates remain research-only and do not authorize decisions.", "",
    ]
    status_path.write_text(before + "\n\n" + "\n".join(section), encoding="utf-8")


def build_phase29_compressed_regime_edge_retest_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    phase28 = _phase28(root)
    phase28_ready = bool(phase28.get("regime_taxonomy_compression_ready", False))
    compression_rows = _read_csv(_compression_path(root, phase28))
    specs = _unique_retest_specs(compression_rows)
    retests = [_evaluate_spec(root, s) for s in specs]
    summaries = _coin_summaries(retests)

    stable_count = sum(1 for r in retests if bool(r.get("stable_compressed_edge_research_candidate")))
    edge_operationally_validated = False
    decision_layer_allowed = False
    canonical_data_writes = 0
    promotion_allowed = False
    safe_apply_allowed = False
    git_status = _git_status(root)

    next_path = "ROLLING_VALIDATION_FOR_STABLE_COMPRESSED_CANDIDATES_RESEARCH_ONLY" if stable_count > 0 else "REBUILD_FEATURES_AND_BASELINES_NO_EDGE_RESEARCH_ONLY"

    retest_path = out / "compressed_regime_edge_retest.csv"
    summary_path = out / "coin_compressed_retest_summaries.csv"
    retest_fields = [
        "coin","coarse_regime_key","source_original_regimes","candidate_baseline_id","global_baseline_id","selected_validation_baseline",
        "compressed_holdout_rows","early_rows","late_rows","full_candidate_mae","full_global_mae","full_improvement","full_improvement_pct",
        "early_candidate_mae","early_global_mae","early_improvement","early_improvement_pct",
        "late_candidate_mae","late_global_mae","late_improvement","late_improvement_pct",
        "rows_pass","full_improvement_pass","early_improvement_pass","late_improvement_pass",
        "stable_compressed_edge_research_candidate","edge_operationally_validated","decision_layer_allowed","classification",
        "trading_signal_generated","recommendation_generated","operational_decision_allowed","source",
    ]
    summary_fields = ["coin","retest_count","stable_compressed_candidate_count","avg_full_improvement_pct","avg_early_improvement_pct","avg_late_improvement_pct","edge_operationally_validated","decision_layer_allowed"]
    _write_csv(retest_path, retests, retest_fields)
    _write_csv(summary_path, summaries, summary_fields)

    criteria = [
        _criterion("phase28_index_present", bool(phase28.get("_present")), phase28.get("gate_answer", "MISSING"), "Phase 28 index present"),
        _criterion("phase28_compression_ready", phase28_ready, phase28_ready, "true"),
        _criterion("compression_rows_present", len(compression_rows) > 0, len(compression_rows), ">0 compression rows"),
        _criterion("compressed_retests_complete", len(retests) > 0 and len(retests) <= len(compression_rows), f"{len(retests)}/{len(compression_rows)}", "unique compressed retests complete"),
        _criterion("retest_outputs_written", retest_path.exists() and summary_path.exists(), "written", "CSV outputs exist"),
        _criterion("edge_not_operational", edge_operationally_validated is False, edge_operationally_validated, "false"),
        _criterion("decision_layer_blocked", decision_layer_allowed is False, decision_layer_allowed, "false"),
        _criterion("signals_blocked", True, "compressed_regime_retest_only", "no signal/recommendation/allocation"),
        _criterion("safe_apply_blocked", not safe_apply_allowed, safe_apply_allowed, "false"),
        _criterion("promotion_blocked", not promotion_allowed, promotion_allowed, "false"),
        _criterion("canonical_writes_zero", canonical_data_writes == 0, canonical_data_writes, "0"),
        _criterion("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]
    ready_count = sum(1 for c in criteria if c["ready"])
    ready = ready_count == len(criteria)
    gate = "PHASE29_COMPRESSED_REGIME_EDGE_RETEST_READY_RESEARCH_ONLY" if ready else "PHASE29_COMPRESSED_REGIME_EDGE_RETEST_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.phase29_compressed_regime_edge_retest_pack.v1",
        "report_name": "qrds-phase29-compressed-regime-edge-retest-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": "PHASE_29_COMPRESSED_REGIME_EDGE_RETEST",
        "compressed_regime_retest_ready": ready,
        "phase28_compression_ready": phase28_ready,
        "data_nature": "COMPRESSED_REGIME_EDGE_RETEST_RESEARCH_ONLY",
        "compression_rows": len(compression_rows),
        "compressed_retest_count": len(retests),
        "stable_compressed_candidate_count": stable_count,
        "coins_with_stable_compressed_candidate": len({r["coin"] for r in retests if r.get("stable_compressed_edge_research_candidate")}),
        "next_research_path": next_path,
        "edge_operationally_validated": edge_operationally_validated,
        "decision_layer_allowed": decision_layer_allowed,
        "compressed_retest_preview": retests[:24],
        "coin_retest_summaries": summaries,
        "retest_path": str(retest_path),
        "summary_path": str(summary_path),
        "retest_sha256": _sha_file(retest_path)[:16],
        "summary_sha256": _sha_file(summary_path)[:16],
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "modeling_status": "COMPRESSED_REGIME_RETEST_READY" if ready else "COMPRESSED_REGIME_RETEST_NEEDS_REVIEW",
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "canonical_data_writes": canonical_data_writes,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_retest_score": round(ready_count / len(criteria), 4),
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    rp = out / "phase29_compressed_regime_edge_retest_pack.json"
    mp = out / "phase29_compressed_regime_edge_retest_pack.md"
    hp = out / "index.html"
    ip = out / "phase29_compressed_regime_edge_retest_pack_index.json"

    rp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(
        f"# QRDS/QOS Phase 29 Compressed Regime Edge Retest\n\n**Gate answer:** {gate}\n\nCompressed retests: {len(retests)}\n\nStable compressed candidates: {stable_count}\n\nNext research path: `{next_path}`\n\nOperational edge validated: false\n\nDecision layer allowed: false\n\nOperational status: BLOCKED_RESEARCH_ONLY\n",
        encoding="utf-8",
    )
    _render_html(hp, payload)

    index = {
        "schema": "qrds.phase29_compressed_regime_edge_retest_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": payload["station"],
        "compressed_regime_retest_ready": ready,
        "phase28_compression_ready": phase28_ready,
        "data_nature": payload["data_nature"],
        "compression_rows": len(compression_rows),
        "compressed_retest_count": len(retests),
        "stable_compressed_candidate_count": stable_count,
        "coins_with_stable_compressed_candidate": payload["coins_with_stable_compressed_candidate"],
        "next_research_path": next_path,
        "edge_operationally_validated": edge_operationally_validated,
        "decision_layer_allowed": decision_layer_allowed,
        "operational_status": payload["operational_status"],
        "modeling_status": payload["modeling_status"],
        "safe_apply_allowed": payload["safe_apply_allowed"],
        "promotion_allowed": payload["promotion_allowed"],
        "canonical_data_writes": payload["canonical_data_writes"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_retest_score": payload["mean_retest_score"],
        "git_status_line_count": payload["git_status_line_count"],
        "retest_path": str(retest_path),
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


build_compressed_regime_edge_retest_pack = build_phase29_compressed_regime_edge_retest_pack
