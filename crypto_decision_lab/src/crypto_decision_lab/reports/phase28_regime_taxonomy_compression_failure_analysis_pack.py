from __future__ import annotations

import csv
import hashlib
import html
import json
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"
COINS = ["BTC", "ETH", "SOL"]
SOURCE = "QRDS_REGIME_TAXONOMY_COMPRESSION_FAILURE_ANALYSIS_RESEARCH_ONLY"
HARNESS_SOURCE = "QRDS_OFFLINE_EXPERIMENT_HARNESS_RESEARCH_ONLY"
VOL_TARGET = "forward_realized_vol_24h_research_target"

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


def _phase27(root: Path) -> dict[str, Any]:
    return _load_json(root / "crypto_decision_lab/artifacts/phase27_edge_candidate_stability_anti_overfit_pack/phase27_edge_candidate_stability_anti_overfit_pack_index.json")


def _stability_path(root: Path, phase27: dict[str, Any]) -> Path:
    raw = phase27.get("stability_path")
    if raw:
        return Path(raw)
    return root / "crypto_decision_lab/artifacts/phase27_edge_candidate_stability_anti_overfit_pack/edge_candidate_stability.csv"


def _harness_path(root: Path, coin: str) -> Path:
    return root / "crypto_decision_lab/artifacts/phase19_offline_experiment_harness_pack/harness" / f"{coin.lower()}_offline_experiment_harness_1h.csv"


def _harness_rows(root: Path, coin: str) -> list[dict[str, Any]]:
    return [r for r in _read_csv(_harness_path(root, coin)) if r.get("source") in {HARNESS_SOURCE, ""}]


def _parts(regime: str) -> tuple[str, str, str]:
    p = (regime or "").split("|")
    p += ["MISSING"] * (3 - len(p))
    return p[0], p[1], p[2]


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


def _coarse_regime_from_key(regime: str) -> str:
    v, d, m = _parts(regime)
    return "|".join([_coarse_vol(v), _coarse_disp(d), _coarse_mom(m)])


def _coarse_regime_from_row(row: dict[str, Any]) -> str:
    return "|".join([
        _coarse_vol(str(row.get("volatility_regime_24h", ""))),
        _coarse_disp(str(row.get("dispersion_regime_24h", ""))),
        _coarse_mom(str(row.get("momentum_diagnostic_24h", ""))),
    ])


def _failure_reason(row: dict[str, Any]) -> str:
    if not _b(row.get("rows_pass")):
        return "INSUFFICIENT_SEGMENT_DEPTH"
    full = _f(row.get("full_improvement_pct"), 0.0)
    early = _f(row.get("early_improvement_pct"), 0.0)
    late = _f(row.get("late_improvement_pct"), 0.0)
    if full <= 0:
        return "FULL_HOLDOUT_EDGE_EVAPORATED"
    if early > 0 and late <= 0:
        return "LATE_HOLDOUT_DECAY"
    if early <= 0 and late > 0:
        return "EARLY_HOLDOUT_WEAKNESS"
    if early <= 0 and late <= 0:
        return "EARLY_AND_LATE_FAIL"
    if full < 0.05:
        return "IMPROVEMENT_TOO_SMALL"
    return "UNCLASSIFIED_RESEARCH_FAILURE"


def _analyse_failures(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        out.append({
            "coin": r.get("coin", ""),
            "regime_key": r.get("regime_key", ""),
            "coarse_regime_key": _coarse_regime_from_key(str(r.get("regime_key", ""))),
            "candidate_baseline_id": r.get("candidate_baseline_id", ""),
            "global_baseline_id": r.get("global_baseline_id", ""),
            "holdout_rows": r.get("holdout_rows", 0),
            "early_rows": r.get("early_rows", 0),
            "late_rows": r.get("late_rows", 0),
            "full_improvement_pct": r.get("full_improvement_pct", 0),
            "early_improvement_pct": r.get("early_improvement_pct", 0),
            "late_improvement_pct": r.get("late_improvement_pct", 0),
            "stable_edge_research_candidate": _b(r.get("stable_edge_research_candidate")),
            "failure_reason": _failure_reason(r),
            "edge_operationally_validated": False,
            "trading_signal_generated": False,
            "recommendation_generated": False,
            "operational_decision_allowed": False,
            "source": SOURCE,
        })
    return out


def _coarse_coverage(root: Path) -> list[dict[str, Any]]:
    rows_out: list[dict[str, Any]] = []
    for coin in COINS:
        h = [r for r in _harness_rows(root, coin) if r.get("split") == "HOLDOUT_RESEARCH_ONLY"]
        buckets: dict[str, list[float]] = {}
        for r in h:
            buckets.setdefault(_coarse_regime_from_row(r), []).append(_f(r.get(VOL_TARGET), 0.0))
        for bucket, vals in sorted(buckets.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            rows_out.append({
                "coin": coin,
                "coarse_regime_key": bucket,
                "holdout_rows": len(vals),
                "target_mean": round(_mean(vals), 12),
                "target_median": round(_median(vals), 12),
                "source": SOURCE,
            })
    return rows_out


def _compression_map(root: Path, failure_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    coverage = _coarse_coverage(root)
    cov_index = {(r["coin"], r["coarse_regime_key"]): r for r in coverage}
    out = []
    seen = set()
    for r in failure_rows:
        key = (r["coin"], r["regime_key"], r["coarse_regime_key"])
        if key in seen:
            continue
        seen.add(key)
        cov = cov_index.get((r["coin"], r["coarse_regime_key"]), {})
        out.append({
            "coin": r["coin"],
            "original_regime_key": r["regime_key"],
            "coarse_regime_key": r["coarse_regime_key"],
            "candidate_baseline_id": r["candidate_baseline_id"],
            "failure_reason": r["failure_reason"],
            "coarse_holdout_rows": cov.get("holdout_rows", 0),
            "coarse_target_mean": cov.get("target_mean", 0.0),
            "coarse_target_median": cov.get("target_median", 0.0),
            "compression_action": "RETEST_ON_COARSE_REGIME_NEXT_RESEARCH_ONLY",
            "edge_operationally_validated": False,
            "decision_layer_allowed": False,
            "source": SOURCE,
        })
    return out


def _criterion(cid: str, ok: bool, observed: Any, threshold: str) -> dict[str, Any]:
    return {"criterion_id": cid, "status": "PASS" if ok else "FAIL", "ready": bool(ok), "observed": observed, "threshold": threshold}


def _render_html(path: Path, payload: dict[str, Any]) -> None:
    esc = lambda x: html.escape(str(x))
    cards = [
        ("Gate", payload["regime_taxonomy_compression_ready"]),
        ("Phase27", payload["phase27_stability_ready"]),
        ("Candidates", payload["candidate_count"]),
        ("Stable", payload["stable_edge_candidate_count"]),
        ("Failures", payload["failure_rows_total"]),
        ("Compression rows", payload["compression_map_rows"]),
        ("Decision layer", payload["decision_layer_allowed"]),
        ("Operational", payload["operational_status"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)
    fail_html = "".join(
        f"<tr><td>{esc(r['coin'])}</td><td>{esc(r['regime_key'])}</td><td>{esc(r['coarse_regime_key'])}</td><td>{esc(r['full_improvement_pct'])}</td><td>{esc(r['early_improvement_pct'])}</td><td>{esc(r['late_improvement_pct'])}</td><td>{esc(r['failure_reason'])}</td></tr>"
        for r in payload["failure_analysis_preview"]
    )
    comp_html = "".join(
        f"<tr><td>{esc(r['coin'])}</td><td>{esc(r['original_regime_key'])}</td><td>{esc(r['coarse_regime_key'])}</td><td>{esc(r['coarse_holdout_rows'])}</td><td>{esc(r['compression_action'])}</td></tr>"
        for r in payload["compression_map_preview"]
    )
    crit_html = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td></tr>"
        for c in payload["criteria"]
    )
    page = (
        "<!doctype html><html><head><meta charset='utf-8'><title>QRDS Phase 28 Regime Compression</title>"
        "<style>body{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}.kpi{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:150px}.card{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}table{border-collapse:collapse;width:100%;background:white}th,td{border:1px solid #d9deea;padding:8px;text-align:left}th{background:#eef2ff}.blocked{background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}</style></head><body>"
        f"<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Phase 28 Regime Taxonomy Compression + Failure Analysis</h2>"
        f"<div class='card'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p>{card_html}<p class='blocked'>This compresses overfit-prone regimes for retest. It creates no edge validation, signals, recommendations, or decisions.</p></div>"
        f"<h2>Failure analysis</h2><table><thead><tr><th>coin</th><th>original regime</th><th>coarse regime</th><th>full</th><th>early</th><th>late</th><th>reason</th></tr></thead><tbody>{fail_html}</tbody></table>"
        f"<h2>Compression map</h2><table><thead><tr><th>coin</th><th>original regime</th><th>coarse regime</th><th>coarse rows</th><th>action</th></tr></thead><tbody>{comp_html}</tbody></table>"
        f"<h2>Criteria</h2><table><thead><tr><th>criterion</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th></tr></thead><tbody>{crit_html}</tbody></table>"
        f"<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"
    )
    path.write_text(page, encoding="utf-8")


def _update_project_status(root: Path, payload: dict[str, Any]) -> None:
    status_path = root / "crypto_decision_lab/docs/reports/PROJECT_STATUS_QRDS_GATE_BTC.md"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    existing = status_path.read_text(encoding="utf-8") if status_path.exists() else "# QRDS/QOS Gate BTC — Project Status\n"
    marker = "\n## Latest Phase 28 update\n"
    before = existing.split(marker)[0].rstrip()
    section = [
        marker.strip(), "",
        f"Updated at: {payload['generated_at']}", "",
        f"- Phase 28 gate: `{payload['gate_answer']}`",
        f"- Regime compression ready: `{payload['regime_taxonomy_compression_ready']}`",
        f"- Failure rows: `{payload['failure_rows_total']}`",
        f"- Compression map rows: `{payload['compression_map_rows']}`",
        f"- Next research path: `{payload['next_research_path']}`",
        f"- Decision layer allowed: `{payload['decision_layer_allowed']}`",
        f"- Operational status: `{payload['operational_status']}`",
        f"- Canonical writes: `{payload['canonical_data_writes']}`", "",
        "Phase 28 converts unstable fine-grained edge candidates into compressed-regime retest inputs. It validates no operational edge.", "",
    ]
    status_path.write_text(before + "\n\n" + "\n".join(section), encoding="utf-8")


def build_phase28_regime_taxonomy_compression_failure_analysis_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    phase27 = _phase27(root)
    phase27_ready = bool(phase27.get("edge_candidate_stability_ready", False))
    stable_count = int(phase27.get("stable_edge_candidate_count", 0) or 0)
    candidate_count = int(phase27.get("candidate_count", 0) or 0)

    stability_rows = _read_csv(_stability_path(root, phase27))
    failure_rows = _analyse_failures(stability_rows)
    coverage_rows = _coarse_coverage(root)
    compression_rows = _compression_map(root, failure_rows)

    failure_path = out / "candidate_failure_analysis.csv"
    coverage_path = out / "coarse_regime_coverage.csv"
    compression_path = out / "regime_compression_map.csv"

    _write_csv(failure_path, failure_rows, ["coin","regime_key","coarse_regime_key","candidate_baseline_id","global_baseline_id","holdout_rows","early_rows","late_rows","full_improvement_pct","early_improvement_pct","late_improvement_pct","stable_edge_research_candidate","failure_reason","edge_operationally_validated","trading_signal_generated","recommendation_generated","operational_decision_allowed","source"])
    _write_csv(coverage_path, coverage_rows, ["coin","coarse_regime_key","holdout_rows","target_mean","target_median","source"])
    _write_csv(compression_path, compression_rows, ["coin","original_regime_key","coarse_regime_key","candidate_baseline_id","failure_reason","coarse_holdout_rows","coarse_target_mean","coarse_target_median","compression_action","edge_operationally_validated","decision_layer_allowed","source"])

    edge_operationally_validated = False
    decision_layer_allowed = False
    canonical_data_writes = 0
    promotion_allowed = False
    safe_apply_allowed = False
    git_status = _git_status(root)

    next_path = "RETEST_COMPRESSED_REGIME_EDGE_CANDIDATES_RESEARCH_ONLY" if compression_rows else "REBUILD_REGIME_FEATURE_TAXONOMY_RESEARCH_ONLY"

    criteria = [
        _criterion("phase27_index_present", bool(phase27.get("_present")), phase27.get("gate_answer", "MISSING"), "Phase 27 index present"),
        _criterion("phase27_stability_ready", phase27_ready, phase27_ready, "true"),
        _criterion("phase27_no_stable_candidates", stable_count == 0, stable_count, "0 stable candidates triggers compression"),
        _criterion("candidate_rows_present", candidate_count > 0 and len(stability_rows) > 0, f"{candidate_count}/{len(stability_rows)}", ">0 candidates"),
        _criterion("failure_analysis_written", failure_path.exists() and len(failure_rows) == len(stability_rows), len(failure_rows), "failure row per candidate"),
        _criterion("coarse_coverage_written", coverage_path.exists() and len(coverage_rows) > 0, len(coverage_rows), ">0 coverage rows"),
        _criterion("compression_map_written", compression_path.exists() and len(compression_rows) > 0, len(compression_rows), ">0 compression rows"),
        _criterion("edge_not_operational", edge_operationally_validated is False, edge_operationally_validated, "false"),
        _criterion("decision_layer_blocked", decision_layer_allowed is False, decision_layer_allowed, "false"),
        _criterion("signals_blocked", True, "taxonomy_research_only", "no signal/recommendation/allocation"),
        _criterion("safe_apply_blocked", not safe_apply_allowed, safe_apply_allowed, "false"),
        _criterion("promotion_blocked", not promotion_allowed, promotion_allowed, "false"),
        _criterion("canonical_writes_zero", canonical_data_writes == 0, canonical_data_writes, "0"),
        _criterion("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]
    ready_count = sum(1 for c in criteria if c["ready"])
    ready = ready_count == len(criteria)
    gate = "PHASE28_REGIME_TAXONOMY_COMPRESSION_FAILURE_ANALYSIS_READY_RESEARCH_ONLY" if ready else "PHASE28_REGIME_TAXONOMY_COMPRESSION_FAILURE_ANALYSIS_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.phase28_regime_taxonomy_compression_failure_analysis_pack.v1",
        "report_name": "qrds-phase28-regime-taxonomy-compression-failure-analysis-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": "PHASE_28_REGIME_TAXONOMY_COMPRESSION_FAILURE_ANALYSIS",
        "regime_taxonomy_compression_ready": ready,
        "phase27_stability_ready": phase27_ready,
        "data_nature": "REGIME_TAXONOMY_COMPRESSION_FAILURE_ANALYSIS_RESEARCH_ONLY",
        "candidate_count": candidate_count,
        "stable_edge_candidate_count": stable_count,
        "failure_rows_total": len(failure_rows),
        "coarse_regime_coverage_rows": len(coverage_rows),
        "compression_map_rows": len(compression_rows),
        "next_research_path": next_path,
        "edge_operationally_validated": edge_operationally_validated,
        "decision_layer_allowed": decision_layer_allowed,
        "failure_analysis_preview": failure_rows[:24],
        "coverage_preview": coverage_rows[:24],
        "compression_map_preview": compression_rows[:24],
        "failure_analysis_path": str(failure_path),
        "coarse_regime_coverage_path": str(coverage_path),
        "compression_map_path": str(compression_path),
        "failure_analysis_sha256": _sha_file(failure_path)[:16],
        "coarse_regime_coverage_sha256": _sha_file(coverage_path)[:16],
        "compression_map_sha256": _sha_file(compression_path)[:16],
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "modeling_status": "REGIME_TAXONOMY_COMPRESSION_READY" if ready else "REGIME_TAXONOMY_COMPRESSION_NEEDS_REVIEW",
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "canonical_data_writes": canonical_data_writes,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_compression_score": round(ready_count / len(criteria), 4),
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    rp = out / "phase28_regime_taxonomy_compression_failure_analysis_pack.json"
    mp = out / "phase28_regime_taxonomy_compression_failure_analysis_pack.md"
    hp = out / "index.html"
    ip = out / "phase28_regime_taxonomy_compression_failure_analysis_pack_index.json"

    rp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(
        f"# QRDS/QOS Phase 28 Regime Taxonomy Compression + Failure Analysis\n\n**Gate answer:** {gate}\n\nFailure rows: {len(failure_rows)}\n\nCompression map rows: {len(compression_rows)}\n\nNext research path: `{next_path}`\n\nOperational edge validated: false\n\nDecision layer allowed: false\n\nOperational status: BLOCKED_RESEARCH_ONLY\n",
        encoding="utf-8",
    )
    _render_html(hp, payload)

    index = {
        "schema": "qrds.phase28_regime_taxonomy_compression_failure_analysis_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": payload["station"],
        "regime_taxonomy_compression_ready": ready,
        "phase27_stability_ready": phase27_ready,
        "data_nature": payload["data_nature"],
        "candidate_count": candidate_count,
        "stable_edge_candidate_count": stable_count,
        "failure_rows_total": len(failure_rows),
        "coarse_regime_coverage_rows": len(coverage_rows),
        "compression_map_rows": len(compression_rows),
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
        "mean_compression_score": payload["mean_compression_score"],
        "git_status_line_count": payload["git_status_line_count"],
        "failure_analysis_path": str(failure_path),
        "coarse_regime_coverage_path": str(coverage_path),
        "compression_map_path": str(compression_path),
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


build_regime_taxonomy_compression_failure_analysis_pack = build_phase28_regime_taxonomy_compression_failure_analysis_pack
